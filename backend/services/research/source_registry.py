"""Operational source-family contracts and fail-closed, server-side reviews.

The researched catalog is not imported at runtime. These versioned contracts
describe supported routes; neither registration nor channel health grants use
permission or establishes successful body acquisition. No health/network probe
runs on this path. Existing routes retain their own access controls.
"""
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
import re
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit
from contextvars import ContextVar
from contextlib import contextmanager


CAPABILITIES = frozenset({'DISCOVERY_ONLY', 'BODY_ACQUISITION', 'STRUCTURED_EVIDENCE', 'MODEL_PROCESSING'})
STATES = frozenset({'AUTH_REQUIRED', 'PERMISSION_REQUIRED', 'BLOCKED', 'UNVERIFIED', 'REVIEW_APPROVED'})
_SCOPES = {'discovery', 'body', 'excerpt', 'model_processing'}
_BODY_REGISTRY = ContextVar('aegis_source_body_registry', default=None)
_ROBOTS_FETCH = ContextVar('aegis_source_robots_fetch', default=None)
SOURCE_USER_AGENT = 'AegisResearchBot/1.0'
_NEIGHBOURS = {
    'bollywood': {'film', 'interviews'},
    'regional_cinema': {'film', 'interviews', 'hindi'},
    'hollywood': {'film', 'television', 'interviews'},
    'cricket': {'sports'},
    'elections': {'politics', 'public_policy'},
    'semiconductors': {'technology', 'manufacturing', 'materials'},
    'energy': {'research', 'materials'},
    'finance': {'business', 'filings', 'banking', 'regulation'},
    'scams': {'fraud', 'impersonation', 'enforcement', 'fact_checks', 'consumer_protection'},
    'false_quotes': {'fact_checks', 'false_quotes', 'synthetic_media'},
    'politics': {'public_policy', 'elections'},
    'product_safety': {'recalls', 'product_safety'},
}


@lru_cache(maxsize=1)
def definitions():
    data = json.loads(Path(__file__).with_name('source_registry_data.json').read_text(encoding='utf-8'))
    sources = data['sources']
    ids = set()
    for row in sources:
        if row['id'] in ids or not row['hosts'] or not row['topics']:
            raise ValueError('Invalid operational source definition')
        ids.add(row['id'])
        for host in row['hosts']:
            parsed = urlsplit('https://' + host)
            if parsed.hostname != host or parsed.path or parsed.username or parsed.port:
                raise ValueError('Invalid source host')
    return tuple(sources)


def _reviews_from_server():
    filename = os.getenv('AEGIS_SOURCE_REVIEWS_FILE', '').strip()
    if not filename:
        value = json.loads(Path(__file__).with_name('source_public_licence_reviews.json').read_text(encoding='utf-8'))
        return value['reviews'], 'VERSIONED_PUBLIC_LICENCE_REVIEW'
    try:
        path = Path(filename)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 128_000:
            raise ValueError('Unsafe review file')
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('schema_version') != 1 or not isinstance(value.get('reviews'), dict):
            raise ValueError('Invalid review schema')
        return value['reviews'], 'LOADED'
    except (OSError, ValueError, TypeError):
        return {}, 'INVALID_FAIL_CLOSED'


