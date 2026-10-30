"""Admit validated document/feed locators to the existing bounded reader."""
import hashlib
from urllib.parse import urlsplit

from backend.services.research.research_models import EvidenceItem


def planned_source_reads(plan, allowed_channels=None):
    """Planning is a read opportunity, never permission or article evidence.

    Only the planner's admitted, identical, validated web/rss READ actions enter
    this lane. The reader rechecks permissions, robots, DNS and all request caps.
    """
    if plan is None:
        return []
    actions = {action.action_id: action for action in plan.actions}
    blocked = {row.get('action_id') for row in plan.runtime_decisions
               if row.get('decision') in {'EXCLUDE', 'DEFER_TEMPORARY'}}
    result, seen = [], set()
    for channel, rows in plan.to_channel_queries().items():
        if channel not in {'web', 'rss'} or allowed_channels is not None and channel not in allowed_channels:
            continue
        for row in rows:
            action = actions.get(row.get('query_id'))
            if (not action or action.action_id in blocked or action.validation_status != 'VALID'
                    or action.operation != 'read' or (channel, row.get('operation'), row.get('query_text'), row.get('query_class')) !=
                    (action.channel, action.operation, action.query, action.source_category)):
                continue
            try:
                url = urlsplit(action.query)
                if url.scheme not in {'https', 'http'} or not url.hostname or url.username or url.password:
                    continue
            except ValueError:
                continue
            if action.query in seen:
                continue
            seen.add(action.query)
            result.append(EvidenceItem(id='planned_' + hashlib.sha256(action.query.encode()).hexdigest()[:16],
                canonical_url=action.query, title='Planned source document', channel=channel,
                query_id=action.action_id, query_class=action.source_category, query_text=plan.claim,
                content_depth='METADATA', source_domain=url.hostname,
                metadata={'source_plan_action_id': action.action_id,
                    'source_kind': 'VALIDATED_PLANNED_SOURCE_READ', 'source_family': action.source_family,
                    **({'discovery_kind': 'FEED_INDEX'} if channel == 'rss' or action.source_category == 'issuer_documents' else {}),
                    'publisher_basis': 'VALIDATED_SOURCE_PLAN_READ',
                    'planned_source_read': True, 'planning_is_not_evidence': True}))
            if len(result) >= 2:
                return result
    return result
