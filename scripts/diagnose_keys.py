from dotenv import load_dotenv
load_dotenv()

import os
import sys

print("=== API Key Diagnostics ===")

print("\nGemini Keys Presence:")
for name in ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY"]:
    print(f"  {name}:", "present" if os.getenv(name) else "missing")

print("\nGemini Connectivity:")
try:
    from google import genai
    keys = [
        ("GEMINI_API_KEY_1", os.getenv("GEMINI_API_KEY_1")),
        ("GEMINI_API_KEY_2", os.getenv("GEMINI_API_KEY_2")),
        ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY")),
    ]
    for name, key in keys:
        if not key:
            print(f"  {name}: skipped (missing)")
            continue
        try:
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(model="gemini-2.0-flash-lite", contents="ping")
            txt = getattr(resp, "text", "")
            print(f"  {name}: OK (chars={len(txt)})")
        except Exception as e:
            print(f"  {name}: FAIL ({e.__class__.__name__}) {e}")
except Exception as e:
    print("  Gemini SDK import failed:", e.__class__.__name__, e)

print("\nSupabase Presence:")
for name in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
    print(f"  {name}:", "present" if os.getenv(name) else "missing")

print("\nSupabase Connectivity:")
try:
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("  Supabase: skipped (missing env)")
    else:
        try:
            client = create_client(url, key)
            resp = client.table("claims").select("id").limit(1).execute()
            count = len(resp.data) if getattr(resp, "data", None) is not None else 0
            print(f"  Supabase: OK (claims rows fetched={count})")
        except Exception as e:
            print(f"  Supabase: FAIL ({e.__class__.__name__}) {e}")
except Exception as e:
    print("  Supabase SDK import failed:", e.__class__.__name__, e)

print("\n=== Diagnostics Complete ===")