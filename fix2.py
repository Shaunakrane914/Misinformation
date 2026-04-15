import os, re

pages = [
    "frontend/trending-agent.html",
    "frontend/scout-agent.html",
    "frontend/personal-watch-agent.html",
    "frontend/brandshield-agent.html",
    "frontend/status.html",
]

for path in pages:
    if not os.path.exists(path):
        print("SKIP: " + path)
        continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        c = f.read()
    orig = c
    c = re.sub(r'<header class=["\x27]navbar["\x27].*?</header>', "", c, flags=re.DOTALL)
    c = re.sub(r'<button[^>]*theme-toggle[^>]*>.*?</button>', "", c, flags=re.DOTALL)
    # strip mojibake noise characters (non-printable non-ascii that crept in)
    c = re.sub(r'[\x80-\xbf][\x80-\xbf]', "", c)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Fixed: " + path)

print("Done")
