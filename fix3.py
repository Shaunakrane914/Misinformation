import os, re

pages = [
    "frontend/trending-agent.html",
    "frontend/scout-agent.html",
    "frontend/personal-watch-agent.html",
    "frontend/brandshield-agent.html",
]

for path in pages:
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        c = f.read()

    # Add pt-62 style to first element after body to compensate for fixed navbar
    c = c.replace(
        '<div class="agent-hero"',
        '<div class="agent-hero" style="padding-top:100px;"',
        1
    )
    c = c.replace(
        '<section class="agent-hero"',
        '<section class="agent-hero" style="padding-top:100px;"',
        1
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Fixed nav offset: " + path)

print("Done")
