"""Offline reservation controls; no provider/model calls or real ledger reset."""
import pytest

from backend.infrastructure.llm import advisory_policy as policy


@pytest.fixture(autouse=True)
def isolated_limit(monkeypatch):
    monkeypatch.delenv('AEGIS_AI_DAILY_REQUEST_LIMIT', raising=False)


def reserve_once(identity):
    with policy.investigation_scope(identity), policy.reserve_request('search_suggestion'):
        pass


def test_default_three_is_enforced_by_preflight_and_atomic_reservation(tmp_path):
    path = tmp_path / 'policy.sqlite3'
    with policy.advisory_run(verified_models=[policy.MODEL], database=path, identity='runtime-utc-control'):
        for number in range(3):
            reserve_once('case-' + str(number))
        status = policy.advisory_budget_status(identity='runtime-utc-control', database=path)
        assert status == {'allowed': False, 'calls': 3, 'reason': 'DAILY_REQUEST_BUDGET',
                          'daily_request_limit': 3}
        with policy.investigation_scope('fourth'), pytest.raises(policy.AdvisoryPolicyError):
            with policy.reserve_request('search_suggestion'):
                pytest.fail('Daily allowance cannot be exceeded')
        assert policy.call_count() == 3


def test_increase_to_eight_preserves_existing_calls_and_same_identity(monkeypatch, tmp_path):
    path = tmp_path / 'policy.sqlite3'
    identity = 'runtime-utc-control'
    with policy.advisory_run(verified_models=[policy.MODEL], database=path, identity=identity):
        for number in range(3):
            reserve_once('case-' + str(number))
    monkeypatch.setenv('AEGIS_AI_DAILY_REQUEST_LIMIT', '8')
    status = policy.advisory_budget_status(identity=identity, database=path)
    assert status['allowed'] and status['calls'] == 3 and status['daily_request_limit'] == 8
    with policy.advisory_run(verified_models=[policy.MODEL], database=path, identity=identity):
        assert policy.call_count() == 3
        for number in range(3, 8):
            reserve_once('case-' + str(number))
        assert policy.call_count() == 8
        with policy.investigation_scope('ninth'), pytest.raises(policy.AdvisoryPolicyError):
            with policy.reserve_request('search_suggestion'):
                pytest.fail('Configured shared allowance cannot be exceeded')
    assert policy.advisory_budget_status(identity=identity, database=path)['reason'] == 'DAILY_REQUEST_BUDGET'


@pytest.mark.parametrize('value', ['0', '21', '-1', '1.5', 'invalid', '', '9999'])
def test_invalid_or_above_hard_maximum_fails_closed_without_reservation(monkeypatch, tmp_path, value):
    path = tmp_path / 'policy.sqlite3'
    monkeypatch.setenv('AEGIS_AI_DAILY_REQUEST_LIMIT', value)
    with pytest.raises(policy.AdvisoryPolicyError):
        policy.advisory_budget_status(identity='runtime-utc-control', database=path)
    with policy.advisory_run(verified_models=[policy.MODEL], database=path, identity='runtime-utc-control'):
        with policy.investigation_scope('one'), pytest.raises(policy.AdvisoryPolicyError):
            with policy.reserve_request('search_suggestion'):
                pytest.fail('Invalid config cannot reserve a call')
        assert policy.call_count() == 0


def test_higher_limit_keeps_busy_investigation_and_cooldown_guards(monkeypatch, tmp_path):
    path = tmp_path / 'policy.sqlite3'
    identity = 'runtime-utc-control'
    monkeypatch.setenv('AEGIS_AI_DAILY_REQUEST_LIMIT', '8')
    with policy.advisory_run(verified_models=[policy.MODEL], database=path, identity=identity):
        with policy.investigation_scope('one'):
            with policy.reserve_request('search_suggestion'):
                assert policy.advisory_budget_status(identity=identity, database=path)['reason'] == 'PROVIDER_BUSY'
                with pytest.raises(policy.AdvisoryPolicyError):
                    with policy.reserve_request('passage_suggestion'):
                        pytest.fail('Busy provider must remain unavailable')
            assert policy.advisory_budget_status(identity=identity, database=path)['reason'] == 'INVESTIGATION_REQUEST_BUDGET'
            with pytest.raises(policy.AdvisoryPolicyError):
                with policy.reserve_request('passage_suggestion'):
                    pytest.fail('One call per investigation remains enforced')
        policy.set_cooldown(60)
        with policy.investigation_scope('two'):
            assert policy.advisory_budget_status(identity=identity, database=path)['reason'] == 'PROVIDER_COOLDOWN'
            with pytest.raises(policy.AdvisoryPolicyError):
                with policy.reserve_request('search_suggestion'):
                    pytest.fail('Existing provider cooldown remains enforced')
        assert policy.call_count() == 1
