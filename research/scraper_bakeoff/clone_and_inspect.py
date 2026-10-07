"""
Clone repositories for Scraper Bake-Off and extract inventory metadata.
"""
import os
import subprocess
import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("research/scraper_bakeoff")
REPOS_DIR = BASE_DIR / "repos"
REPORTS_DIR = BASE_DIR / "reports"

REPOSITORIES = [
    # Core / Generic
    {"name": "playwright", "url": "https://github.com/microsoft/playwright.git", "category": "Generic Browser", "language": "TypeScript / Multi-lang"},
    {"name": "playwright-python", "url": "https://github.com/microsoft/playwright-python.git", "category": "Generic Browser", "language": "Python"},
    {"name": "Scrapling", "url": "https://github.com/D4Vinci/Scrapling.git", "category": "Adaptive Scraper", "language": "Python"},
    {"name": "crawlee-python", "url": "https://github.com/apify/crawlee-python.git", "category": "Crawling Framework", "language": "Python"},
    {"name": "scrapy", "url": "https://github.com/scrapy/scrapy.git", "category": "Crawling Framework", "language": "Python"},
    # Platform Specialists
    {"name": "instaloader", "url": "https://github.com/instaloader/instaloader.git", "category": "Instagram Specialist", "language": "Python"},
    {"name": "twscrape", "url": "https://github.com/vladkens/twscrape.git", "category": "X/Twitter Specialist", "language": "Python"},
    {"name": "praw", "url": "https://github.com/praw-dev/praw.git", "category": "Reddit Specialist", "language": "Python"},
    {"name": "yt-dlp", "url": "https://github.com/yt-dlp/yt-dlp.git", "category": "YouTube Specialist", "language": "Python"},
    # Additional Social Candidates
    {"name": "TikTok-Api", "url": "https://github.com/davidteather/TikTok-Api.git", "category": "TikTok Specialist", "language": "Python"},
    {"name": "linkedin_scraper", "url": "https://github.com/joeyism/linkedin_scraper.git", "category": "LinkedIn Specialist", "language": "Python"},
    {"name": "facebook-scraper", "url": "https://github.com/kevinzg/facebook-scraper.git", "category": "Facebook Specialist", "language": "Python"},
]

def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=120)
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except Exception as e:
        return "", str(e), -1

def inspect_repo(repo_path, meta):
    name = meta["name"]
    out, err, code = run_cmd("git rev-parse HEAD", cwd=repo_path)
    commit_sha = out if code == 0 else "UNKNOWN"
    
    out, err, code = run_cmd("git rev-parse --abbrev-ref HEAD", cwd=repo_path)
    branch = out if code == 0 else "UNKNOWN"

    out, err, code = run_cmd("git log -1 --format=%cd --date=iso", cwd=repo_path)
    commit_date = out if code == 0 else "UNKNOWN"

    # Detect license
    license_type = "UNKNOWN"
    for lic_file in ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "LICENSE-MIT", "LICENSE-APACHE"]:
        lp = repo_path / lic_file
        if lp.exists():
            content = lp.read_text(encoding="utf-8", errors="ignore")
            if "MIT" in content:
                license_type = "MIT"
            elif "Apache License, Version 2.0" in content or "Apache-2.0" in content:
                license_type = "Apache-2.0"
            elif "GNU GENERAL PUBLIC LICENSE" in content:
                if "Version 3" in content:
                    license_type = "GPL-3.0"
                else:
                    license_type = "GPL-2.0"
            elif "BSD" in content:
                license_type = "BSD"
            else:
                license_type = "CUSTOM / OTHER"
            break

    # Detect dependencies
    deps = []
    pyproject = repo_path / "pyproject.toml"
    setup_py = repo_path / "setup.py"
    req_txt = repo_path / "requirements.txt"
    pkg_json = repo_path / "package.json"

    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        deps.append("pyproject.toml configured")
    if setup_py.exists():
        deps.append("setup.py configured")
    if req_txt.exists():
        deps.append("requirements.txt configured")
    if pkg_json.exists():
        deps.append("package.json (Node.js) configured")

    # Analyze runtime requirements
    browser_req = "NO"
    if name in ["playwright", "playwright-python", "Scrapling", "crawlee-python", "TikTok-Api"]:
        browser_req = "YES (Chromium / WebKit / Firefox)"
    elif "selenium" in str(deps).lower() or "playwright" in str(deps).lower():
        browser_req = "YES (Browser engine)"

    auth_req = "NONE"
    if name == "praw":
        auth_req = "Reddit Client ID + Secret (Script or Web app)"
    elif name == "twscrape":
        auth_req = "Twitter/X user pool (cookies/tokens) or guest credentials"
    elif name == "instaloader":
        auth_req = "Optional for public profiles; Required for full posts/stories"
    elif name == "linkedin-api":
        auth_req = "LinkedIn Username + Password / Session Cookie (JSESSIONID)"
    elif name == "facebook-scraper":
        auth_req = "Optional for public pages; c_user / xs cookies for groups"

    return {
        "repository": meta["name"],
        "url": meta["url"],
        "category": meta["category"],
        "language": meta["language"],
        "latest_commit": commit_sha,
        "default_branch": branch,
        "last_commit_date": commit_date,
        "license": license_type,
        "dependencies": deps,
        "browser_requirements": browser_req,
        "authentication_requirements": auth_req,
        "storage_requirements": "SQLite / Local Files" if name in ["twscrape", "instaloader"] else "Memory / Cache",
        "proxy_requirements": "Recommended for high volume / rate-limited endpoints",
        "archived": False,
        "maintainers": "Active Community / Organization"
    }

def main():
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    inventory = []

    print("[*] Starting repository cloning and inspection...")
    for item in REPOSITORIES:
        name = item["name"]
        url = item["url"]
        target_path = REPOS_DIR / name

        if not target_path.exists():
            print(f"  -> Cloning {name} from {url}...")
            out, err, code = run_cmd(f"git clone --depth 1 {url} {name}", cwd=REPOS_DIR)
            if code != 0:
                print(f"     [!] Failed to clone {name}: {err}")
                continue
        else:
            print(f"  -> {name} already exists. Inspecting...")

        info = inspect_repo(target_path, item)
        inventory.append(info)
        print(f"     Commit: {info['latest_commit'][:8]} | Branch: {info['default_branch']} | License: {info['license']}")

    output_path = REPORTS_DIR / "repository_inventory.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)

    print(f"\n[+] Repository inventory written to {output_path} ({len(inventory)} repos cataloged).")

if __name__ == "__main__":
    main()
