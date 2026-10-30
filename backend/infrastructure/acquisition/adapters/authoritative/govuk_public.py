"""Documented GOV.UK search/content APIs, agency text only under the OGL.

Search results remain leads. Content requires an observed GOV.UK URL and the
same versioned body/excerpt review used by the ordinary publisher reader.
"""
import json
import hashlib
import re
from urllib.parse import urlencode, urlsplit
from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch
from backend.services.agent_reach.channels import CandidateSource, FetchedDocument, EvidenceFragment


class GovukPublicAdapter(PlatformAdapter):
    platform = 'govuk'
    backend_id = 'govuk_content_api'

    def can_handle(self, candidate):
        parsed = urlsplit(candidate.canonical_url or candidate.url)
        return (parsed.scheme == 'https' and parsed.netloc == 'www.gov.uk'
                and not parsed.query and not parsed.fragment
                and not any(part in {'.', '..'} for part in parsed.path.split('/'))
                and not any(char in parsed.path for char in ('%', '\\'))
                and parsed.path.startswith(('/government/', '/guidance/', '/news/')))

    def discover(self, query, limit=3, *, speeches_only=False):
        from backend.services.research.source_registry import source_registry
        if not source_registry.assess('govuk')['eligible_for_bounded_probe']:
            raise PermissionError('PERMISSION_REQUIRED')
        parameters = {'q': query[:300], 'count': min(3, limit),
                      'fields': 'title,link,description,public_timestamp,format'}
        if speeches_only:
            parameters['filter_format'] = 'speech'
        url = 'https://www.gov.uk/api/search.json?' + urlencode(parameters)
        response = safe_fetch(url, preserve_http_errors=True)
        if response.status_code != 200:
            raise PermissionError('ACCESS_DENIED' if response.status_code in {401, 403} else 'HTTP_' + str(response.status_code))
        results = []
        for row in json.loads(response.body).get('results', [])[:limit]:
            link = row.get('link', '')
            if not isinstance(link, str) or not link.startswith(('/government/', '/guidance/', '/news/')) or link.startswith('//'):
                continue
            candidate = CandidateSource(url='https://www.gov.uk' + link, title=row.get('title', ''),
                snippet=row.get('description', ''), platform='govuk',
                metadata={'discovery_published_at': row.get('public_timestamp'), 'source_family': 'govuk'})
            if self.can_handle(candidate):
                results.append(candidate)
        return results

    def acquire(self, candidate, request):
        from backend.services.research.source_registry import source_registry
        url = candidate.canonical_url or candidate.url
        if not self.can_handle(candidate) or not source_registry.body_decision(url)['eligible']:
            return FetchedDocument(url=url, status='PERMISSION_REQUIRED', backend_id=self.backend_id)
        response = safe_fetch('https://www.gov.uk/api/content' + urlsplit(url).path, preserve_http_errors=True)
        if response.status_code != 200:
            return FetchedDocument(url=url, status='HTTP_' + str(response.status_code), backend_id=self.backend_id)
        payload = json.loads(response.body)
        # Do not accept a mismatched resource, attachment or arbitrary JSON text.
        if not isinstance(payload, dict) or payload.get('base_path') != urlsplit(url).path:
            return FetchedDocument(url=url, status='IDENTITY_MISMATCH', backend_id=self.backend_id)
        details = payload.get('details') if isinstance(payload.get('details'), dict) else {}
        body = details.get('body', '')
        if not isinstance(body, str):
            body = ''
        if re.search(r'all rights reserved|third.party copyright|\u00a9', body, re.I):
            return FetchedDocument(url=url, status='RIGHTS_EXCEPTION_REVIEW_REQUIRED', backend_id=self.backend_id)
        soup = BeautifulSoup(body, 'html.parser')
        for node in soup(['script', 'style']):
            node.decompose()
        from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
        extracted = extract_readable_page(soup)
        text = extracted['text'][:25000]
        permission = source_registry.excerpt_decision(url)
        if not permission['eligible'] or not text:
            return FetchedDocument(url=url, status='BODY_EMPTY_OR_UNAPPROVED', backend_id=self.backend_id)
        links = payload.get('links') if isinstance(payload.get('links'), dict) else {}
        def rows(key):
            value = links.get(key)
            return value[:8] if isinstance(value, list) else []
        organisations = [row['title'][:200] for row in rows('organisations')
                         if isinstance(row, dict) and isinstance(row.get('title'), str)]
        speakers = []
        for row in rows('speaker'):
            if isinstance(row, dict) and isinstance(row.get('title'), str) and row['title'].strip():
                path = row.get('base_path')
                profile = ('https://www.gov.uk' + path if isinstance(path, str)
                           and path.startswith('/government/people/') and not any(c in path for c in ('?', '#', '%', '\\')) else '')
                speakers.append((row['title'].strip()[:150], profile, 'links.speaker'))
        without_profile = details.get('speaker_without_profile')
        if isinstance(without_profile, str) and without_profile.strip():
            speakers.append((BeautifulSoup(without_profile, 'html.parser').get_text(' ', strip=True)[:150], '',
                             'details.speaker_without_profile'))
        unique_names = {name.casefold() for name, _, _ in speakers}
        speaker = speakers[0] if len(unique_names) == 1 else None
        publication = payload.get('first_published_at') if isinstance(payload.get('first_published_at'), str) else ''
        delivery = details.get('delivered_on') if isinstance(details.get('delivered_on'), str) else ''
        page = {key: extracted[key] for key in ('text_blocks', 'body_quality', 'extraction_method', 'headings') if key in extracted}
        page.update(content_scope='GOVUK_CONTENT_API_BODY', published=publication,
                    publisher='GOV.UK', issuing_organisations=organisations, delivered_on=delivery,
                    body_quality={'body_kind': 'ARTICLE_BODY', 'basis': 'CAPTURED_CONTENT_API_BODY', 'evidence_qualified': False})
        page['official_statement'] = {'publisher':'GOV.UK', 'speaker':speaker[0] if speaker else '',
            'issuing_organisations':organisations, 'delivered_on':delivery, 'first_published_at':publication}
        if payload.get('document_type') == 'speech' and speaker and text:
            from backend.services.research.address_provenance import GOVUK_BASIS
            page['published_address'] = {'speaker':speaker[0], 'speaker_profile_url':speaker[1], 'speaker_basis':speaker[2],
                'publisher':'GOV.UK', 'issuing_organisations':organisations, 'delivered_on':delivery,
                'first_published_at':publication, 'document_type':'speech',
                'source_api_url':response.endpoint, 'api_response_sha256':hashlib.sha256(response.body).hexdigest(),
                'start':0, 'end':len(text), 'source_text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'basis':GOVUK_BASIS, 'identity_authenticated':False}
        return FetchedDocument(url=url, status='SUCCESS', backend_id=self.backend_id, raw_content=text,
            raw_metadata={'title': payload.get('title'), 'published': publication,
                'updated': payload.get('public_updated_at'), 'source_family': 'govuk',
                'publisher':'GOV.UK', 'issuing_organisations':organisations,
                'speaker':speaker[0] if speaker else '', 'delivered_on':delivery, 'page_metadata':page,
                'body_truncated':len(extracted['text']) > len(text),
                'source_permission': {**permission, 'author': 'GOV.UK',
                    'licence_url': 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'}})

    def normalize(self, document, candidate, request):
        if document.status != 'SUCCESS':
            return []
        return [EvidenceFragment(platform='govuk', channel_name='expanded_sources', url=document.url,
            title=document.raw_metadata.get('title') or candidate.title, content=document.raw_content,
            snippet=document.raw_content[:350], published=document.raw_metadata.get('published') or '',
            author='', content_depth='OFFICIAL_STATEMENT', retrieval_mode='direct_api',
            native_backend_id=self.backend_id, raw_metadata={**document.raw_metadata,
                'source_role': 'PRIMARY', 'official_source': True, 'source_assertion_only': True})]
