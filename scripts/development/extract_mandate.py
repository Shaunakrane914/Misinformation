import json
import os

with open(r'C:\Users\Shaunak Rane\.gemini\antigravity-ide\brain\c9705189-73d5-470d-9661-f5c131bdf346\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        c = obj.get('content', '')
        if 'P0 Retrieval Integrity' in c and 'MISSION' in c:
            print(f"Found at line {idx}, length {len(c)}")
            out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.scratch'))
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, 'full_mission_mandate.txt'), 'w', encoding='utf-8') as out:
                out.write(c)
            break
print("Done searching transcript_full")
