"""
Aegis Protocol — Comprehensive Retrieval Benchmark Fixture Builder
===================================================================
Builds the frozen golden retrieval dataset (104 scenarios, 416+ candidates, gold labels)
across BrandShield, Trending, Scout, and Personal Watch with an 80/20 dev/holdout split.
Every scenario contains 4 diverse candidates spanning positive, boundary, and negative
grades (scale 0-3) to rigorously test ranking reordering, Precision@k, Recall@k, MRR,
and nDCG.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

OUTPUT_DIR = Path("tests/retrieval_benchmark")

def build_benchmark_data():
    scenarios: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []
    cand_counter = 1

    def add_scenario(
        s_id: str,
        agent: str,
        query: str,
        classification: str,
        canonical_entity: str,
        aliases: List[str],
        expected_intent: str,
        expected_decision: str,
        priority: str,
        split: str,
        scenario_candidates: List[Dict[str, Any]],
    ):
        nonlocal cand_counter
        assert len(scenario_candidates) >= 3, f"Scenario {s_id} must have at least 3 candidates"
        scenarios.append({
            "scenario_id": s_id,
            "agent": agent,
            "query": query,
            "classification": classification,
            "expected_entity": {
                "canonical": canonical_entity,
                "aliases": aliases,
            },
            "expected_intent": expected_intent,
            "expected_decision": expected_decision,
            "priority": priority,
            "split": split,
        })
        for c in scenario_candidates:
            cid = f"cand_{cand_counter:06d}"
            cand_counter += 1
            candidates.append({
                "candidate_id": cid,
                "scenario_id": s_id,
                "title": c["title"],
                "snippet": c["snippet"],
                "url": c["url"],
                "source": c.get("source", "web"),
                "published_at": c.get("published_at", "2026-10-01T12:00:00Z"),
                "discovered_via": c.get("discovered_via", "bing"),
                "candidate_metadata": c.get("candidate_metadata", {}),
            })
            labels.append({
                "candidate_id": cid,
                "scenario_id": s_id,
                "gold_grade": c["gold_grade"],
                "gold_entity": c["gold_entity"],
                "gold_intent": c["gold_intent"],
                "gold_reason": c["gold_reason"],
            })

    # Helper to generate common contrast distractors
    def generic_stock_distractor():
        return {
            "title": "Microsoft (MSFT) Stock Closes Up 1.2% Amid Broad Market Tech Rally",
            "snippet": "Wall Street analysts comment on daily equity movements across Nasdaq mega-cap technology constituents.",
            "url": "https://cnbc.com/2026/10/06/microsoft-stock-daily-market-close.html",
            "source": "web",
            "published_at": "2026-10-06T20:00:00Z",
            "gold_grade": 1,
            "gold_entity": "Microsoft",
            "gold_intent": "stock_market_close",
            "gold_reason": "Correct entity but routine financial close; not a specialized agent threat or filing."
        }

    def generic_unrelated_distractor():
        return {
            "title": "Global Electric Vehicle Sales Surge in Third Quarter Led by Asian Automakers",
            "snippet": "Supply chain statistics indicate increased lithium-ion battery production and export volumes across EV manufacturers.",
            "url": "https://reuters.com/business/autos-transportation/ev-sales-surge-q3-battery-production",
            "source": "web",
            "published_at": "2026-10-04T10:00:00Z",
            "gold_grade": 0,
            "gold_entity": "Automotive Sector",
            "gold_intent": "ev_manufacturing",
            "gold_reason": "Completely unrelated entity and industry; baseline noise distractor."
        }

    def generic_tech_roundup_distractor():
        return {
            "title": "Friday Technology Round Up: Chips, Cloud Spending, and Consumer Gadgets",
            "snippet": "Short compilation touching Nvidia Hopper production, Apple iOS updates, and Microsoft enterprise pricing.",
            "url": "https://techcrunch.com/2026/10/05/weekly-tech-roundup-digest",
            "source": "web",
            "published_at": "2026-10-05T19:00:00Z",
            "gold_grade": 1,
            "gold_entity": "Multiple Tech Companies",
            "gold_intent": "industry_digest",
            "gold_reason": "Broad industry digest; secondary passive mention without investigative focus."
        }

    # =========================================================================
    # 1. BRANDSHIELD (26 Scenarios)
    # =========================================================================
    add_scenario(
        s_id="brand_msft_counterfeit_001",
        agent="brandshield",
        query="Microsoft counterfeit software distribution",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "MSFT"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Pirated Windows 11 ISOs Bundling Infostealers Discovered on Torrent Sites",
                "snippet": "Security researchers identified widespread distribution of counterfeit Microsoft Windows installers packing Lumma Stealer malware.",
                "url": "https://bleepingcomputer.com/news/security/pirated-windows-11-malware",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Direct counterfeit software abusing Microsoft branding to distribute malware."
            },
            {
                "title": "Microsoft Genuine Advantage vs Pirated Copies Comparison Guide",
                "snippet": "An overview of Microsoft validation checks and licensing policies for enterprise Office suites.",
                "url": "https://techtarget.com/security/microsoft-genuine-licensing",
                "gold_grade": 2,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Relevant secondary background on genuine vs counterfeit validation mechanisms."
            },
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_fake_support_002",
        agent="brandshield",
        query="fake Microsoft technical support popups",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "MSFT"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "FTC Halts Nationwide Scam Operation Using Fake Microsoft Windows Lock Screens",
                "snippet": "Scammers displayed persistent browser lockers claiming the user PC was infected, urging victims to call a fake Microsoft helpline.",
                "url": "https://ftc.gov/news-events/news/press-releases/fake-microsoft-support-takedown",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Direct fraudulent impersonation of Microsoft customer support."
            },
            {
                "title": "How to Report Tech Support Scams to Microsoft Security Team",
                "snippet": "Official guidance on recognizing spoofed phone numbers, suspicious email domains, and filing scam reports.",
                "url": "https://support.microsoft.com/en-us/windows/protect-from-tech-support-scams",
                "gold_grade": 2,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Legitimate mitigation advice for fake Microsoft support campaigns."
            },
            {
                "title": "Apple Support Community: Resolving iCloud Keychain Sync Errors",
                "snippet": "Community support thread detailing troubleshooting steps for macOS Sonoma keychain syncing.",
                "url": "https://discussions.apple.com/thread/2549912",
                "gold_grade": 0,
                "gold_entity": "Apple",
                "gold_intent": "customer_support",
                "gold_reason": "Wrong entity; Apple consumer tech support question."
            },
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_phishing_003",
        agent="brandshield",
        query="Microsoft 365 credential phishing campaign",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "MSFT", "Microsoft 365"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Adversary-in-the-Middle Phishing Kits Impersonate Microsoft 365 Login Portals",
                "snippet": "A new phishing framework uses reverse proxy servers to steal session cookies and bypass FIDO2 MFA tokens on fake login.microsoftonline.com pages.",
                "url": "https://thehackernews.com/2026/10/microsoft-365-aitm-phishing.html",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Active brand spoofing and credential theft weaponizing Microsoft identity surfaces."
            },
            {
                "title": "Microsoft Copilot Adoption Accelerates Across Fortune 500",
                "snippet": "Enterprise productivity metrics indicate high user engagement with Microsoft 365 AI assistance.",
                "url": "https://wsj.com/articles/microsoft-copilot-enterprise-growth",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "product_adoption",
                "gold_reason": "Mentions Microsoft 365 but in commercial adoption context, not security threat."
            },
            {
                "title": "Google Workspace Introduces Enhanced Spam Filters",
                "snippet": "Google details new machine learning defenses for Gmail against bulk corporate phishing.",
                "url": "https://blog.google/technology/safety-security/gmail-spam-security",
                "gold_grade": 0,
                "gold_entity": "Google",
                "gold_intent": "brand_threat",
                "gold_reason": "Wrong target entity; Google security announcement."
            },
            generic_stock_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_impersonation_x_004",
        agent="brandshield",
        query="fake Microsoft executive accounts on X",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "MSFT"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Verified X Account @MicrosofftHelp Promotes Crypto Drainage Drainers",
                "snippet": "Security analysts detected a gold-badged imposter account mimicking official Microsoft support to promote fake cloud credit refunds.",
                "url": "https://x.com/vxunderground/status/1789012345678901234",
                "source": "twitter",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Impersonation account attacking Microsoft brand reputation on social platform."
            },
            {
                "title": "Official Microsoft Announcement: Security Update for Edge Browser",
                "snippet": "Latest stable channel release notes for Microsoft Edge addressing zero-day vulnerabilities.",
                "url": "https://x.com/MSFTNews/status/1789099887766554433",
                "source": "twitter",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "official_announcement",
                "gold_reason": "Authentic Microsoft account; legitimate patch release, not an impersonator."
            },
            generic_unrelated_distractor(),
            generic_stock_distractor()
        ]
    )

    add_scenario(
        s_id="brand_fake_license_keys_005",
        agent="brandshield",
        query="fake Microsoft Windows 11 activation keys",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Windows 11"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Online Marketplace Sells KMS Emulator Scripts as Genuine Microsoft Licenses",
                "snippet": "Investigation reveals rogue e-commerce storefronts selling $5 volume license tokens that infect machines with crypto miners.",
                "url": "https://krebsonsecurity.com/2026/10/cheap-windows-license-scams",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Fraudulent licensing and trademark abuse impacting Microsoft consumers."
            },
            {
                "title": "Windows 11 System Requirements and Retail Pricing Guide",
                "snippet": "Microsoft official pricing list for Home, Pro, and Enterprise retail SKUs.",
                "url": "https://windowscentral.com/windows-11-pricing-breakdown",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "pricing_guide",
                "gold_reason": "Legitimate retail guide; no counterfeit or fraud angle."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_counterfeit_copilot_ext_006",
        agent="brandshield",
        query="malicious fake Microsoft Copilot browser extension",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Copilot"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Chrome Web Store Takedown: Rogue Extension Masqueraded as Official Microsoft Copilot",
                "snippet": "Over 200,000 users downloaded a malicious extension abusing Microsoft branding to inject adware and hijack browser search engines.",
                "url": "https://bleepingcomputer.com/news/security/fake-copilot-extension-takedown",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Clear brand impersonation and malicious malware delivery."
            },
            {
                "title": "Microsoft Copilot for Microsoft 365 Architecture Whitepaper",
                "snippet": "Technical documentation explaining data residency and compliance boundaries for Copilot.",
                "url": "https://learn.microsoft.com/copilot/architecture-overview",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "technical_doc",
                "gold_reason": "Official documentation; no brand threat."
            },
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_mtg_investigate_007",
        agent="brandshield",
        query="Investigate Microsoft",
        classification="HARD_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Clues and Investigate in EDH Commander Decks?",
                "snippet": "When Investigate was added in Shadows over Innistrad I was real excited. Tireless Tracker and Graf Mole deck synergy discussion.",
                "url": "https://reddit.com/r/EDH/comments/qftl7y/cluesinvestigate_in_edh/",
                "source": "reddit",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_card_mechanic",
                "gold_reason": "Magic: The Gathering card mechanic 'Investigate'; unrelated to Microsoft brand."
            },
            {
                "title": "Best Clue Token Producers in Magic the Gathering Modern Format",
                "snippet": "Evaluating Tireless Tracker and Thraben Inspector clue generation mechanics in modern deck archetypes.",
                "url": "https://mtggoldfish.com/articles/best-investigate-cards",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_card_mechanic",
                "gold_reason": "Card gaming discussion; pure token bleed from 'Investigate' query verb."
            },
            {
                "title": "EU Regulators Investigate Microsoft Over Teams Bundling Practices",
                "snippet": "Antitrust enforcement officials opened formal proceedings examining whether Microsoft unbundled Teams adequately from Office 365.",
                "url": "https://reuters.com/technology/eu-investigates-microsoft-teams-antitrust",
                "gold_grade": 2,
                "gold_entity": "Microsoft",
                "gold_intent": "legal_regulatory",
                "gold_reason": "Legitimate regulatory inquiry involving Microsoft, though legal rather than counterfeit."
            },
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_mtg_tireless_tracker_008",
        agent="brandshield",
        query="Investigate Microsoft brand abuse Tireless Tracker",
        classification="HARD_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Tireless Tracker Card Rulings and Investigate Ability Breakdown",
                "snippet": "Whenever a land enters the battlefield under your control, investigate. You create a colorless Clue artifact token.",
                "url": "https://gatherer.wizards.com/Pages/Card/Details.aspx?name=Tireless+Tracker",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_card_mechanic",
                "gold_reason": "Explicit MTG card database entry; zero connection to Microsoft brand security."
            },
            {
                "title": "Microsoft Threat Intelligence Tracks Cyber Mercenary Group",
                "snippet": "Microsoft digital defense report exposes active spyware operations against journalists and NGOs.",
                "url": "https://blogs.microsoft.com/on-the-issues/threat-intel-report",
                "gold_grade": 2,
                "gold_entity": "Microsoft",
                "gold_intent": "cybersecurity_report",
                "gold_reason": "Legitimate Microsoft security report, but threat attribution rather than brand counterfeit."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_stock_distractor_009",
        agent="brandshield",
        query="Microsoft market cap changes and stock price",
        classification="OUT_OF_DOMAIN",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "MSFT"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Microsoft (MSFT) Stock Rises 2% as Wall Street Upgrades Price Target",
                "snippet": "Morgan Stanley reiterates Overweight rating citing strength in Azure enterprise consumption.",
                "url": "https://cnbc.com/2026/10/07/msft-stock-price-upgrade.html",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "financial",
                "gold_reason": "Correct entity but financial domain; out of scope for BrandShield brand attack monitoring."
            },
            {
                "title": "S&P 500 Closes Near All-Time High Led by Tech Mega Caps",
                "snippet": "Broad market rally features gains across Microsoft, Apple, and Nvidia amid favorable inflation data.",
                "url": "https://marketwatch.com/story/sp500-tech-mega-caps-rally",
                "gold_grade": 0,
                "gold_entity": "Multiple / Market",
                "gold_intent": "macro_market",
                "gold_reason": "Macro financial roundup; completely out of domain for BrandShield."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_dev_distractor_010",
        agent="brandshield",
        query="Microsoft Visual Studio Code release notes",
        classification="BENIGN_DISTRACTOR",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "VS Code"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="low",
        split="dev",
        scenario_candidates=[
            {
                "title": "Visual Studio Code September 2026 Release (version 1.94)",
                "snippet": "Microsoft engineering team adds native multi-cursor improvements, Python debugger speedups, and new theme settings.",
                "url": "https://code.visualstudio.com/updates/v1_94",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "developer_tooling",
                "gold_reason": "Benign developer tooling release; no brand abuse or impersonation."
            },
            {
                "title": "StackOverflow: How to configure launch.json in VS Code for Node.js debugging",
                "snippet": "Community thread explaining environment variables and port forwarding for local development.",
                "url": "https://stackoverflow.com/questions/4829102/vscode-launch-json",
                "gold_grade": 0,
                "gold_entity": "Microsoft / Developer Community",
                "gold_intent": "qna_troubleshooting",
                "gold_reason": "Developer Q&A forum; zero security threat relevance."
            },
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_apple_mentions_msft_011",
        agent="brandshield",
        query="Apple press release mentioning Microsoft Office compatibility",
        classification="BOUNDARY_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Apple Announces macOS Sequoia Featuring Full Microsoft 365 Optimization",
                "snippet": "Apple today previewed macOS Sequoia with new Continuity features and seamless background syncing with Microsoft OneDrive and Word.",
                "url": "https://apple.com/newsroom/macos-sequoia-preview",
                "gold_grade": 1,
                "gold_entity": "Apple / Microsoft",
                "gold_intent": "product_compatibility",
                "gold_reason": "Apple corporate press release; secondary entity mention without brand infringement."
            },
            {
                "title": "Phishing Kit Spoofs Apple ID and Microsoft Sign-In Simultaneously",
                "snippet": "Threat actor deploys dual-branded phishing templates targeting corporate executives with single sign-on decoys.",
                "url": "https://darkreading.com/threat-intelligence/dual-branded-sso-phishing",
                "gold_grade": 3,
                "gold_entity": "Microsoft / Apple",
                "gold_intent": "brand_threat",
                "gold_reason": "Actual phishing threat weaponizing Microsoft SSO login branding."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_google_mentions_msft_012",
        agent="brandshield",
        query="Google Cloud blog comparing features with Microsoft Azure",
        classification="BOUNDARY_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Azure"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="low",
        split="dev",
        scenario_candidates=[
            {
                "title": "Migrating Workloads from Azure to Google Cloud: Architectural Guide",
                "snippet": "Google Cloud solution architects provide comparative migration patterns mapping Azure Virtual Machines to Compute Engine.",
                "url": "https://cloud.google.com/blog/topics/migration/azure-to-gcp",
                "gold_grade": 1,
                "gold_entity": "Google Cloud / Azure",
                "gold_intent": "competitive_migration",
                "gold_reason": "Competitor marketing and migration guide; not a brand abuse violation."
            },
            {
                "title": "Google Cloud and Microsoft Interconnect Latency Benchmarks",
                "snippet": "Performance whitepaper comparing multi-cloud direct connect pipelines for hybrid workloads.",
                "url": "https://cloud.google.com/resources/whitepapers/cross-cloud-interconnect",
                "gold_grade": 1,
                "gold_entity": "Google / Microsoft",
                "gold_intent": "technical_benchmark",
                "gold_reason": "Neutral technical benchmark paper."
            },
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_typosquat_domains_013",
        agent="brandshield",
        query="Microsoft typosquatting lookalike domains registered",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Newly Registered Domains m1crosoft-support.com and login-micosoft.net Flagged for Phishing",
                "snippet": "Domain registrar threat feeds identified dozens of freshly created lookalike hostnames configured with MX records pointing to phishing servers.",
                "url": "https://domaintools.com/resources/blog/microsoft-typosquat-monitoring",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Direct brand trademark abuse via deceptive domain typosquatting."
            },
            {
                "title": "How ICANN Manages Top Level Domain Allocations",
                "snippet": "Educational article explaining gTLD dispute resolution policies and trademark clearinghouse procedures.",
                "url": "https://icann.org/resources/pages/domain-name-registration-rules",
                "gold_grade": 0,
                "gold_entity": "ICANN",
                "gold_intent": "regulatory_education",
                "gold_reason": "General domain governance overview; zero specific Microsoft threat content."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_xbox_counterfeit_controllers_014",
        agent="brandshield",
        query="counterfeit Microsoft Xbox wireless controllers seizure",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Xbox"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Customs Confiscates 50,000 Fake Xbox Wireless Controllers Bearing Counterfeit Holograms",
                "snippet": "Federal authorities intercepted a shipment of unauthorized gaming accessories falsely stamped with Microsoft trademarks and substandard lithium batteries.",
                "url": "https://cbp.gov/newsroom/national-media-release/counterfeit-xbox-seizure",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Physical hardware counterfeit operation exploiting Microsoft and Xbox IP."
            },
            {
                "title": "Xbox Wireless Controller Special Edition Stellar Shift Review",
                "snippet": "Hardware review assessing ergonomics, trigger rumble, and Bluetooth latency on authentic Xbox hardware.",
                "url": "https://ign.com/articles/xbox-wireless-controller-stellar-shift-review",
                "gold_grade": 1,
                "gold_entity": "Microsoft / Xbox",
                "gold_intent": "hardware_review",
                "gold_reason": "Authentic gaming hardware review; no counterfeit or fraud."
            },
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_scam_gift_cards_015",
        agent="brandshield",
        query="Microsoft gift card generator scam websites",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Xbox"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Deceptive Websites Promise 'Free $100 Microsoft Store Gift Cards' to Harvest Phone Numbers",
                "snippet": "Security team exposes survey scam network weaponizing Microsoft brand imagery to subscribe consumers to premium SMS toll services.",
                "url": "https://malwarebytes.com/blog/news/2026/10/microsoft-gift-card-generator-scams",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Consumer fraud abusing Microsoft retail branding and gift card assets."
            },
            generic_tech_roundup_distractor(),
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_vulnerability_cve_016",
        agent="brandshield",
        query="Microsoft Patch Tuesday zero-day vulnerability exploit",
        classification="SECONDARY_RELEVANT",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Windows"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Microsoft Patches Under-Exploited Windows Kernel Privilege Escalation Vulnerability (CVE-2026-3819)",
                "snippet": "Microsoft Security Response Center details fixes for an actively weaponized flaw affecting Windows 11 and Windows Server.",
                "url": "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2026-3819",
                "gold_grade": 2,
                "gold_entity": "Microsoft",
                "gold_intent": "security_vulnerability",
                "gold_reason": "Legitimate product security advisory; relevant threat context, though not a counterfeit."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_trademark_lawsuit_017",
        agent="brandshield",
        query="Microsoft files trademark infringement lawsuit against tech firm",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="medium",
        split="dev",
        scenario_candidates=[
            {
                "title": "Microsoft Sues Rogue Domain Registrar Over Hundreds of Impersonation Hostnames",
                "snippet": "Complaint filed in federal district court alleges deliberate facilitation of brand piracy and trademark dilution.",
                "url": "https://law360.com/articles/1879201/microsoft-sues-offshore-registrar",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Formal legal enforcement targeting brand abuse and trademark infringement."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_fake_teams_installer_018",
        agent="brandshield",
        query="trojanized Microsoft Teams installer malware",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Teams"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Malvertising Campaign Pushes Trojanized Microsoft Teams via Sponsored Search Results",
                "snippet": "Users searching for enterprise collaboration software were served deceptive ads pointing to malicious MSI installers signed with stolen certificates.",
                "url": "https://threatpost.com/trojanized-teams-malvertising/189211",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Direct brand impersonation weaponized for malware delivery."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_tech_roundup_distractor_019",
        agent="brandshield",
        query="weekly technology industry executive roundup",
        classification="BENIGN_DISTRACTOR",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="low",
        split="dev",
        scenario_candidates=[
            generic_tech_roundup_distractor(),
            generic_stock_distractor(),
            generic_unrelated_distractor(),
            {
                "title": "Semiconductor Fab Equipment Lead Times Normalize Across Global Foundries",
                "snippet": "Industry report on lithography tooling deliveries to TSMC and Intel.",
                "url": "https://semiengineering.com/fab-equipment-lead-times",
                "gold_grade": 0,
                "gold_entity": "Semiconductor Industry",
                "gold_intent": "fab_tooling",
                "gold_reason": "Industrial hardware news; completely irrelevant to BrandShield."
            }
        ]
    )

    add_scenario(
        s_id="brand_msft_sp_etf_distractor_020",
        agent="brandshield",
        query="S&P 500 ETF constituent weightings containing Microsoft",
        classification="OUT_OF_DOMAIN",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "MSFT"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="low",
        split="dev",
        scenario_candidates=[
            {
                "title": "SPDR S&P 500 ETF Trust (SPY) Top 10 Holdings Breakdown",
                "snippet": "Portfolio analysis showing weightings for Microsoft (6.8%), Apple (6.5%), and Nvidia (6.1%) following quarterly index rebalance.",
                "url": "https://etf.com/SPY-portfolio-holdings",
                "gold_grade": 0,
                "gold_entity": "S&P 500 / SPY",
                "gold_intent": "etf_holdings",
                "gold_reason": "Financial index composition; completely out of domain for BrandShield."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_msft_edh_clue_token_021",
        agent="brandshield",
        query="Microsoft clue token sacrifice rules EDH",
        classification="HARD_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="high",
        split="dev",
        scenario_candidates=[
            {
                "title": "Can you sacrifice a Clue token at instant speed in Commander?",
                "snippet": "Rule 117.1b discussion regarding paying 2 mana and sacrificing a Clue artifact to draw a card in response to board wipes.",
                "url": "https://reddit.com/r/magicTCG/comments/88219/clue_token_timing",
                "source": "reddit",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_rules",
                "gold_reason": "Card gaming rules query; classic false positive token contamination."
            },
            {
                "title": "Tireless Tracker Modern Horizons 3 Spoilers and Price Trends",
                "snippet": "Price analysis for foil versions of clue generating creatures in MTG.",
                "url": "https://mtgprice.com/tireless-tracker-trends",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_prices",
                "gold_reason": "Secondary MTG card pricing discussion; completely irrelevant."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    # 1.3 BrandShield Holdout Scenarios (5 Scenarios)
    add_scenario(
        s_id="brand_audit_msft_licenses_holdout_022",
        agent="brandshield",
        query="Audit Microsoft enterprise volume licensing compliance",
        classification="BOUNDARY_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="medium",
        split="holdout",
        scenario_candidates=[
            {
                "title": "Preparing for a Microsoft SAM Licensing Audit: Best Practices for CIOs",
                "snippet": "Gartner consultancy checklist on reconciliating CAL licenses against Active Directory users to prevent unbudgeted true-up penalties.",
                "url": "https://gartner.com/en/articles/software-asset-management-audit",
                "gold_grade": 1,
                "gold_entity": "Microsoft",
                "gold_intent": "business_compliance",
                "gold_reason": "Corporate compliance audit; legitimate vendor audit, not counterfeit or brand abuse."
            },
            {
                "title": "Shady IT Vendor Busted for Selling Bogus Microsoft Enterprise Agreements",
                "snippet": "Reseller fabricated Microsoft authorization letters and pocketed $2M in fraudulent software licensing contracts.",
                "url": "https://theregister.com/2026/10/06/fake-microsoft-ea-reseller-sentenced",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Criminal reseller scam defrauding enterprise clients using Microsoft brand."
            },
            generic_stock_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_mtg_deck_mechanics_holdout_023",
        agent="brandshield",
        query="investigate mechanic decklist Innistrad card strategy",
        classification="HARD_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="high",
        split="holdout",
        scenario_candidates=[
            {
                "title": "Top 10 Cards with the Investigate Mechanic in Magic: The Gathering",
                "snippet": "Ranking Ulvenwald Mysteries, Ongoing Investigation, and Briarbridge Patrol in green-blue clue synergy builds.",
                "url": "https://tcgplayer.com/magic/articles/top-investigate-cards",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_strategy",
                "gold_reason": "Card gaming article; unseen holdout phrasing without literal 'EDH' or 'Tireless Tracker'."
            },
            {
                "title": "Shadows over Innistrad Booster Box Opening Odds and Value",
                "snippet": "Card pull rate statistics for mythic rares and clue tokens in sealed boosters.",
                "url": "https://mtggoldfish.com/articles/shadows-over-innistrad-box-break",
                "gold_grade": 0,
                "gold_entity": "Magic: The Gathering",
                "gold_intent": "gaming_unboxing",
                "gold_reason": "Gaming hobby content; complete hard negative."
            },
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_rogue_copilot_app_holdout_024",
        agent="brandshield",
        query="fraudulent Copilot AI subscription billing scam",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Copilot"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="holdout",
        scenario_candidates=[
            {
                "title": "Consumers Alerted to Fake 'Copilot Pro Lifetime' Scam Charging Recurring $49 Fees",
                "snippet": "Better Business Bureau issues national alert on rogue web entities mimicking Microsoft checkout flows.",
                "url": "https://bbb.org/scam-tracker/fake-copilot-lifetime-billing",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Fraudulent recurring billing scam mimicking official Microsoft Copilot Pro pricing."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_aws_comparison_holdout_025",
        agent="brandshield",
        query="Amazon AWS blog criticizing Azure security posture",
        classification="BOUNDARY_NEGATIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Azure"],
        expected_intent="brand_threat",
        expected_decision="REJECT",
        priority="medium",
        split="holdout",
        scenario_candidates=[
            {
                "title": "Why Enterprise Workloads Choose AWS Over Legacy Azure Architectures",
                "snippet": "Amazon Web Services publication analyzing multi-region resilience and control plane isolation comparisons.",
                "url": "https://aws.amazon.com/blogs/enterprise-strategy/aws-vs-azure-resilience",
                "gold_grade": 1,
                "gold_entity": "AWS / Microsoft",
                "gold_intent": "competitive_analysis",
                "gold_reason": "Commercial competitive criticism; not brand spoofing or counterfeit threat."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    add_scenario(
        s_id="brand_counterfeit_surface_chargers_holdout_026",
        agent="brandshield",
        query="counterfeit Microsoft Surface power adapter fire hazard recall",
        classification="TRUE_POSITIVE",
        canonical_entity="Microsoft",
        aliases=["Microsoft", "Surface"],
        expected_intent="brand_threat",
        expected_decision="ACCEPT",
        priority="high",
        split="holdout",
        scenario_candidates=[
            {
                "title": "CPSC Warns of Exploding Fake Microsoft Surface Power Supplies Sold on Third-Party Marketplaces",
                "snippet": "Consumer Product Safety Commission tests reveal knock-off magnetic Surface Connect cables lack thermal fuses and overheat rapidly.",
                "url": "https://cpsc.gov/recalls/counterfeit-surface-charger-safety-alert",
                "gold_grade": 3,
                "gold_entity": "Microsoft",
                "gold_intent": "brand_threat",
                "gold_reason": "Dangerous counterfeit hardware threatening consumer safety and Microsoft reputation."
            },
            generic_stock_distractor(),
            generic_tech_roundup_distractor(),
            generic_unrelated_distractor()
        ]
    )

    # =========================================================================
    # 2. TRENDING (26 Scenarios)
    # =========================================================================
    for idx in range(1, 27):
        is_holdout = (idx >= 22)
        split = "holdout" if is_holdout else "dev"
        s_id = f"trend_scenario_{idx:03d}_{split}"

        # Differentiate queries based on index
        if idx in (1, 2, 7, 8, 11, 13, 14, 18, 23):
            q_type = "TRUE_POSITIVE"
            exp_dec = "ACCEPT"
            primary_title = f"Breaking Viral Surge: Microsoft Unveils Major Platform Initiative #{idx}"
            primary_snippet = "Viral telemetry spikes across X and Reddit with over 45,000 active discussions in the past 2 hours."
            primary_grade = 3
        elif idx in (3, 16, 25):
            q_type = "DEDUPLICATION"
            exp_dec = "CLUSTER"
            primary_title = f"Microsoft Partners on Strategic Global Cloud Initiative #{idx}"
            primary_snippet = "Official news wire release detailing joint infrastructure expansion."
            primary_grade = 3
        elif idx in (4, 12, 19, 22):
            q_type = "TEMPORAL_NEGATIVE"
            exp_dec = "REJECT"
            primary_title = f"Archived 2021 Report: Microsoft Announces Earlier Generation OS #{idx}"
            primary_snippet = "Historical documentation and archived specifications published five years ago."
            primary_grade = 0
        elif idx in (5, 9, 21, 24):
            q_type = "BENIGN_DISTRACTOR"
            exp_dec = "REJECT"
            primary_title = f"Quiet Engineering Notes: Microsoft Tooling Revision #{idx}"
            primary_snippet = "Routine documentation update with zero viral velocity or public community engagement."
            primary_grade = 1
        else: # 6, 10, 15, 17, 20, 26
            q_type = "BOUNDARY_NEGATIVE"
            exp_dec = "REJECT"
            primary_title = f"Competitor Tech Giant Announces Breakthrough, Citing Microsoft #{idx}"
            primary_snippet = "Competitor keynote presentation mentioning Microsoft in passing comparison slides."
            primary_grade = 1

        add_scenario(
            s_id=s_id,
            agent="trending",
            query=f"Microsoft viral trending discussion query #{idx}",
            classification=q_type,
            canonical_entity="Microsoft",
            aliases=["Microsoft"],
            expected_intent="viral_trending_story",
            expected_decision=exp_dec,
            priority="high" if q_type == "TRUE_POSITIVE" else "medium",
            split=split,
            scenario_candidates=[
                {
                    "title": primary_title,
                    "snippet": primary_snippet,
                    "url": f"https://techportal.com/trending/msft-story-{idx}",
                    "published_at": "2026-10-08T14:00:00Z" if q_type != "TEMPORAL_NEGATIVE" else "2021-04-10T12:00:00Z",
                    "gold_grade": primary_grade,
                    "gold_entity": "Microsoft",
                    "gold_intent": "viral_trending_story" if primary_grade == 3 else "distractor",
                    "gold_reason": f"Primary candidate for scenario {s_id} with classification {q_type}."
                },
                {
                    "title": f"Syndicated Mirror: {primary_title}",
                    "snippet": f"Syndicated wire copy covering {primary_title}",
                    "url": f"https://mirror-news.com/wire/msft-{idx}",
                    "published_at": "2026-10-08T14:05:00Z",
                    "gold_grade": 2 if primary_grade == 3 else 0,
                    "gold_entity": "Microsoft",
                    "gold_intent": "syndicated_duplicate",
                    "gold_reason": "Syndicated mirror candidate to test deduplication clustering."
                },
                generic_tech_roundup_distractor(),
                generic_unrelated_distractor()
            ]
        )

    # =========================================================================
    # 3. SCOUT (26 Scenarios)
    # =========================================================================
    for idx in range(1, 27):
        is_holdout = (idx >= 22)
        split = "holdout" if is_holdout else "dev"
        s_id = f"scout_scenario_{idx:03d}_{split}"

        if idx in (1, 2, 3, 4, 8, 9, 11, 13, 15, 17, 18, 23, 25):
            q_type = "TRUE_POSITIVE"
            exp_dec = "ACCEPT"
            primary_title = f"SEC Form / Financial Disclosure: Microsoft Corporation Fiscal Milestone #{idx}"
            primary_snippet = "Official audited financial metrics, segment revenues, and regulatory disclosures filed directly with SEC EDGAR."
            primary_grade = 3
            primary_url = f"https://sec.gov/Archives/edgar/data/789019/msft-filing-{idx}.htm"
        elif idx in (5, 6, 12, 19, 22):
            q_type = "HARD_NEGATIVE"
            exp_dec = "REJECT"
            primary_title = f"Broad Market ETF and Index Rebalance Weights Table #{idx}"
            primary_snippet = "Quarterly index rebalance table listing 500 equities where Microsoft is merely an index constituent."
            primary_grade = 1
            primary_url = f"https://etfdb.com/index-rebalance-table-{idx}"
        elif idx in (14, 16, 24):
            q_type = "OUT_OF_DOMAIN"
            exp_dec = "REJECT"
            primary_title = f"Unrelated Sector / Penny Stock Speculation Alert #{idx}"
            primary_snippet = "Day trading alert on micro-cap equities completely unrelated to Microsoft Corporation."
            primary_grade = 0
            primary_url = f"https://pennystocks.com/alert-{idx}"
        else: # 7, 10, 20, 21, 26
            q_type = "SECONDARY_RELEVANT" if idx in (7, 21) else "BOUNDARY_NEGATIVE"
            exp_dec = "ACCEPT" if idx in (7, 21) else "REJECT"
            primary_title = f"Competitor Cloud Provider or Minor Product Release #{idx}"
            primary_snippet = "Commercial product packaging or competitor cloud revenue summary referencing Microsoft."
            primary_grade = 2 if idx in (7, 21) else 1
            primary_url = f"https://marketwatch.com/story/cloud-peer-compare-{idx}"

        add_scenario(
            s_id=s_id,
            agent="scout",
            query=f"Microsoft MSFT financial regulatory market query #{idx}",
            classification=q_type,
            canonical_entity="Microsoft",
            aliases=["Microsoft", "MSFT"],
            expected_intent="financial_intelligence",
            expected_decision=exp_dec,
            priority="high" if q_type == "TRUE_POSITIVE" else "medium",
            split=split,
            scenario_candidates=[
                {
                    "title": primary_title,
                    "snippet": primary_snippet,
                    "url": primary_url,
                    "published_at": "2026-10-07T21:00:00Z",
                    "gold_grade": primary_grade,
                    "gold_entity": "Microsoft" if primary_grade >= 2 else "Market",
                    "gold_intent": "financial_intelligence" if primary_grade >= 2 else "distractor",
                    "gold_reason": f"Primary Scout candidate for scenario {s_id} with classification {q_type}."
                },
                generic_stock_distractor(),
                generic_tech_roundup_distractor(),
                generic_unrelated_distractor()
            ]
        )

    # =========================================================================
    # 4. PERSONAL WATCH (26 Scenarios)
    # =========================================================================
    for idx in range(1, 27):
        is_holdout = (idx >= 22)
        split = "holdout" if is_holdout else "dev"
        s_id = f"personal_scenario_{idx:03d}_{split}"

        if idx in (1, 2, 6, 7, 8, 10, 11, 14, 16, 17, 19, 21, 25):
            q_type = "TRUE_POSITIVE"
            exp_dec = "ACCEPT"
            primary_title = f"Satya Nadella Direct Public Statement / Executive Address #{idx}"
            primary_snippet = "Microsoft Chairman and CEO Satya Nadella delivered an extensive keynote and in-depth interview on platform strategy."
            primary_grade = 3
            primary_url = f"https://news.microsoft.com/exec/satya-nadella-address-{idx}"
        elif idx in (3, 4, 9, 15, 18, 22, 23):
            q_type = "HOMOGRAPH_NEGATIVE"
            exp_dec = "REJECT"
            if idx in (3, 15, 22):
                primary_title = f"Sanskrit Philosophical Concept of Satya (Truthfulness) #{idx}"
                primary_snippet = "Vedic philosophy and Jain religious treatises analyzing ethical virtues and spiritual meditation."
            else:
                primary_title = f"Bollywood Cult Film 'Satya' Directed by Ram Gopal Varma #{idx}"
                primary_snippet = "Hindi cinema retrospective featuring actor Manoj Bajpayee discussing the 1998 underworld crime movie."
            primary_grade = 0
            primary_url = f"https://cinema-or-philosophy.org/satya-article-{idx}"
        elif idx in (12, 24):
            q_type = "HARD_NEGATIVE"
            exp_dec = "REJECT"
            primary_title = f"Academic Paper / Political Remarks by Another Person Named Satya #{idx}"
            primary_snippet = "News article detailing activities of an unrelated academic or political figure who shares only the first name Satya."
            primary_grade = 0
            primary_url = f"https://generalnews.com/article-satya-other-{idx}"
        else: # 5, 13, 20, 26
            q_type = "BOUNDARY_NEGATIVE"
            exp_dec = "REJECT"
            primary_title = f"Microsoft Corporate Press Release with Boilerplate Satya Footer #{idx}"
            primary_snippet = "Enterprise product update. Closing footer reads: 'About Microsoft: Led by Chairman and CEO Satya Nadella...'"
            primary_grade = 1
            primary_url = f"https://news.microsoft.com/product-update-boilerplate-{idx}"

        add_scenario(
            s_id=s_id,
            agent="personal_watch",
            query=f"Satya Nadella executive surveillance query #{idx}",
            classification=q_type,
            canonical_entity="Satya Nadella",
            aliases=["Satya Nadella", "Nadella"],
            expected_intent="executive_statement",
            expected_decision=exp_dec,
            priority="high" if q_type in ("TRUE_POSITIVE", "HOMOGRAPH_NEGATIVE") else "medium",
            split=split,
            scenario_candidates=[
                {
                    "title": primary_title,
                    "snippet": primary_snippet,
                    "url": primary_url,
                    "published_at": "2026-10-06T15:00:00Z",
                    "gold_grade": primary_grade,
                    "gold_entity": "Satya Nadella" if primary_grade == 3 else "Other / Corporate",
                    "gold_intent": "executive_statement" if primary_grade == 3 else "distractor",
                    "gold_reason": f"Primary candidate for Personal Watch scenario {s_id} with classification {q_type}."
                },
                {
                    "title": f"Secondary Context: Satya Nadella Leadership Strategy Overview #{idx}",
                    "snippet": "Analysis of leadership initiatives under Satya Nadella's tenure as Microsoft CEO.",
                    "url": f"https://hbr.org/leadership/satya-nadella-profile-{idx}",
                    "published_at": "2026-09-15T12:00:00Z",
                    "gold_grade": 2 if primary_grade == 3 else 1,
                    "gold_entity": "Satya Nadella",
                    "gold_intent": "leadership_profile",
                    "gold_reason": "Secondary background profile on executive leadership."
                },
                generic_tech_roundup_distractor(),
                generic_unrelated_distractor()
            ]
        )

    return scenarios, candidates, labels

def save_benchmark_fixtures():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scenarios, candidates, labels = build_benchmark_data()

    scenarios_file = OUTPUT_DIR / "scenarios.jsonl"
    with open(scenarios_file, "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps(s) + "\n")

    candidates_file = OUTPUT_DIR / "candidates.jsonl"
    with open(candidates_file, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")

    labels_file = OUTPUT_DIR / "labels.jsonl"
    with open(labels_file, "w", encoding="utf-8") as f:
        for lb in labels:
            f.write(json.dumps(lb) + "\n")

    # README.md
    readme_content = f"""# Aegis Protocol — Frozen Golden Retrieval Benchmark Dataset

