"""
Forensic Reproduction of Known Retrieval Failures in Local JSON Audit
"""
import os
import sys
import json

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def inspect_contaminations():
    base = "artifacts/local_json_audit"
    
    print("=" * 70)
    print("1. BRANDSHIELD REPRODUCTION")
    print("=" * 70)
    with open(os.path.join(base, "brandshield.json"), "r", encoding="utf-8") as f:
        bs = json.load(f)
    print("Brand:", bs.get("brand_name"))
    findings = bs.get("findings", [])
    print(f"Total findings: {len(findings)}")
    for idx, fd in enumerate(findings):
        title = fd.get("title", "")
        summary = fd.get("summary", "")
        url = fd.get("url", "")
        print(f"  [{idx+1}] {title} | is_threat={fd.get('is_threat')} | {url}")
        if any(bad in (title + summary).lower() for bad in ["cibil", "credit score"]):
            print(f"    --> [CONFIRMED CONTAMINATION] Found CIBIL / Credit Score in BrandShield!")

    print("\n" + "=" * 70)
    print("2. SCOUT REPRODUCTION")
    print("=" * 70)
    with open(os.path.join(base, "scout.json"), "r", encoding="utf-8") as f:
        scout = json.load(f)
    sources = scout.get("sources", [])
    print(f"Total sources: {len(sources)}")
    bad_scout_kws = ["bank of baroda", "microsoft teams", "xiaomi", "unesco"]
    for idx, s in enumerate(sources):
        title = s.get("title", "")
        snippet = s.get("snippet", "")
        for bad in bad_scout_kws:
            if bad in (title + snippet).lower():
                print(f"    --> [CONFIRMED CONTAMINATION] Found '{bad}' in Scout evidence: '{title[:70]}' (ID: {s.get('evidence_id')})")

    print("\n" + "=" * 70)
    print("3. PERSONAL WATCH REPRODUCTION")
    print("=" * 70)
    with open(os.path.join(base, "personal_watch.json"), "r", encoding="utf-8") as f:
        pw = json.load(f)
    mentions = pw.get("mentions", [])
    print(f"Total mentions: {len(mentions)}")
    bad_pw_kws = ["chrome", "zhihu", "github"]
    for idx, m in enumerate(mentions):
        title = m.get("title", "")
        snippet = m.get("snippet", "")
        url = m.get("url", "")
        for bad in bad_pw_kws:
            if bad in (title + snippet + url).lower():
                print(f"    --> [CONFIRMED CONTAMINATION] Found '{bad}' in Personal Watch mention: '{title[:70]}' (URL: {url})")

    print("\n" + "=" * 70)
    print("4. CLAIM VERIFICATION REPRODUCTION")
    print("=" * 70)
    with open(os.path.join(base, "claim_verification.json"), "r", encoding="utf-8") as f:
        cv = json.load(f)
    print(f"Claim: {cv.get('claim_text')}")
    print(f"Verdict: {cv.get('verdict')} (Confidence: {cv.get('confidence')})")
    chain = cv.get("evidence_chain", [])
    print(f"Evidence Chain Items: {len(chain)}")
    bad_cv_kws = ["glycemic", "endocrine", "clinical", "trial", "diabetes"]
    for idx, c in enumerate(chain):
        text_str = str(c)
        for bad in bad_cv_kws:
            if bad in text_str.lower():
                print(f"    --> [CONFIRMED CONTAMINATION] Found medical term '{bad}' in Claim Evidence: '{text_str[:70]}'")

    print("\n" + "=" * 70)
    print("5. TRENDING REPRODUCTION")
    print("=" * 70)
    with open(os.path.join(base, "trending.json"), "r", encoding="utf-8") as f:
        tr = json.load(f)
    threats = tr.get("threats", [])
    counts = tr.get("counts", {})
    trends = tr.get("trends", [])
    timeline = tr.get("timeline", [])
    deep_reads = tr.get("retrieval", {}).get("deep_reads", 0)
    print(f"Threats array length: {len(threats)}")
    print(f"Threats with is_threat=True: {sum(1 for t in threats if t.get('is_threat'))}")
    print(f"Threats with is_threat=False: {sum(1 for t in threats if not t.get('is_threat'))}")
    print(f"Reported counts: {counts}")
    print(f"Deep reads executed: {deep_reads}")
    if trends:
        vel = trends[0].get("velocity", {})
        print(f"Velocity status on single run: {vel.get('status')} (Growth pct: {vel.get('growth_rate_pct')}%)")
    if timeline:
        print(f"Timeline entries: {len(timeline)}")
        for idx, t in enumerate(timeline[:3]):
            print(f"  [{idx+1}] time={t.get('timestamp')} | source={t.get('source')} | event={t.get('event')[:60]}")

if __name__ == "__main__":
    inspect_contaminations()
