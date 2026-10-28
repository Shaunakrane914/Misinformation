"""Explicit restrictions/caps survive fixes to observation and selection defaults."""
from collections import Counter
import pytest
from bs4 import BeautifulSoup
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import EvidenceItem
from backend.services.research.candidate_selection import SelectionContext, score_candidate


@pytest.mark.parametrize('notice,exception', [
    ('Copyright 2026 Publisher. All rights reserved.', False),
    ('Third-party content: All rights reserved.', True),
    ('This article is not covered by the Creative Commons licence.', True),
    ('This article is republished with permission.', True),
])
def test_generic_notice_is_separate_from_explicit_article_exception(notice, exception):
    html = '<article><h1>Observed statement</h1><p>The speaker described the research and reported its limitations.</p></article><footer>' + notice + '</footer>'
    page = extract_readable_page(BeautifulSoup(html, 'html.parser'))
    assert bool(page.get('rights_exception_observed')) is exception
    assert notice in page['raw_text'] and notice not in page['text']
    if 'All rights reserved' in notice:
        assert page['rights_notice_observed'] is True


def clean_budget_env(monkeypatch):
    import os
    for name in list(os.environ):
        if name.startswith(('SERVER_RESEARCH_', 'LOCAL_RESEARCH_', 'RESEARCH_')) or name in {'PORT', 'RENDER', 'SERVER_MODE', 'AEGIS_RESEARCH_PROFILE'}:
            monkeypatch.delenv(name, raising=False)


def test_deep_request_rebases_only_implicit_standard_limits(monkeypatch):
    clean_budget_env(monkeypatch)
    budget = ResearchBudget.from_env()
    assert budget.deep_read_budget == 14
    deep = budget.for_profile('DEEP')
    assert deep.deep_read_budget == 24 and deep.timeout_seconds == 240
    assert budget.deep_read_budget == 14


def test_explicit_server_caps_still_bound_deep_requests(monkeypatch):
    clean_budget_env(monkeypatch)
    monkeypatch.setenv('RENDER', 'true')
    monkeypatch.setenv('SERVER_RESEARCH_MAX_DEEP_READS', '9')
    monkeypatch.setenv('SERVER_RESEARCH_TIMEOUT', '80')
    deep = ResearchBudget.from_env().for_profile('DEEP')
    assert deep.deep_read_budget == 9 and deep.timeout_seconds == 80
    explicit = ResearchBudget(deep_read_budget=3, timeout_seconds=20).for_profile('DEEP')
    assert explicit.deep_read_budget == 3 and explicit.timeout_seconds == 20


def lead(title, host='publisher.example'):
    return EvidenceItem(id=title, title=title, canonical_url='https://' + host + '/original-interview-research-source',
                        snippet=title, content_depth='INDEX_SNIPPET')


def test_person_statement_lead_outranks_executive_speculation_without_qualifying_body():
    ctx = SelectionContext('Aster Quinn', 'personal')
    statement = lead('Aster Quinn interview on research limitations')
    opinion = lead('Who can replace Aster Quinn?')
    rank = lambda item: score_candidate(item, ctx, is_wrapper=False, is_index=False)[0]
    assert rank(statement) > rank(opinion)
    assert statement.content == '' and statement.content_depth == 'INDEX_SNIPPET'


def test_diversity_prefers_comparable_unread_publisher_without_dropping_strong_leads():
    ctx = SelectionContext('battery recycling', 'trending', group_reads=Counter({'first.example': 4}))
    same = lead('Battery recycling research announcement', 'first.example')
    other = lead('Battery recycling research announcement', 'second.example')
    score = lambda item: score_candidate(item, ctx, is_wrapper=False, is_index=False)[0]
    assert score(other) > score(same)
    assert score(same) > score(lead('Unrelated sport result', 'third.example'))


def test_person_queries_keep_the_exact_name_and_distinct_tasks():
    from backend.services.research.harvesting import diversified_queries
    rows = diversified_queries('Aster Quinn', 'personal', specialist_tasks=['PUBLIC_STATEMENT', 'FALSE_QUOTE'])
    assert rows[0]['query_text'] == '"Aster Quinn" interview'
    assert any(row.get('specialist_task') == 'FALSE_QUOTE' for row in rows)


def test_name_only_person_query_prioritizes_interviews_and_keeps_threat_searches():
    from backend.services.research.harvesting import diversified_queries
    rows = diversified_queries('Aster Quinn', 'personal')
    assert rows[0]['query_text'] == '"Aster Quinn" interview'
    assert rows[0]['acquisition_objective'] == 'PUBLIC_STATEMENT'
    assert any(row['acquisition_objective'] == 'IDENTITY_THREAT' for row in rows)


def test_request_timeout_cannot_raise_explicit_server_ceiling(monkeypatch):
    from backend.application.research.harvest_pipeline import run_harvest_pipeline
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_models import ResearchRequest
    observed = []
    class StopAtHarvest(Exception):
        pass
    def harvest(self, **kwargs):
        observed.append(kwargs)
        raise StopAtHarvest
    monkeypatch.setattr(HarvestingEngine, 'run', harvest)
    monkeypatch.setattr('backend.application.research.harvest_pipeline.time.monotonic', lambda: 100.0)
    with pytest.raises(StopAtHarvest):
        run_harvest_pipeline(ResearchRequest(target='Aster Quinn', domain='personal', timeout_seconds=240),
            ResearchBudget(timeout_seconds=37), 'DEEP')
    assert observed[0]['deadline'] == pytest.approx(100.0 + 37 * .90)