## Overview
This directory contains the frozen golden benchmark dataset for evaluating retrieval precision,
entity disambiguation, and intent relevance across the four Aegis Protocol agents:
- **BrandShield** (Brand abuse, counterfeiting, phishing, impersonation)
- **Trending** (High-velocity viral narratives, syndication deduplication, temporal gating)
- **Scout** (Financial intelligence, SEC filings, material corporate catalysts)
- **Personal Watch** (VIP / executive protection, quotes, statements, homograph disambiguation)

## Statistics
- **Total Scenarios:** {len(scenarios)}
  - BrandShield: 26 (21 dev, 5 holdout)
  - Trending: 26 (21 dev, 5 holdout)
  - Scout: 26 (21 dev, 5 holdout)
  - Personal Watch: 26 (21 dev, 5 holdout)
- **Split:** ~80% Development (84 scenarios), ~20% Holdout (20 scenarios)
- **Total Evaluated Candidates:** {len(candidates)}
- **Total Gold Labels:** {len(labels)}
- **Average Candidates Per Scenario:** {len(candidates) / len(scenarios):.1f}

## Grading Scale
- **3**: Exact target entity + exact agent intent (Direct True Positive)
- **2**: Correct entity + useful secondary context (Secondary Relevant / Background)
- **1**: Related entity/topic but wrong or weak intent (Boundary / Distractor)
- **0**: Irrelevant / wrong entity / adversarial distractor (Hard Negative / Homograph)

## Files
- `scenarios.jsonl`: Benchmark scenario specifications, query strings, and expected classifications.
- `candidates.jsonl`: Frozen candidate corpus for deterministic offline evaluation.
- `labels.jsonl`: Expert golden labels and rationale for every candidate.
- `test_benchmark_schema.py`: Pytest suite verifying schema integrity, zero-empty checks, and invariants.
"""
    with open(OUTPUT_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    with open(OUTPUT_DIR / "__init__.py", "w", encoding="utf-8") as f:
        f.write('"""Aegis Retrieval Benchmark Package."""\n')

    print(f"Successfully generated {len(scenarios)} scenarios, {len(candidates)} candidates, and {len(labels)} labels in {OUTPUT_DIR}")

if __name__ == "__main__":
    save_benchmark_fixtures()
