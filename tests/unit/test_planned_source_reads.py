"""Existing validated original-source locators must reach the bounded reader."""
from dataclasses import replace
from unittest.mock import patch, Mock
from types import SimpleNamespace

from backend.services.agent_reach.source_planner import SourceAction, SourcePlan, PlanningBudget
from backend.services.research.harvesting import HarvestingEngine, raw_source_type
from backend.services.research.planned_source_reads import planned_source_reads
from backend.services.research.research_profiles import QUICK
from backend.services.agent_reach.channels import RetrievalResult


INDEX = 'https://issuer.example/reports-filings.html'
ARTICLE = 'https://issuer.example/quarter-results.html'


def plan(channel='web', category='issuer_documents', decisions=()):
    action = SourceAction('issuer', 1, channel, 'read', INDEX, category, 'DIRECT_CONTENT',
                          0, 'Synthetic source planning fixture', validation_status='VALID')
    return SourcePlan('control', 'scout', 'Acme', 'Acme financial results', 'financial_integrity',
                      [action], [], PlanningBudget(), runtime_decisions=list(decisions))


def test_validated_reads_are_not_lost_or_relabelled_as_search_results():
    candidate = planned_source_reads(plan())[0]
    assert candidate.canonical_url == INDEX
    assert candidate.metadata['planned_source_read'] is True
    assert candidate.content == '' and not candidate.acquired_id
    assert raw_source_type(candidate) == 'DISCOVERY_LEAD'
    assert not planned_source_reads(plan(), allowed_channels=['news'])
    assert not planned_source_reads(plan(decisions=[{'action_id': 'issuer', 'decision': 'EXCLUDE'}]))


def test_unsafe_unvalidated_and_projection_mismatched_reads_cannot_seed():
    p = plan()
    p.actions[0].validation_status = 'INVALID'
    assert not planned_source_reads(p)
    p = plan()
    with patch.object(p, 'to_channel_queries', return_value={'web': [
            {'query_id': 'issuer', 'operation': 'read', 'query_text': 'https://other.example/',
             'query_class': 'issuer_documents'}]}):
        assert not planned_source_reads(p)
    p = plan()
    p.actions[0].query = 'https://username:password@issuer.example/'
    assert not planned_source_reads(p)


def test_observed_issuer_chain_uses_same_total_read_cap_without_repeating_discovery_fetch():
    class Service:
        def __init__(self):
            self.reads = []

        def retrieve_many(self, *args, **kwargs):
            assert all(row.get('operation') != 'read' for rows in args[0].values() for row in rows)
            return RetrievalResult(query='Acme', domain='financial', fragments=[])

        def read(self, url, **kwargs):
            self.reads.append(url)
            if url == INDEX:
                return {'status': 'success', 'content': 'Issuer index listing original quarterly results. ' * 10,
                    'page_metadata': {'content_scope': 'body_fallback', 'observed_links': [
                        {'url': ARTICLE, 'text': 'Quarterly results release'}]}}
            return {'status': 'success', 'content': 'Acme reported quarterly revenue of USD 20 million. ' * 30,
                'page_metadata': {'title': 'Acme quarterly results', 'content_scope': 'article',
                                  'body_quality': {'body_kind': 'ARTICLE_BODY'}}}
    service = Service()
    profile = replace(QUICK, max_queries=1, max_reads=2, host_spacing_seconds=0)
    with patch('backend.services.agent_reach.source_planner.source_planning_engine.refine_topics', return_value=[]):
        result = HarvestingEngine(service).run('Acme', domain='financial', profile=profile, source_plan=plan())
    assert service.reads == [INDEX, ARTICLE]
    assert result.read_telemetry['attempted'] == 2
    assert len([item for item in result.captures if raw_source_type(item) == 'ARTICLE_BODY']) == 1
    assert result.retrieval_trace['planned_source_reads'][0]['status'] == 'CANDIDATE_ONLY_READER_GATES_PENDING'


def test_original_statement_feed_and_explicit_article_have_different_roles():
    feed = planned_source_reads(plan(channel='rss', category='public_statement_discovery'))[0]
    assert feed.metadata['discovery_kind'] == 'FEED_INDEX'
    article = planned_source_reads(plan(category='direct_source'))[0]
    assert 'discovery_kind' not in article.metadata


def test_planned_source_is_still_denied_by_normal_body_policy():
    service = SimpleNamespace(retrieve_many=lambda *a, **k: RetrievalResult(query='Acme', domain='financial'),
                              read=Mock(side_effect=AssertionError('Source permission cannot be bypassed')))
    with patch('backend.services.research.source_registry.source_registry.body_decision',
               return_value={'eligible': False, 'status': 'PERMISSION_REQUIRED'}), patch(
               'backend.services.agent_reach.source_planner.source_planning_engine.refine_topics', return_value=[]):
        result = HarvestingEngine(service).run('Acme', domain='financial',
            profile=replace(QUICK, max_queries=1, max_reads=1), source_plan=plan())
    service.read.assert_not_called()
    assert result.read_telemetry['attempted'] == 0
