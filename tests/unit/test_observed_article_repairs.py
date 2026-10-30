"""Actual failure shapes: organizational introductions and concise incident tasks."""
import pytest
from backend.services.research.passage_records import _captured_surname_unambiguous, public_statement_attribution
from backend.services.agent_reach.source_planner import SourcePlanningEngine


def test_role_and_organization_intro_is_not_a_competing_given_name():
    body = ('CEO and Chairwoman of General Motors Mary Barra discussed factory changes.\n\n'
            '"Employees will be offered further retraining opportunities," Barra said.')
    record = {'content': body, 'metadata': {'acquisition_objective': 'PUBLIC_STATEMENT'}}
    assert _captured_surname_unambiguous(body, 'Mary Barra')
    assert public_statement_attribution(record, body.split('\n\n')[1], 'Mary Barra') == 'REPORTED_QUOTATION_SURNAME_IN_CAPTURE'


@pytest.mark.parametrize('other', ['Jessica Barra', 'John Mary Barra'])
def test_actual_competing_or_extended_person_name_stays_ambiguous(other):
    body = f'Mary Barra attended. Chairwoman of General Motors {other} also attended.'
    assert not _captured_surname_unambiguous(body, 'Mary Barra')


def test_explicit_brand_research_task_gets_separate_concise_incident_searches():
    task = ('Investigate reported Dyson counterfeit products, phishing promotions and official consumer warnings. '
            'Identify actual documented incidents, relevant dates and source authority.')
    plan = SourcePlanningEngine().plan(task, entity='Dyson', domain='brand', agent='brandshield', use_llm=False)
    assert plan.claim == task
    queries = {a.query for a in plan.actions if a.operation == 'search'}
    assert '"Dyson" counterfeit' in queries and '"Dyson" phishing' in queries


def test_declarative_negated_claim_does_not_take_imperative_shortening_path():
    claim = 'Dyson did not issue a counterfeit warning in 2025.'
    plan = SourcePlanningEngine().plan(claim, entity='Dyson', domain='brand', agent='brandshield', use_llm=False)
    assert any(claim in a.query for a in plan.actions)
    assert '"Dyson" counterfeit' not in {a.query for a in plan.actions}
