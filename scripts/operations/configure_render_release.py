"""Preview or explicitly apply non-secret production settings; never deploy.

Uses single-variable PUTs, never replaces the secret-bearing environment list.
API keys/provider credentials stay in memory and out of reports/errors.
"""
import argparse
import json
import re
from pathlib import Path
import urllib.error
import urllib.request

from dotenv import dotenv_values

EXPECTED_ENV = {
    "ENVIRONMENT": "production", "AEGIS_ENV": "production", "AEGIS_MOCK_LLM": "false",
    "RSS_INGESTION_ENABLED": "false", "ALLOWED_ORIGIN": "https://aegis-protocol-110.pages.dev",
    "GEMINI_MODELS": '["gemini-3.5-flash-lite"]', "DEFAULT_MODEL": "gemini-3.5-flash-lite",
    "LLM_ADVISORY_MODEL": "gemini-3.5-flash-lite",
}


def configure(client, service_id, apply=False):
    if not re.fullmatch(r"srv-[a-z0-9]+", service_id):
        raise ValueError("Invalid service identifier")
    base = "services/" + service_id
    service = client("GET", base)
    repo = str(service.get("repo", "")).rstrip("/").removesuffix(".git").casefold()
    if (repo != "https://github.com/shaunakrane914/misinformation" or service.get("branch") != "main"
            or (service.get("serviceDetails") or {}).get("url") != "https://misinformation-1ouh.onrender.com"
            or service.get("suspended") != "not_suspended"):
        raise ValueError("Target identity/branch/state mismatch; no configuration changed")
    rows = client("GET", base + "/env-vars?limit=100")
    if len(rows) >= 100:
        raise ValueError("Environment pagination requires explicit review; no configuration changed")
    env = {r["envVar"]["key"]: r["envVar"].get("value", "") for r in rows}
    drift = [key for key, value in EXPECTED_ENV.items() if env.get(key) != value]
    health_drift = (service.get("serviceDetails") or {}).get("healthCheckPath") != "/api/healthz"
    changed = []
    if apply:
        for key in drift:
            client("PUT", base + "/env-vars/" + key, {"value": EXPECTED_ENV[key]})
            changed.append(key)
        if health_drift:
            client("PATCH", base, {"serviceDetails": {"healthCheckPath": "/api/healthz"}})
    return {"mode": "APPLIED_PENDING_DEPLOYMENT" if apply else "READ_ONLY_PREVIEW",
            "service_id": service_id, "branch": service["branch"], "auto_deploy": service.get("autoDeploy"),
            "configuration_drift": drift, "health_check_drift": health_drift, "changed_nonsecret_keys": changed,
            "previous_nonsecret_values": {key: env.get(key) for key in drift},
            "expected_nonsecret_values": EXPECTED_ENV,
            "admin_api_token_configured": bool(env.get("ADMIN_API_TOKEN")),
            "secret_values_in_report": False, "deployment_triggered_by_script": False,
            "limitations": ["Service-level variables only; linked environment groups are not inventoried.",
                            "Missing admin token leaves privileged writes disabled; this script never creates or changes credentials.",
                            "Applying settings is not proof that a running deployment has loaded them."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Explicitly authorized non-secret environment and health-path updates")
    parser.add_argument("--report", type=Path, required=True, help="New report path; existing files are never overwritten")
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Report exists; use a fresh output path")
    key = dotenv_values(args.env_file).get("RENDER_API_KEY")
    if not key:
        parser.error("Server-side Render credential unavailable")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("Credential-bearing API redirect refused")

    opener = urllib.request.build_opener(NoRedirect())

    def client(method, path, data=None):
        request = urllib.request.Request("https://api.render.com/v1/" + path,
            data=json.dumps(data).encode() if data is not None else None, method=method,
            headers={"Authorization": "Bearer " + key, "Accept": "application/json", "Content-Type": "application/json"})
        try:
            with opener.open(request, timeout=8) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ValueError("API response exceeds read bound")
                return json.loads(raw)
        except urllib.error.HTTPError as error:
            raise RuntimeError("Render API request failed (HTTP " + str(error.code) + "); no retry") from None

    try:
        report = configure(client, args.service_id, args.apply)
    except Exception as error:
        # Do not serialize upstream response bodies, request objects or secrets.
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__,
                          "note": "Configuration can be partially applied; re-run read-only preview before continuing."}))
        return 1
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