class SourceRegistry:
    def __init__(self, *, reviews=None, sources=None, clock=None, robots_fetcher=None, monotonic=None, sleeper=None):
        self.sources = tuple(sources) if sources is not None else definitions()
        self.by_id = {s['id']: s for s in self.sources}
        self._reviews = reviews
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._observations = {}
        self._lock = threading.Lock()
        self._robots_fetcher = robots_fetcher
        self._robots_cache, self._robots_locks = {}, {}
        self._pacing_locks, self._last_completed = {}, {}
        self._monotonic, self._sleep = monotonic or time.monotonic, sleeper or time.sleep

    def match_url(self, url):
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or '').casefold().rstrip('.')
            if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
                return None
            matches = [row for row in self.sources if any(host == h or host.endswith('.' + h) for h in row['hosts'])]
            return max(matches, key=lambda row: max(map(len, row['hosts']))) if matches else None
        except ValueError:
            return None

    def describe(self, family, runtime_capabilities=None):
        row = self.by_id[family]
        return {**row, 'capabilities': {
            'DISCOVERY_ONLY': self.assess(family, 'discovery', runtime_capabilities),
            'BODY_ACQUISITION': self.assess(family, 'body', runtime_capabilities),
            'STRUCTURED_EVIDENCE': {'declared_api': row['body'].get('structured', False),
                                    'runtime_availability': 'UNVERIFIED'}},
            'excerpt_permission': self.assess(family, 'excerpt', runtime_capabilities),
            'model_processing_permission': self.assess(family, 'model_processing')}

    def _grant(self, family, scope):
        reviews, config = (self._reviews, 'INJECTED_REVIEW') if self._reviews is not None else _reviews_from_server()
        if family not in reviews:
            return False, 'NO_REVIEW' if config != 'INVALID_FAIL_CLOSED' else config
        review = reviews[family]
        try:
            if not isinstance(review, dict):
                return False, 'INVALID_REVIEW_FAIL_CLOSED'
            if review.get('decision') in {'DENIED', 'REJECTED'}:
                return False, 'EXPLICIT_PERMISSION_DENIED'
            if review.get('decision') != 'APPROVED':
                return False, 'REVIEW_NOT_APPROVED'
            expiry = datetime.fromisoformat(review['expires_at'].replace('Z', '+00:00'))
            if expiry.tzinfo is None or expiry <= self._clock():
                return False, 'REVIEW_EXPIRED_OR_INVALID'
            scopes = review.get('scopes', [])
            if not isinstance(scopes, list) or not set(scopes) <= _SCOPES or scope not in scopes:
                return False, 'SCOPE_NOT_APPROVED'
            reference = urlsplit(review.get('basis_url', ''))
            if reference.scheme != 'https' or not reference.hostname or reference.username or reference.password:
                return False, 'MISSING_REVIEW_BASIS'
            if not isinstance(review.get('reviewed_at'), str):
                return False, 'MISSING_REVIEW_DATE'
            return True, 'SERVER_REVIEW_APPROVED'
        except (KeyError, ValueError, TypeError, AttributeError):
            return False, 'INVALID_REVIEW_FAIL_CLOSED'

    def assess(self, family, scope='discovery', runtime_capabilities=None):
        row = self.by_id[family]
        if scope not in _SCOPES:
            raise ValueError('Unsupported source permission scope')
        permitted, review_basis = self._grant(family, scope)
        status, eligible = 'UNVERIFIED', False
        if (row.get('permission_status') == 'EXISTING_ROUTE_POLICY' and not permitted
                and review_basis == 'NO_REVIEW' and scope != 'model_processing'):
            # Not a new enablement. Its native route still decides auth/access.
            status, eligible = 'EXISTING_ROUTE_POLICY', True
        elif not permitted:
            status = ('PERMISSION_REQUIRED' if row.get('permission_status') == 'PERMISSION_REQUIRED'
                      or review_basis in {'EXPLICIT_PERMISSION_DENIED', 'SCOPE_NOT_APPROVED'} else 'UNVERIFIED')
        elif row.get('auth_env') and not os.getenv(row['auth_env'], '').strip():
            status = 'AUTH_REQUIRED'
        else:
            eligible, status = True, 'REVIEW_APPROVED'
        if eligible and row.get('auth_env') and not os.getenv(row['auth_env'], '').strip():
            eligible, status = False, 'AUTH_REQUIRED'
        capability = ('DISCOVERY_ONLY' if scope == 'discovery' else
                      'MODEL_PROCESSING' if scope == 'model_processing' else 'BODY_ACQUISITION')
        route = row['discovery' if scope == 'discovery' else 'body']
        channel_decision = None
        if eligible and runtime_capabilities is not None:
            decision = runtime_capabilities.assess(route['channel'], route['operation'])
            channel_decision = decision['decision']
            if channel_decision in {'EXCLUDE', 'DEFER_TEMPORARY'}:
                eligible, status = False, 'BLOCKED'
        with self._lock:
            observation = dict(self._observations.get(family, {}))
        if observation and (self._clock().timestamp() - observation['at_epoch']) > 900:
            observation = {'availability': 'UNVERIFIED', 'stale': True}
        if eligible and observation.get('availability') == 'BLOCKED':
            eligible, status = False, 'BLOCKED'
        return {'source_family': family, 'scope': scope, 'capability': capability,
                'eligible_for_bounded_probe': eligible, 'status': status,
                'review_basis': review_basis, 'channel_decision': channel_decision,
                'runtime_availability': observation.get('availability', 'UNVERIFIED'),
                'runtime_observation': observation, 'network_calls': 0}

    def body_decision(self, url):
        row = self.match_url(url)
        allowed = {v.strip() for v in os.getenv('AEGIS_SOURCE_ALLOWED_FAMILIES', '').split(',') if v.strip()}
        if allowed and (row is None or row['id'] not in allowed):
            if (urlsplit(url).hostname or '').lower() == 'news.google.com':
                return {'source_family': None, 'status': 'DISCOVERY_ONLY', 'eligible': True}
            return {'source_family': row['id'] if row else None, 'status': 'BLOCKED',
                    'eligible': False, 'reason': 'SOURCE_OUTSIDE_SERVER_ALLOWLIST'}
        if row is None:
            return {'source_family': None, 'status': 'OUTSIDE_REGISTRY', 'eligible': True}
        decision = self.assess(row['id'], 'body')
        eligible = decision['eligible_for_bounded_probe'] or decision['status'] == 'EXISTING_ROUTE_POLICY'
        if eligible and not self._path_allowed(row, url, 'body'):
            return {**decision, 'eligible': False, 'status': 'PERMISSION_REQUIRED', 'reason': 'PATH_OUTSIDE_REVIEWED_SCOPE'}
        return {**decision, 'eligible': eligible}

    @staticmethod
    def _path_allowed(row, url, scope):
        paths = row.get('allowed_paths', {}).get(scope)
        if paths is None:
            return True
        try:
            from urllib.parse import unquote
            parsed = urlsplit(url)
            hosts = row.get('scope_hosts', {}).get(scope)
            if hosts is not None and (parsed.hostname or '').lower() not in hosts:
                return False
            path = unquote(parsed.path)
            # Reject residual escapes: a downstream second decode must not turn
            # an allowed press path into a private file or another path segment.
            if '%' in path or any(part in {'.', '..'} for part in path.split('/')) or '\\' in path:
                return False
            return any(path.startswith(prefix) if prefix.endswith('/') else path == prefix for prefix in paths)
        except (ValueError, TypeError):
            return False

    def observe(self, url, *, body_acquired=False, failure=None):
        row = self.match_url(url)
        if not row:
            return
        availability = ('BODY_ACQUISITION_OBSERVED' if body_acquired else
                        'BLOCKED' if failure in {'ACCESS_DENIED', 'AUTH_REQUIRED', 'HTTP_403'} else 'UNVERIFIED')
        with self._lock:
            self._observations[row['id']] = {'availability': availability,
                'at_epoch': self._clock().timestamp(), 'failure': failure,
                'scope': 'NATIVE_OBSERVATION_NOT_QUALIFICATION'}

    def discovery_entrypoints(self, family):
        """Reviewed publisher directories, not guessed article slugs or evidence.

        Used inside the same reader budget when indexed discovery is weak.
        Actual robots/SSRF/redirect checks happen on the normal read path.
        """
        row = self.by_id.get(family)
        if row is None or not self.assess(family)['eligible_for_bounded_probe']:
            return []
        result = []
        for url in row['discovery'].get('entrypoints', [])[:2]:
            matched = self.match_url(url)
            if matched and matched['id'] == family and self.body_decision(url)['eligible']:
                result.append(url)
        return result

    def excerpt_decision(self, url, page=None):
        row = self.match_url(url)
        page = page if isinstance(page, dict) else {}
        if page.get('rights_exception_observed'):
            return {'eligible': False, 'reason': 'ARTICLE_RIGHTS_EXCEPTION_REVIEW_REQUIRED'}
        if row is None or (row['permission_status'] == 'EXISTING_ROUTE_POLICY'
                           and self._grant(row['id'], 'excerpt')[1] == 'NO_REVIEW'):
            return {'eligible': True, 'basis': 'EXISTING_READER_POLICY'}
        decision = self.assess(row['id'], 'excerpt')
        eligible = decision['eligible_for_bounded_probe']
        reason = decision['status']
        if eligible and not self._path_allowed(row, url, 'excerpt'):
            eligible, reason = False, 'PATH_OUTSIDE_REVIEWED_SCOPE'
        if row['id'] == 'global_voices' and (not isinstance(page.get('author'), str) or not page.get('author').strip() or
                row.get('licence_url') not in page.get('licence_urls', [])):
            eligible, reason = False, 'MISSING_CAPTURED_AUTHOR_OR_LICENCE'
        return {'eligible': eligible, 'basis': decision['review_basis'], 'reason': reason,
                'source_family': row['id'], 'licence_url': row.get('licence_url'),
                'author': page.get('author'), 'source_url': url,
                'usage': 'EXACT_TEXT_EXCERPTS_NO_THIRD_PARTY_MEDIA', 'translation': 'NOT_GENERATED'}

    def model_decision(self, url, page=None):
        """A body/excerpt grant never implicitly permits external model processing."""
        row = self.match_url(url)
        if row is None:
            return {'eligible': False, 'status': 'UNVERIFIED', 'reason': 'NO_SOURCE_MODEL_REVIEW'}
        decision = self.assess(row['id'], 'model_processing')
        excerpt = self.excerpt_decision(url, page)
        eligible = decision['eligible_for_bounded_probe'] and excerpt['eligible'] and self._path_allowed(row, url, 'model_processing')
        return {**decision, 'eligible': eligible, 'reason':
                excerpt.get('reason') if not excerpt['eligible'] else
                'MODEL_PROCESSING_APPROVED' if eligible else 'MODEL_SCOPE_NOT_APPROVED'}

    def robots_decision(self, url):
        """Lazy bounded access check on read workers, never on planning paths.

        Existing routes retain their contracts. New reviewed text families must
        also pass robots checks; a licence does not override access policy.
        """
        row = self.match_url(url)
        if row is None or row['permission_status'] == 'EXISTING_ROUTE_POLICY':
            return {'eligible': True, 'status': 'EXISTING_ROUTE_POLICY'}
        from urllib.robotparser import RobotFileParser
        from backend.infrastructure.acquisition.network.budget import remaining_timeout
        parts = urlsplit(url)
        origin = f'{parts.scheme}://{parts.netloc}'
        with self._lock:
            lock = self._robots_locks.setdefault(origin, threading.Lock())
        if not lock.acquire(timeout=remaining_timeout(5.0)):
            return {'eligible': False, 'status': 'ROBOTS_UNVERIFIED'}
        try:
            cached = self._robots_cache.get(origin)
            if cached is None or self._clock().timestamp() - cached[0] > 900:
                robots_url = origin + '/robots.txt'
                token = _ROBOTS_FETCH.set(robots_url)
                try:
                    from backend.infrastructure.acquisition.network.http import fetch_public_http
                    fetch = self._robots_fetcher or fetch_public_http
                    response = fetch(robots_url, timeout=5.0, max_bytes=128_000,
                                     max_attempts=1, max_redirects=0, headers={'User-Agent': SOURCE_USER_AGENT})
                    status, text = response.status_code, response.body.decode('utf-8', errors='replace')
                    failure = None
                except Exception as error:
                    status, text = getattr(error, 'status_code', None), ''
                    from backend.infrastructure.acquisition.network.http import transport_failure_kind
                    failure = transport_failure_kind(error)
                finally:
                    _ROBOTS_FETCH.reset(token)
                parser = RobotFileParser()
                if status == 404:
                    parser.parse(['User-agent: *', 'Allow: /'])
                elif status == 200:
                    parser.parse(text.splitlines())
                else:
                    parser = None
                cached = (self._clock().timestamp(), parser, status, failure)
                self._robots_cache[origin] = cached
                self._last_completed[origin] = self._monotonic()
            _, parser, status, failure = cached
            permitted = parser is not None and parser.can_fetch(SOURCE_USER_AGENT, url)
            delay = parser.crawl_delay(SOURCE_USER_AGENT) if parser is not None else None
            return {'eligible': permitted, 'status': 'ROBOTS_ALLOWED' if permitted else
                    'ROBOTS_DENIED' if parser is not None else 'ROBOTS_UNVERIFIED', 'http_status': status,
                    'cause': failure, 'crawl_delay_seconds': delay or 0}
        finally:
            lock.release()

    @contextmanager
    def paced_request(self, url, delay):
        """One origin-wide in-process lease, held through response completion.

        Wait inside the parent research deadline, before the HTTP socket's own
        short deadline starts. No concurrent same-origin call can jump the wait.
        """
        from backend.infrastructure.acquisition.network.budget import remaining_timeout
        parts = urlsplit(url)
        origin = f'{parts.scheme}://{parts.netloc}'
        with self._lock:
            lock = self._pacing_locks.setdefault(origin, threading.RLock())
        if not lock.acquire(timeout=remaining_timeout(30.0)):
            raise SourcePermissionError({'status': 'ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED'})
        try:
            wait = max(0.0, self._last_completed.get(origin, float('-inf')) + delay - self._monotonic())
            if wait:
                if wait > 60 or remaining_timeout(wait + .01) <= wait:
                    raise SourcePermissionError({'status': 'ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED'})
                self._sleep(wait)
                remaining_timeout(.01)
            try:
                yield
            finally:
                self._last_completed[origin] = self._monotonic()
        finally:
            lock.release()

    def select(self, context, *, runtime_capabilities=None, limit=3):
        topics = set(context.topics)
        expanded = topics | set().union(*(_NEIGHBOURS.get(t, set()) for t in topics)) if topics else set()
        ranked = []
        for row in self.sources:
            if context.agent not in row['agents'] or not topics:
                continue
            if row.get('required_jurisdiction') and row['required_jurisdiction'] != context.jurisdiction:
                continue
            if row.get('entity_scoped'):
                names = set(re.findall(r'[^\W_]+', ' '.join((context.subject, *context.aliases)).casefold()))
                anchors = {label for host in row['hosts'] for label in host.split('.')
                           if len(label) >= 4 and label not in {'news', 'press', 'source', 'investors'}}
                if not names & anchors:
                    continue
            if row['id'] == 'govuk' and not topics & {'politics', 'elections', 'scams', 'product_safety'}:
                continue
            overlap = expanded & set(row['topics'])
            if not overlap:
                continue
            supported = row.get('tasks', {}).get(context.agent, [])
            explicit_tasks = set(context.tasks) - {'BRAND_RISK', 'IDENTITY_THREAT'}
            if explicit_tasks and not explicit_tasks & set(supported):
                continue
            score = 4 * len(topics & set(row['topics'])) + len(overlap)
            # Prefer a genuinely topic-focused family over a broad catch-all
            # when both match equally. No publisher/subject special cases.
            score += 2 * len(topics & set(row['topics'])) / len(row['topics'])
            if context.language != 'und' and context.language in row['languages']:
                score += 1
            if context.jurisdiction in row['geographies']:
                score += 1
            # A disputed endorsement should seek incident/claim records even
            # when the name is an actor; entertainment popularity is not proof.
            if any(t in context.tasks for t in ('ENDORSEMENT_CLAIM', 'QUOTE_VERIFICATION')):
                if set(row['topics']) & {'fact_checks', 'enforcement', 'advertising', 'false_quotes'}:
                    score += 10
                elif set(row['topics']) & {'box_office', 'film'}:
                    score -= 4
            assessment = self.assess(row['id'], runtime_capabilities=runtime_capabilities)
            if row['discovery'].get('automatic_selection') is False:
                # A reviewed structured API must not be advertised as a web
                # article route before its native record contract is wired.
                assessment = {**assessment, 'eligible_for_bounded_probe': False,
                              'status': 'UNVERIFIED', 'routing_reason': 'EXPLICIT_ADAPTER_ONLY'}
            ranked.append((score, row, assessment))
        ranked.sort(key=lambda value: (-value[0], value[1]['id']))
        selected, decisions = [], []
        for score, row, assessment in ranked:
            decision = {**assessment, 'score': score, 'matched_topics': sorted(expanded & set(row['topics']))}
            if assessment['eligible_for_bounded_probe'] and len(selected) < max(0, min(3, limit)):
                selected.append(row)
                decision['selection'] = 'SELECTED'
            else:
                decision['selection'] = 'NOT_SELECTED' if not assessment['eligible_for_bounded_probe'] else 'SOURCE_LIMIT'
            decisions.append(decision)
        return selected, decisions[:24]


