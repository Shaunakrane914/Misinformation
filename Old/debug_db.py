import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    print("❌ Error: Credentials missing in .env")
    raise SystemExit(1)

supabase = create_client(url, key)

print("--- Debugging Table: verified_threats ---")
try:
    response = supabase.table("verified_threats").select("*").execute()
    rows = response.data or []
    print(f"Total Rows Found: {len(rows)}")
    if not rows:
        print("⚠️ Table is EMPTY. The ID 1 does not exist.")
    else:
        print("Existing IDs:")
        for row in rows:
            rid = row.get("id")
            evid = row.get("event_id")
            title = row.get("title") or row.get("smoking_gun_headline") or row.get("headline")
            print(f" - ID: {rid} | event_id: {evid} | Title: {title}")
        id1 = [r for r in rows if r.get("id") == 1 or str(r.get("event_id")) == "1"]
        if id1:
            print("✅ Row with ID 1 is present.")
        else:
            print("❌ Row with ID 1 not found.")
except Exception as e:
    print(f"❌ Database Error: {e}")
