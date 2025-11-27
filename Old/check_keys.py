import os
import sys
import time
import json
from typing import Tuple
import requests
from dotenv import load_dotenv

def load_envs() -> None:
    here = os.path.dirname(__file__)
    load_dotenv(os.path.join(here, "backend", ".env"))
    load_dotenv(os.path.join(here, ".env"))

def check_gemini(key_name: str, key_value: str) -> Tuple[str, str]:
    if not key_value:
        return (key_name, "missing")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key_value}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return (key_name, "ok")
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            msg = r.text[:200]
        return (key_name, f"error {r.status_code}: {msg}")
    except Exception as e:
        return (key_name, f"exception: {e}")

def check_supabase(url: str, key: str) -> Tuple[str, str]:
    if not url or not key:
        return ("SUPABASE", "missing")
    try:
        url_clean = url.strip().strip('"').strip("'").strip('`')
        test = f"{url_clean.rstrip('/')}/rest/v1/raw_claims?select=claim_id&limit=1"
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        r = requests.get(test, headers=headers, timeout=8)
        if r.status_code in (200, 204):
            return ("SUPABASE", "ok")
        try:
            msg = r.json().get("message", "")
        except Exception:
            msg = r.text[:200]
        return ("SUPABASE", f"error {r.status_code}: {msg}")
    except Exception as e:
        return ("SUPABASE", f"exception: {e}")

def main() -> None:
    load_envs()
    def clean(v: str | None) -> str:
        if not v:
            return ""
        return v.strip().strip('"').strip("'")
    keys = {
        "GEMINI_API_KEY_2": clean(os.getenv("GEMINI_API_KEY_2", "")),
        "GEMINI_API_KEY_1": clean(os.getenv("GEMINI_API_KEY_1", "")),
        "GEMINI_API_KEY": clean(os.getenv("GEMINI_API_KEY", "")),
        "RESEARCH_GEMINI_KEY": clean(os.getenv("RESEARCH_GEMINI_KEY", "")),
        "INVESTIGATOR_GEMINI_KEY": clean(os.getenv("INVESTIGATOR_GEMINI_KEY", "")),
    }
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    results = []
    for name, val in keys.items():
        results.append(check_gemini(name, val))
        time.sleep(0.2)
    results.append(check_supabase(supabase_url, supabase_key))

    print("=== Key Validation Results ===")
    for name, status in results:
        print(f"{name}: {status}")

if __name__ == "__main__":
    main()
