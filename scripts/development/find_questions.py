import json
import os

with open(r'C:\Users\Shaunak Rane\.gemini\antigravity-ide\brain\c9705189-73d5-470d-9661-f5c131bdf346\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    lines = []
    for idx, line in enumerate(f):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        c = obj.get('content', '')
        if obj.get('type') in ('USER_INPUT', 'MODEL') and ('17' in c and any(k in c.lower() for k in ['root-cause', 'mandate', 'questions', 'final_report'])):
            lines.append(f"=== IDX {idx} TYPE {obj.get('type')} ===\n")
            for l in c.split('\n'):
                if any(k in l.lower() for k in ['17', 'root-cause', 'mandate', 'final_report', 'question']):
                    lines.append("  " + l + "\n")

out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.scratch'))
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, 'found_questions.txt'), 'w', encoding='utf-8') as out:
    out.writelines(lines)
print(f"Written {len(lines)} lines")
