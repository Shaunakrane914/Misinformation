import os, re

pages = [
    'frontend/trending-agent.html',
    'frontend/scout-agent.html',
    'frontend/personal-watch-agent.html',
    'frontend/brandshield-agent.html',
    'frontend/dashboard.html',
    'frontend/status.html',
]

for path in pages:
    if not os.path.exists(path):
        print(f'SKIP: {path}')
        continue

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    original = content

    # Remove old navbar blocks completely
    content = re.sub(
        r'<header class=["\']navbar["\'].*?</header>',
        '',
        content,
        flags=re.DOTALL
    )
    # Remove theme-toggle buttons
    content = re.sub(
        r'<button[^>]*theme-toggle[^>]*>.*?</button>',
        '',
        content,
        flags=re.DOTALL
    )

    # Fix mojibake: replace all sequences starting with 0xC3 decoded as Windows-1252
    # Common patterns: strip them and replace with clean text equivalents
    mojibake_pairs = [
        # smart quotes and dashes
        ('\u00e2\u0080\u0099', "'"),
        ('\u00e2\u0080\u009c', '"'),
        ('\u00e2\u0080\u009d', '"'),
        ('\u00e2\u0080\u0094', '\u2014'),
        ('\u00c2\u00b7', '\u00b7'),  # middle dot
        ('\u00c2\u00a0', ' '),  # nbsp
        ('\u00c2', ''),  # stray
        ('\u00e2\u0086\u00bb', '\u21bb'),  # refresh arrow
        # strip broken emoji prefixes - these are multi-byte sequences decoded wrong
        # Just strip them; icons come from SVGs now
        ('ðŸŽ¬', ''),
        ('ðŸ¦', ''),
        ('ðŸ"°', ''),
        ('ðŸ"Š', ''),
        ('ðŸ"ˆ', ''),
        ('ðŸ"¸', ''),
        ('ðŸ¤', ''),
        ('ðŸ"¹', ''),
        ('âญ', ''),
        ('ðŸŽ¯', ''),
        ('ðŸš¨', ''),
        ('ðŸ"„', ''),
        ('ðŸ"', ''),
        ('ðŸŒ™', ''),
        ('ðŸ›¡', ''),
        ('ðŸ"¡', ''),
        ('ðŸ'¡', ''),
        ('ðŸ§', ''),
        ('ðŸ"§', ''),
        ('ðŸ'°', ''),
        ('ðŸ"¦', ''),
        ('ðŸ†', ''),
        ('ðŸ¥', ''),
        ('â£', ''),
        ('âœ"', '✓'),
        ('âœ…', ''),
        ('âŒ', 'X'),
        ('âš ', '!'),
        ('âš¡', ''),
        ('â„¹', 'i'),
        ('â†»', '↻'),
        ('â±', ''),
        ('Â·', '·'),
        ('Â', ''),
    ]
    for bad, good in mojibake_pairs:
        content = content.replace(bad, good)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{'Fixed' if content != original else 'No change'}: {path}")

print("Done.")