source_registry = SourceRegistry()


class SourcePermissionError(RuntimeError):
    def __init__(self, decision):
        self.failure_kind = decision['status']
        super().__init__('Source-family body access unavailable: ' + self.failure_kind)


@contextmanager
def source_body_scope(registry=None):
    token = _BODY_REGISTRY.set(registry or source_registry)
    try:
        yield
    finally:
        _BODY_REGISTRY.reset(token)


def enforce_scoped_body_access(url):
    registry = _BODY_REGISTRY.get()
    if registry is not None:
        # The exact in-flight robots document is an access-policy check, not an
        # article grant. Redirects remain disabled and every HTTP connection
        # still passes normal URL/DNS/SSRF validation.
        if _ROBOTS_FETCH.get() == url:
            return
        decision = registry.body_decision(url)
        if not decision['eligible']:
            raise SourcePermissionError(decision)
        if not _ROBOTS_FETCH.get():
            robots = registry.robots_decision(url)
            if not robots['eligible']:
                raise SourcePermissionError(robots)


def scoped_user_agent(url):
    registry = _BODY_REGISTRY.get()
    row = registry.match_url(url) if registry is not None else None
    return SOURCE_USER_AGENT if row and row['permission_status'] != 'EXISTING_ROUTE_POLICY' else None


@contextmanager
def paced_source_request(url):
    registry = _BODY_REGISTRY.get()
    if registry is None or _ROBOTS_FETCH.get():
        yield False
        return
    permission = registry.body_decision(url)
    if not permission['eligible']:
        raise SourcePermissionError(permission)
    robots = registry.robots_decision(url)
    if not robots['eligible']:
        raise SourcePermissionError(robots)
    delay = robots.get('crawl_delay_seconds', 0)
    if not delay:
        yield False
        return
    with registry.paced_request(url, delay):
        yield True
