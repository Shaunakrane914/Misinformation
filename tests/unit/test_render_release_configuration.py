import copy
import pytest
from scripts.operations.configure_render_release import configure, EXPECTED_ENV


def fixture():
    service = {"repo": "https://github.com/Shaunakrane914/Misinformation", "branch": "main",
               "suspended": "not_suspended", "autoDeploy": "yes",
               "serviceDetails": {"url": "https://misinformation-1ouh.onrender.com", "healthCheckPath": ""}}
    env = {"GEMINI_API_KEY": "private-test-secret", "SUPABASE_SERVICE_ROLE_KEY": "private-db-secret"}
    calls = []
    def client(method, path, data=None):
        calls.append((method, path, data))
        if method == "GET" and "env-vars" not in path:
            return copy.deepcopy(service)
        if method == "GET":
            return [{"envVar": {"key": k, "value": v}} for k, v in env.items()]
        if method == "PUT":
            env[path.rsplit("/", 1)[-1]] = data["value"]
        if method == "PATCH":
            service["serviceDetails"].update(data["serviceDetails"])
        return {}
    return service, env, calls, client


def test_preview_is_read_only_and_does_not_expose_credentials():
    _, _, calls, client = fixture()
    report = configure(client, "srv-test")
    assert all(c[0] == "GET" for c in calls)
    assert "private-test-secret" not in str(report) and "private-db-secret" not in str(report)
    assert set(report["configuration_drift"]) == set(EXPECTED_ENV)


def test_apply_preserves_provider_credentials_and_never_bulk_replaces_or_deploys():
    service, env, calls, client = fixture()
    configure(client, "srv-test", apply=True)
    assert env["GEMINI_API_KEY"] == "private-test-secret"
    assert env["SUPABASE_SERVICE_ROLE_KEY"] == "private-db-secret"
    assert all(env[k] == v for k, v in EXPECTED_ENV.items())
    assert service["serviceDetails"]["healthCheckPath"] == "/api/healthz"
    assert not any(path.endswith(("/deploys", "/env-vars")) and method != "GET" for method, path, _ in calls)
    assert configure(client, "srv-test")["configuration_drift"] == []


def test_wrong_target_fails_before_environment_reads_or_writes():
    service, _, calls, client = fixture()
    service["branch"] = "unrelated"
    with pytest.raises(ValueError, match="Target identity"):
        configure(client, "srv-test", apply=True)
    assert len(calls) == 1
