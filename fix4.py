import os, re

pages = [
    "frontend/trending-agent.html",
    "frontend/scout-agent.html",
    "frontend/personal-watch-agent.html",
    "frontend/brandshield-agent.html",
    "frontend/status.html",
    "frontend/index.html",
    "frontend/about.html",
    "frontend/agents.html",
    "frontend/submit.html",
    "frontend/dashboard.html",
]

# Remaining mojibake: UTF-8 bytes misread as Win1252
# 0xE2 0x80 0x94 = em-dash, decoded as Win1252 = â€" 
pairs = [
    ("\u00e2\u20ac\u201d", "\u2014"),   # em dash
    ("\u00e2\u20ac\u2122", "'"),         # right single quote
    ("\u00e2\u20ac\u0153", '"'),         # left double quote
    ("\u00e2\u20ac\u009d", '"'),         # right double quote
    ("\u00e2\u20ac\u201c", " - "),       # en dash
    ("\u00c2\u00b7", "\u00b7"),          # middle dot
    ("\u00c2\u00a0", " "),               # nbsp
    ("\u00c2", ""),                       # stray prefix
    ("\u00e2\u0080\u0099", "'"),
    ("\u00e2\u0080\u009c", '"'),
    ("\u00e2\u0080\u009d", '"'),
    ("\u00e2\u0080\u0094", "\u2014"),
    ("\u00e2\u0080\u0093", "\u2013"),
    ("â€™", "'"),
    ("â€œ", '"'),
    ("â€", '"'),
    ("â€\x94", "\u2014"),
    ("â€"", "\u2014"),
    ("Â·", "\u00b7"),
    ("Â", ""),
]

for path in pages:
    if not os.path.exists(path):
        print("SKIP: " + path)
        continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        c = f.read()
    orig = c
    for bad, good in pairs:
        c = c.replace(bad, good)
    if c != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Fixed: " + path)
    else:
        print("Clean: " + path)

print("Done")
