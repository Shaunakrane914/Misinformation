"""Dated, permitted historical reading; never current-trend findings or velocity."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib


def historical_background(captures, target, *, reference_time=None, gate=None):
    from backend.services.research.relevance_gate import relevance_gate
    from backend.services.research.temporal_guard import temporal_guard
    from backend.services.research.source_registry import source_registry
    from backend.services.research.passage_extractor import passage_extractor, has_usable_passage
    gate = gate or relevance_gate
    rows, seen = [], set()
    for original in captures:
        page = original.metadata.get('page_metadata') or {}
        kind = page.get('body_kind') or (page.get('body_quality') or {}).get('body_kind')
        if not original.metadata.get('read_success') or kind != 'ARTICLE_BODY':
            continue
        declared = [node.get('datePublished') for node in page.get('declared_structured_data', [])
                    if isinstance(node, dict) and node.get('@type') in {'Article', 'NewsArticle', 'ReportageNewsArticle', 'BlogPosting'}
                    and node.get('datePublished')]
        if page.get('publication_metadata_conflict') or not (page.get('published') or declared and len(set(declared)) == 1):
            continue
        temporal = temporal_guard.evaluate(original, reference_time=reference_time)
        if temporal.status not in {'STALE', 'SYNDICATED_STALE', 'UPDATED_HISTORICAL_REJECTED'}:
            continue
        permission = source_registry.excerpt_decision(original.canonical_url, page)
        if not permission['eligible']:
            continue
        item = deepcopy(original)
        assessed = gate.evaluate_item(item, target, domain='trending', intent=target,
                                     reference_time=reference_time, historical_context=True)
        if not assessed.is_accepted:
            continue
        # Only this detached background projection skips the current-event
        # requirement. The original capture retains its rejection and identity.
        item.metadata.update(temporal_required=False, historical_background_only=True, layer2_eligible=True)
        passage_extractor.extract_passages([item], target, domain='trending')
        if not has_usable_passage(item):
            continue
        passages = item.metadata.get('evidence_passages') or []
        texts = [p.get('text', '') for p in passages if isinstance(p, dict)]
        texts = texts or [item.relevant_excerpt]
        retained = []
        size = 0
        for text in texts:
            digest = hashlib.sha256(text.encode()).hexdigest()
            if not text or text not in item.content or digest in seen or size + len(text) > 6000:
                continue
            seen.add(digest)
            retained.append(text)
            size += len(text)
            if len(retained) == 4:
                break
        if not retained:
            continue
        rows.append({'evidence_id': item.id, 'url': item.canonical_url, 'title': item.title,
            'publisher': item.source_domain or item.source_name, 'published_at': temporal.published_at_utc,
            'passage': '\n\n'.join(retained), 'freshness': 'OLDER_BACKGROUND',
            'word_count': sum(len(text.split()) for text in retained),
            'source_permission': {'author': permission.get('author') or page.get('author') or '',
                                  'licence_url': permission.get('licence_url') or ''},
            'observation_scope': 'HISTORICAL_SOURCE_PASSAGES_NOT_CURRENT_TREND',
            'source_body_sha256': hashlib.sha256(item.content.encode()).hexdigest()})
    rows.sort(key=lambda row: row['published_at'] or '', reverse=True)
    return {'status': 'AVAILABLE' if rows else 'NO_ELIGIBLE_BACKGROUND',
            'as_of': (reference_time or datetime.now(timezone.utc)).isoformat(),
            'sources': rows[:6], 'published_words': sum(r['word_count'] for r in rows[:6]),
            'scope': 'Older permitted relevant articles; excluded from fresh findings, trend counts and velocity'}
