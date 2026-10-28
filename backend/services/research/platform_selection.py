"""Task-aware optional routes within the existing fixed query count.

An implemented legacy scraper is not proof of approved platform access. Keep
explicit skipped states instead of silently dropping the platform inventory.
"""
import os
import re


def select_platform_queries(request, queries, *, capabilities=None):
    from backend.services.agent_reach.native.operation_capabilities import runtime_operation_capabilities
    capabilities = capabilities or runtime_operation_capabilities
    selected, decisions, channels = [], [], set()
    core = {'web', 'news', 'rss'}
    for row in queries:
        channel = row.get('channel')
        if channel in core:
            selected.append(row)
            continue
        reason = None
        if channel == 'reddit':
            # Existing mirror handlers are not an approved official API route.
            reason = ('APPROVED_OFFICIAL_ROUTE_REQUIRED' if os.getenv('REDDIT_APPROVED_ACCESS', '').lower() in {'1', 'true', 'yes'}
                      else 'PERMISSION_REQUIRED')
        elif channel == 'twitter':
            reason = 'APPROVED_OFFICIAL_ROUTE_REQUIRED'
        elif channel == 'youtube':
            reason = 'AUTHORIZED_API_OR_TRANSCRIPT_ROUTE_REQUIRED'
        else:
            decision = capabilities.assess(channel, row.get('operation', 'search'))
            if decision['decision'] in {'EXCLUDE', 'DEFER_TEMPORARY'}:
                reason = decision.get('reason') or decision['decision']
        if not reason and channel in channels:
            reason = 'PLATFORM_DIVERSITY_LIMIT'
        decisions.append({'channel': channel, 'operation': row.get('operation', 'search'),
                          'query_id': row.get('query_id'), 'status': reason or 'SELECTED_NOT_YET_SUBMITTED'})
        if not reason:
            channels.add(channel)
            selected.append(row)
    # Technical communities are relevant only to technical subjects/objectives;
    # they are never universal fallbacks for celebrities or allegations.
    text = request.target + ' ' + request.intent + ' ' + request.extra_params.get('claim_text', '')
    if (re.search(r'\b(?:software|programming|semiconductor|artificial intelligence|openai|nvidia|developer)\b', text, re.I)
            and 'hackernews' not in channels):
        decision = capabilities.assess('hackernews', 'search')
        if decision['decision'] not in {'EXCLUDE', 'DEFER_TEMPORARY'}:
            selected.append({'channel': 'hackernews', 'operation': 'search', 'query_id': 'community_context',
                'query_class': 'community_context', 'query_text': request.target,
                'basis': 'TECHNICAL_TOPIC_COMMUNITY_CONTEXT_NOT_PRIMARY_PROOF'})
    return selected, decisions
