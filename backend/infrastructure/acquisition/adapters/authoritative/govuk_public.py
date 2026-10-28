"""Documented GOV.UK search/content APIs, agency text only under the OGL.

Search results remain leads. Content requires an observed GOV.UK URL and the
same versioned body/excerpt review used by the ordinary publisher reader.
"""
import json
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

    def discover(self, query, limit=3):
        from backend.services.research.source_registry import source_registry
        if not source_registry.assess('govuk')['eligible_for_bounded_probe']:
            raise PermissionError('PERMISSION_REQUIRED')
        url = 'https://www.gov.uk/api/search.json?' + urlencode({'q': query[:300], 'count': min(3, limit),
            'fields': 'title,link,description,public_timestamp,format'})
        response = safe_fetch(url)
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
        response = safe_fetch('https://www.gov.uk/api/content' + urlsplit(url).path)
        if response.status_code != 200:
            return FetchedDocument(url=url, status='HTTP_' + str(response.status_code), backend_id=self.backend_id)
        payload = json.loads(response.body)
        # Do not accept a mismatched resource, attachment or arbitrary JSON text.
        if payload.get('base_path') != urlsplit(url).path:
            return FetchedDocument(url=url, status='IDENTITY_MISMATCH', backend_id=self.backend_id)
        details = payload.get('details') or {}
        body = details.get('body', '')
        if not isinstance(body, str):
            body = ''
        if re.search(r'all rights reserved|third.party copyright|\u00a9', body, re.I):
            return FetchedDocument(url=url, status='RIGHTS_EXCEPTION_REVIEW_REQUIRED', backend_id=self.backend_id)
        soup = BeautifulSoup(body, 'html.parser')
        for node in soup(['script', 'style']):
            node.decompose()
        text = soup.get_text('\n', strip=True)[:25000]
        permission = source_registry.excerpt_decision(url)
        if not permission['eligible'] or not text:
            return FetchedDocument(url=url, status='BODY_EMPTY_OR_UNAPPROVED', backend_id=self.backend_id)
        return FetchedDocument(url=url, status='SUCCESS', backend_id=self.backend_id, raw_content=text,
            raw_metadata={'title': payload.get('title'), 'published': payload.get('first_published_at'),
                'updated': payload.get('public_updated_at'), 'source_family': 'govuk',
                'source_permission': {**permission, 'author': 'GOV.UK issuing department',
                    'licence_url': 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'}})

    def normalize(self, document, candidate, request):
        if document.status != 'SUCCESS':
            return []
        return [EvidenceFragment(platform='govuk', channel_name='expanded_sources', url=document.url,
            title=document.raw_metadata.get('title') or candidate.title, content=document.raw_content,
            snippet=document.raw_content[:350], published=document.raw_metadata.get('published') or '',
            author='GOV.UK issuing department', content_depth='OFFICIAL_STATEMENT', retrieval_mode='direct_api',
            native_backend_id=self.backend_id, raw_metadata={**document.raw_metadata,
                'source_role': 'PRIMARY', 'official_source': True, 'source_assertion_only': True})]
