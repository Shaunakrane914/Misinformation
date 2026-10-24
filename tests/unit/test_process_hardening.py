"""Configuration, test isolation and non-destructive validation regressions."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tomllib

import pytest

from backend import __version__
from backend.core.settings import Settings, settings
from backend.db import database
from backend.services.research.replay_ledger import replay_ledger
from scripts.validation import isolated_runtime, validate_rollback_compatibility as rollback
from scripts.validation import verify_frozen_benchmarks as frozen
from scripts.validation import validate_release_candidate_smoke as smoke


def test_test_storage_is_outside_protected_workspace():
    repo = Path(__file__).resolve().parents[2]
    assert not Path(database.SQLITE_DB_PATH).resolve().is_relative_to(repo)
    assert not Path(replay_ledger.storage_dir).resolve().is_relative_to(repo)
    assert database.supabase is None
    assert os.environ["RSS_INGESTION_ENABLED"] == "false"
    assert settings.environment == "test"


def test_offline_guard_blocks_real_loopback_but_allows_internal_socketpair():
    with pytest.raises(socket.gaierror, match="forbids external DNS"):
        socket.getaddrinfo("live-provider.example", 443)
    assert socket.getaddrinfo("127.0.0.1", 443)
    with socket.socket() as connection:
        with pytest.raises(OSError, match="forbids live network"):
            connection.connect(("127.0.0.1", 9))
    left, right = socket.socketpair()
    try:
        left.send(b"x")
        assert right.recv(1) == b"x"
    finally:
        left.close()
        right.close()


@pytest.mark.parametrize("executable", ["gh", "opencli", "twitter-cli", "twitter"])
def test_offline_guard_blocks_provider_clis_with_persisted_local_credentials(executable):
    with pytest.raises(OSError, match="forbids provider network subprocesses"):
        subprocess.run([executable, "search", "must-not-access-network"], check=False)


def test_sqlite_canonical_name_and_legacy_alias(monkeypatch, tmp_path):
    canonical = str(tmp_path / "canonical.db")
    legacy = str(tmp_path / "legacy.db")
    monkeypatch.setenv("SQLITE_DB_PATH", canonical)
    monkeypatch.setenv("AEGIS_SQLITE_PATH", legacy)
    assert Settings(_env_file=None).sqlite_db_path == canonical
    monkeypatch.delenv("SQLITE_DB_PATH")
    assert Settings(_env_file=None).sqlite_db_path == legacy
    assert Settings(sqlite_db_path=canonical, _env_file=None).sqlite_db_path == canonical


def test_database_and_settings_use_same_sqlite_path():
    assert database.SQLITE_DB_PATH == settings.sqlite_db_path


@pytest.mark.parametrize("path", ["", "   ", ":memory:", None])
def test_sqlite_configuration_requires_persistent_file(path):
    with pytest.raises(ValueError, match="persistent file"):
        Settings(sqlite_db_path=path, _env_file=None)


def test_server_credentials_prefer_service_role_and_never_promote_anon(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-only")
    monkeypatch.setenv("SUPABASE_KEY", "legacy-server")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-anon")
    assert Settings(_env_file=None).supabase_write_key == "service-only"
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    assert Settings(_env_file=None).supabase_write_key == "legacy-server"
    monkeypatch.setenv("SUPABASE_KEY", "")
    assert Settings(_env_file=None).supabase_write_key is None


def test_package_api_and_settings_share_version():
    metadata = tomllib.loads((Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8"))
    assert settings.version == __version__ == metadata["project"]["version"]


def test_admin_token_is_optional_but_not_exposed_in_repr(monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "do-not-display")
    cfg = Settings(_env_file=None)
    assert cfg.admin_api_token.get_secret_value() == "do-not-display"
    assert "do-not-display" not in repr(cfg)
    assert "do-not-display" not in cfg.model_dump_json()


def test_production_guard_cannot_be_bypassed_with_case_or_whitespace():
    with pytest.raises(ValueError, match="forbids AEGIS_MOCK_LLM"):
        Settings(environment=" Production ", aegis_mock_llm=True, _env_file=None)
    assert Settings(environment=" Staging ", _env_file=None).environment == "staging"
    with pytest.raises(ValueError, match="ENVIRONMENT must be"):
        Settings(environment="misspelled-production", _env_file=None)


def test_validation_environment_is_isolated_and_blanks_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "must-not-reach-child")
    monkeypatch.setenv("GEMINI_KEY_NEW", "must-not-reach-child")
    environment = isolated_runtime.isolated_environment(tmp_path)
    assert environment["SUPABASE_SERVICE_ROLE_KEY"] == environment["GEMINI_KEY_NEW"] == ""
    assert environment["SQLITE_DB_PATH"] == str(tmp_path / "aegis.db")
    assert environment["AEGIS_DOSSIER_DIR"] == str(tmp_path / "dossiers")
    assert environment["AGENT_REACH_ENABLED"] == environment["RSS_INGESTION_ENABLED"] == "false"
    assert environment["PYTHON_DOTENV_DISABLED"] == "1"


def test_validation_child_does_not_load_parent_dotenv(monkeypatch, tmp_path):
    from dotenv import load_dotenv
    # This synthetic marker is not a credential or real server configuration.
    parent = tmp_path / "parent.env"
    parent.write_text("GEMINI_KEY_PARENT_TEST=synthetic-must-not-load\n", encoding="utf-8")
    monkeypatch.delenv("GEMINI_KEY_PARENT_TEST", raising=False)
    monkeypatch.setattr(isolated_runtime, "find_dotenv", lambda: str(parent))
    environment = isolated_runtime.isolated_environment(tmp_path)
    assert environment["GEMINI_KEY_PARENT_TEST"] == ""
    monkeypatch.setenv("GEMINI_KEY_PARENT_TEST", environment["GEMINI_KEY_PARENT_TEST"])
    load_dotenv(parent)
    assert os.environ["GEMINI_KEY_PARENT_TEST"] == ""


def test_validation_output_never_overwrites_existing_report(tmp_path):
    report = tmp_path / "historical.json"
    isolated_runtime.write_report_exclusively(report, {"historical": True})
    before = report.read_bytes()
    with pytest.raises(FileExistsError):
        isolated_runtime.write_report_exclusively(report, {"replacement": True})
    assert report.read_bytes() == before


def test_smoke_default_does_not_write_artifact(monkeypatch):
    monkeypatch.setattr(smoke, "run_isolated_smoke_validation", lambda: {"verdict": "OFFLINE_SMOKE_PASS"})
    monkeypatch.setattr(smoke, "write_report_exclusively", lambda *args: pytest.fail("Unexpected default report write"))
    assert smoke.main([]) == 0


def test_rollback_rejects_non_commit_baseline_ref():
    with pytest.raises(ValueError, match="commit SHA"):
        rollback._resolve_baseline("--help")


def test_archive_inspection_reports_malformed_records_not_pass(tmp_path):
    (tmp_path / "broken.json").write_text("not json", encoding="utf-8")
    (tmp_path / "wrong.json").write_text(json.dumps({"session_id": "wrong"}), encoding="utf-8")
    result = rollback.inspect_dossier_archive(tmp_path)
    assert result["status"] == "FAIL"
    assert result["counts"]["FAILED"] == 2


def test_frozen_benchmark_verifier_rejects_changed_content(tmp_path):
    target = tmp_path / "tests" / "retrieval_benchmark"
    target.mkdir(parents=True)
    for name in frozen.FROZEN_SHA256:
        shutil.copyfile(frozen.REPO_ROOT / "tests" / "retrieval_benchmark" / name, target / name)
    frozen.verify_frozen_benchmarks(tmp_path)
    with (target / "labels.jsonl").open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(ValueError, match="labels.jsonl"):
        frozen.verify_frozen_benchmarks(tmp_path)


def test_active_ci_covers_all_branches_full_suite_and_frontend():
    workflow = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "push: {}" in workflow and "pull_request: {}" in workflow
    assert "pytest tests/ -q" in workflow
    assert "tests/frontend/test_*.js" in workflow
    assert "verify_frozen_benchmarks.py" in workflow
    assert "fetch-depth: 0" in workflow
