"""Bounded entity background, deliberately outside task evidence qualification.

Reuse the existing Wikimedia adapters. No guessed article URL, generated prose,
current-event inference, private biography field or additional request allowance.
"""
import hashlib
import re
import time
from datetime import datetime, timezone


def _name(value):
    return re.sub(r"[^\w]+", " ", str(value).casefold()).strip()


def background_span(content):
    """One exact professional/topic paragraph, excluding sensitive biography.

    No generated replacement or concatenation with invented source offsets.
    Raw captured bytes remain separate from this selected public excerpt.
    """
    safe = []
    private = re.compile(r'\b(?:born|birthday|parents?|spouse|married|children|ancestry|ethnic|religion|sexual|address|phone)\b|@', re.I)
    professional = re.compile(r'\b(?:career|company|chief|executive|business|industry|research|film|cricket|president|minister|automaker|manufactur)\w*', re.I)
    for match in re.finditer(r'[^\n]+', content):
        text = match.group().strip()
        if not text or text.startswith(('#', '=', '**')) or private.search(text):
            continue
        start = match.start() + len(match.group()) - len(match.group().lstrip())
        safe.append((len(professional.findall(text)), len(text.split()), text[:6000], start))
    if not safe:
        return '', 0, 0
    _, _, text, start = max(safe, key=lambda row: (row[0], row[1]))
    return text, start, start + len(text)


def select_entity(candidates, target, aliases=()):
    names = {_name(value) for value in (target, *aliases) if value}
    exact = []
    for candidate in candidates:
        meta = candidate.metadata
        label = meta.get('wiki_title') or meta.get('label') or ''
        if _name(label) in names:
            exact.append(candidate)
    # Do not choose the first plausible namesake or expand ambiguous pages.
    return exact[0] if len(exact) == 1 else None


def acquire_reference_background(request, *, deadline, remaining_reads, adapters=None, cached_captures=()):
    from backend.infrastructure.acquisition.adapters.expanded_catalog import get_expanded_adapters
    from backend.infrastructure.acquisition.adapters.expansion_safety import capture_adapter_fetches
    from backend.infrastructure.acquisition.network.budget import acquisition_deadline, public_request_phase
    from backend.services.agent_reach.channels import RetrievalRequest
    from backend.services.research.research_models import EvidenceItem
    result = {'status': 'NO_ELIGIBLE_BACKGROUND', 'sources': [], 'attempts': [], 'published_words': 0,
              'scope': 'GENERAL_BACKGROUND_ONLY_NOT_TASK_VERIFICATION',
              'as_of': datetime.now(timezone.utc).isoformat()}
    captures = []
    allowed = request.extra_params.get('allowed_channels')
    if allowed is not None and 'expanded_sources' not in allowed:
        result['status'] = 'CHANNEL_RESTRICTED'
        return captures, result
    # A genuine saved/reference capture can be reused without a request or a
    # new acquired ID. Do not depend on a second download to display its bytes.
    from backend.services.research.source_registry import source_registry
    from urllib.parse import unquote, urlsplit
    for item in cached_captures:
        parsed = urlsplit(item.canonical_url)
        label = item.metadata.get('label') or unquote(parsed.path.rsplit('/', 1)[-1]).replace('_', ' ')
        permission = item.metadata.get('source_permission') or {}
        if (parsed.hostname not in {'en.wikipedia.org', 'www.wikidata.org'} or _name(label) != _name(request.target)
                or not item.metadata.get('read_success') or not item.content
                or not permission.get('author') or not permission.get('licence_url')
                or not source_registry.body_decision(item.canonical_url)['eligible']):
            continue
        text, start, end = background_span(item.content)
        if not text:
            continue
        result['sources'].append({'evidence_id': item.id, 'url': item.canonical_url, 'title': item.title,
            'publisher': parsed.hostname, 'published_at': None, 'passage': text, 'word_count': len(text.split()),
            'freshness': 'GENERAL_BACKGROUND', 'source_permission': permission,
            'observation_scope': result['scope'], 'source_body_sha256': hashlib.sha256(item.content.encode()).hexdigest(),
            'start': start, 'end': end})
        result.update(status='AVAILABLE', published_words=len(text.split()), read_attempts=0,
                      acquisition_origin='REUSED_CAPTURE_NO_NEW_REQUEST')
        return captures, result
    if remaining_reads <= 0 or time.monotonic() >= deadline:
        result['status'] = 'BUDGET_EXHAUSTED'
        return captures, result
    from backend.services.research.source_registry import source_registry
    adapters = adapters if adapters is not None else get_expanded_adapters()
    reads = 0
    for key in ('wikipedia', 'wikidata_exec'):
        if reads >= remaining_reads or time.monotonic() >= deadline:
            break
        adapter = adapters[key]
        row = {'source_family': key, 'status': 'DISCOVERED_NOT_TESTED', 'read_attempted': False}
        result['attempts'].append(row)
        try:
            with acquisition_deadline(deadline), public_request_phase('reading'), capture_adapter_fetches() as observed:
                candidates = adapter.discover(request.target, limit=3)
                row['candidate_count'] = len(candidates)
                selected = select_entity(candidates, request.target, request.extra_params.get('entity_aliases', []))
                if selected is None:
                    row['status'] = 'ENTITY_UNRESOLVED_OR_AMBIGUOUS'
                elif not source_registry.body_decision(selected.canonical_url or selected.url)['eligible']:
                    row['status'] = 'PERMISSION_REQUIRED'
                else:
                    reads += 1
                    row['read_attempted'] = True
                    document = adapter.acquire(selected, RetrievalRequest(task_type='READ'))
                    row['status'] = document.status
                    fragments = adapter.normalize(document, selected, RetrievalRequest(task_type='READ'))
                    for fragment in fragments[:1]:
                        permission = fragment.raw_metadata.get('source_permission') or {}
                        if not permission.get('licence_url') or not permission.get('author'):
                            row['status'] = 'MISSING_ATTRIBUTION'
                            continue
                        item = EvidenceItem.from_evidence_fragment(fragment,
                            item_id='ev_reference_' + hashlib.sha256(fragment.url.encode()).hexdigest()[:20],
                            target_name=request.target)
                        item.acquired_id = 'capture_' + hashlib.sha256(item.content.encode()).hexdigest()[:20]
                        item.metadata.update(read_success=True, background_reference_only=True,
                            layer2_eligible=False, post_read_qualification_reason='GENERAL_BACKGROUND_ONLY')
                        captures.append(item)
                        text, start, end = background_span(item.content)
                        if not text:
                            continue
                        result['sources'].append({'evidence_id': item.id, 'url': item.canonical_url,
                            'title': item.title, 'publisher': key, 'published_at': None,
                            'passage': text, 'word_count': len(text.split()), 'freshness': 'GENERAL_BACKGROUND',
                            'observation_scope': result['scope'], 'source_permission': permission,
                            'source_body_sha256': hashlib.sha256(item.content.encode()).hexdigest(),
                            'start': start, 'end': end})
            row['http_observations'] = observed
            if any(o.get('http_status') in {401, 403, 429} for o in observed):
                row['status'] = 'ACCESS_DENIED' if not any(o.get('http_status') == 429 for o in observed) else 'RATE_LIMITED'
                break  # A denial is never a reason to try a second reader.
        except Exception as error:
            row['status'] = type(error).__name__
        if captures:
            break
    result['read_attempts'] = reads
    result['status'] = 'AVAILABLE' if result['sources'] else result['status']
    result['published_words'] = sum(row['word_count'] for row in result['sources'])
    return captures, result
