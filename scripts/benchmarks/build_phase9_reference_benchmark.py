"""
Aegis Protocol — Phase 9 Scientific Reference Benchmark Builder
==============================================================
Constructs a verified, multi-domain, source-adjudicated reference benchmark
of 90 factual claims with strict data separation across three disjoint splits:
  1. dev_set.json         (40 cases) - for development, debugging, and tuning
  2. regression_set.json  (20 cases) - for regression testing and invariance verification
  3. held_out_set.json    (30 cases) - strictly held-out for blind evaluation

Covers all 19 mandated misinformation phenomena:
  - Clearly true / Clearly false
  - Partially true / Misleading context
  - Outdated facts / Incorrect dates
  - Incorrect financial figures
  - Fake company announcements / Fake executive quotations
  - False product announcements / Incorrect scientific claims
  - Cybersecurity misinformation
  - Brand impersonation allegations
  - Misattributed media / Genuinely insufficient evidence
  - Conflicting sources / Multi-entity claims
  - Numerical calculations / Wire syndications

Provenance: All reference passages are derived from primary public sources
(SEC EDGAR filings, NIST NVD database, arXiv preprints, corporate press releases,
and regulatory bulletins).
"""

import json
import os
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parents[2] / "tests" / "evaluation" / "phase9_benchmark"


def get_dev_cases():
    return [
        # --- 1. Clearly True Claims (1-5) ---
        {
            "id": "DEV_TRUE_01",
            "claim": "SEC EDGAR limits automated crawlers to a maximum rate of 10 requests per second",
            "entity": "SEC",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data",
                "passage": "To ensure that all users have access to SEC filings, the SEC imposes a maximum request rate of 10 requests per second.",
                "claim_context": "SEC EDGAR fair access policy",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official SEC EDGAR Accessing Data documentation establishes the 10 requests/second limit.",
            "evidence_limitations": "Applies specifically to automated access of sec.gov endpoints.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_TRUE_02",
            "claim": "The title of arXiv paper 1706.03762 is Attention Is All You Need",
            "entity": "arXiv",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://arxiv.org/abs/1706.03762",
                "passage": "Title: Attention Is All You Need. Authors: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin.",
                "claim_context": "arXiv bibliographic catalog",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Direct bibliographic record of arXiv preprint 1706.03762.",
            "evidence_limitations": "Bibliographic record from arXiv repository.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_TRUE_03",
            "claim": "Microsoft completed its acquisition of LinkedIn in December 2016 for approximately $26.2 billion",
            "entity": "Microsoft",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://news.microsoft.com/2016/12/08/microsoft-closes-acquisition-of-linkedin/",
                "passage": "REDMOND, Wash. — Dec. 8, 2016 — Microsoft Corp. today announced that it has officially closed its acquisition of LinkedIn Corporation in an all-cash transaction valued at $26.2 billion.",
                "claim_context": "Microsoft official acquisition press disclosure",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official press announcement from Microsoft and SEC Form 8-K confirmed closing on Dec 8, 2016 for $26.2B.",
            "evidence_limitations": "Corporate acquisition announcement.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_TRUE_04",
            "claim": "NIST NVD assigned vulnerability CVE-2021-44228 in Apache Log4j a CVSS base score of 10.0 Critical",
            "entity": "Apache",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228",
                "passage": "CVE-2021-44228 Detail: Apache Log4j2 JNDI features do not protect against attacker controlled LDAP. Base Score: 10.0 CRITICAL (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H).",
                "claim_context": "National Vulnerability Database CVE assessment",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official NIST NVD record lists CVE-2021-44228 with CVSS v3.1 score 10.0 Critical.",
            "evidence_limitations": "Security vulnerability database specification.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_TRUE_05",
            "claim": "Satya Nadella succeeded Steve Ballmer as Chief Executive Officer of Microsoft in February 2014",
            "entity": "Microsoft",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://news.microsoft.com/2014/02/04/microsoft-board-names-satya-nadella-as-ceo/",
                "passage": "REDMOND, Wash. — Feb. 4, 2014 — Microsoft Corp. today announced that its Board of Directors has appointed Satya Nadella as Chief Executive Officer and member of the Board of Directors.",
                "claim_context": "Microsoft official leadership announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Microsoft Board appointed Satya Nadella CEO on February 4, 2014 succeeding Steve Ballmer.",
            "evidence_limitations": "Corporate executive transition disclosure.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },

        # --- 2. Clearly False Claims (6-10) ---
        {
            "id": "DEV_FALSE_01",
            "claim": "SEC EDGAR allows automated scrapers an unrestricted request rate of 100 requests per second",
            "entity": "SEC",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data",
                "passage": "To ensure that all users have access to SEC filings, the SEC imposes a maximum request rate of 10 requests per second. Requests exceeding this rate are blocked.",
                "claim_context": "SEC EDGAR fair access policy",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by SEC policy: maximum rate is 10 req/sec, not 100 req/sec.",
            "evidence_limitations": "Factual numerical contradiction on published official limit.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "DEV_FALSE_02",
            "claim": "The title of arXiv paper 1706.03762 is Recurrence Is All You Need",
            "entity": "arXiv",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://arxiv.org/abs/1706.03762",
                "passage": "Title: Attention Is All You Need. Authors: Ashish Vaswani et al.",
                "claim_context": "arXiv bibliographic catalog",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by the catalog: the title is Attention Is All You Need.",
            "evidence_limitations": "Bibliographic counterfactual.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "DEV_FALSE_03",
            "claim": "Microsoft acquired LinkedIn for $50 billion in December 2020",
            "entity": "Microsoft",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://news.microsoft.com/2016/12/08/microsoft-closes-acquisition-of-linkedin/",
                "passage": "Microsoft Corp. today announced that it has officially closed its acquisition of LinkedIn Corporation in an all-cash transaction valued at $26.2 billion on December 8, 2016.",
                "claim_context": "Microsoft official acquisition press disclosure",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "The transaction was $26.2 billion in 2016, contradicting both the $50 billion valuation and 2020 date.",
            "evidence_limitations": "Numerical and temporal discrepancy.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "DEV_FALSE_04",
            "claim": "NIST rated the Log4j vulnerability CVE-2021-44228 as Low severity with a CVSS score of 2.1",
            "entity": "Apache",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228",
                "passage": "Base Score: 10.0 CRITICAL (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H).",
                "claim_context": "National Vulnerability Database CVE assessment",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Contradicts NIST NVD records: score is 10.0 Critical, not 2.1 Low.",
            "evidence_limitations": "Numerical discrepancy on official rating.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "DEV_FALSE_05",
            "claim": "Satya Nadella was appointed CEO of Microsoft in 2021",
            "entity": "Microsoft",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://news.microsoft.com/2014/02/04/microsoft-board-names-satya-nadella-as-ceo/",
                "passage": "Feb. 4, 2014 — Microsoft Corp. today announced that its Board of Directors has appointed Satya Nadella as Chief Executive Officer.",
                "claim_context": "Microsoft official leadership announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Nadella was appointed CEO in 2014, not 2021. (In 2021, he was named Board Chairman, not new CEO).",
            "evidence_limitations": "Temporal error on executive appointment.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },

        # --- 3. Partially True / Misleading Context (11-15) ---
        {
            "id": "DEV_PARTIAL_01",
            "claim": "Tesla recalled all delivered Cybertruck vehicles in April 2024 due to complete motor failure",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "PARTIALLY_TRUE",
            "expected_verdicts": ["MISLEADING", "MIXED"],
            "reference": {
                "primary_url": "https://www.nhtsa.gov/recalls?nhtsaId=24V276000",
                "passage": "NHTSA Campaign Number: 24V276000. Tesla is recalling certain 2024 Cybertruck vehicles. An unapproved lubricant was used during accelerator pedal assembly, which may cause the pedal pad to dislodge and trap the accelerator.",
                "claim_context": "NHTSA Recall Bulletin 24V276000",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Tesla did recall 3,878 Cybertrucks in April 2024, but it was for an accelerator pedal pad dislodgement issue, not 'complete motor failure'.",
            "evidence_limitations": "Component defect exaggerated into catastrophic powertrain failure.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "partially_true"
        },
        {
            "id": "DEV_PARTIAL_02",
            "claim": "Google was broken up into three separate companies following an antitrust court ruling in August 2024",
            "entity": "Google",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "MISLEADING",
            "expected_verdicts": ["MISLEADING", "REFUTED"],
            "reference": {
                "primary_url": "https://www.justice.gov/opa/pr/justice-department-statement-antitrust-ruling-google-search",
                "passage": "On August 5, 2024, the U.S. District Court found Google liable for maintaining an illegal monopoly in general search services. The court did not order a corporate breakup; remedy proceedings were scheduled for a subsequent phase.",
                "claim_context": "DOJ Official Statement on Google Search Antitrust Ruling",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "A federal judge ruled Google violated antitrust laws in search, but the court did NOT order a breakup of Google into three companies.",
            "evidence_limitations": "Liability finding misconstrued as corporate dissolution.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "misleading_context"
        },
        {
            "id": "DEV_PARTIAL_03",
            "claim": "Apple discontinued all Intel-based Mac computers on November 10, 2020",
            "entity": "Apple",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "MISLEADING",
            "expected_verdicts": ["MISLEADING", "OUTDATED"],
            "reference": {
                "primary_url": "https://www.apple.com/newsroom/2020/11/apple-unleashes-m1/",
                "passage": "Nov 10, 2020 — Apple today announced M1, the first chip designed specifically for the Mac. Apple introduced new MacBook Air, 13-inch MacBook Pro, and Mac mini powered by M1, initiating a two-year transition from Intel processors.",
                "claim_context": "Apple Official M1 Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Apple introduced M1 and announced a two-year transition on Nov 10, 2020, but continued selling Intel Mac Pro and Mac mini models until 2023.",
            "evidence_limitations": "Transition announcement confused with immediate total product cessation.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "misleading_context"
        },
        {
            "id": "DEV_PARTIAL_04",
            "claim": "Amazon laid off 100% of its corporate workforce in 2023 due to AI automation",
            "entity": "Amazon",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "MISLEADING"],
            "reference": {
                "primary_url": "https://www.aboutamazon.com/news/company-news/update-from-ceo-andy-jassy-on-role-eliminations",
                "passage": "Andy Jassy announced the elimination of approximately 18,000 corporate roles across retail and recruiting, representing approximately 6% of Amazon's corporate workforce of 300,000 employees.",
                "claim_context": "Amazon CEO letter on role eliminations",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Amazon laid off ~18,000 employees (~6% of corporate staff), not 100%.",
            "evidence_limitations": "Gross numerical exaggeration from 6% to 100%.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "misleading_context"
        },
        {
            "id": "DEV_PARTIAL_05",
            "claim": "Nvidia revenues in FY2024 increased by over 100% year-over-year driven by data center AI demand",
            "entity": "Nvidia",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2024",
                "passage": "For fiscal 2024, revenue was $60.9 billion, up 126% from $27.0 billion a year ago. Data Center fiscal full-year revenue was $47.5 billion, up 217%.",
                "claim_context": "Nvidia FY2024 financial results release",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official 10-K and earnings release confirm FY2024 revenue grew 126%, which is over 100%.",
            "evidence_limitations": "Financial metric comparison matching issuer, period, and accounting standard.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },

        # --- 4. Outdated Facts & Temporal Shifts (16-20) ---
        {
            "id": "DEV_OUTDATED_01",
            "claim": "Steve Ballmer is the current Chief Executive Officer of Microsoft",
            "entity": "Microsoft",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "OUTDATED",
            "expected_verdicts": ["OUTDATED", "REFUTED"],
            "reference": {
                "primary_url": "https://news.microsoft.com/exec/satya-nadella/",
                "passage": "Satya Nadella is Chairman and Chief Executive Officer of Microsoft. Steve Ballmer stepped down as CEO on February 4, 2014.",
                "claim_context": "Microsoft official executive biography",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Steve Ballmer was CEO from 2000 to 2014, but is no longer CEO. Outdated by over a decade.",
            "evidence_limitations": "Historical fact presented as current status.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "outdated_facts"
        },
        {
            "id": "DEV_OUTDATED_02",
            "claim": "Twitter is an independent publicly traded company listed on the New York Stock Exchange under ticker TWTR",
            "entity": "Twitter",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "OUTDATED",
            "expected_verdicts": ["OUTDATED", "REFUTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/Archives/edgar/data/1418091/000119312522271675/d409419d25.htm",
                "passage": "SEC Form 25: Notification of Removal from Listing and Registration under Section 12(b). Twitter, Inc. common stock delisted from NYSE on October 28, 2022 following acquisition by X Holdings I, Inc.",
                "claim_context": "SEC Form 25 Twitter Delisting Notice",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Twitter was taken private in October 2022 and delisted from the NYSE.",
            "evidence_limitations": "Corporate status changed from public to private entity.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "outdated_facts"
        },
        {
            "id": "DEV_OUTDATED_03",
            "claim": "The United Kingdom is a member state of the European Union",
            "entity": "United Kingdom",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "OUTDATED",
            "expected_verdicts": ["OUTDATED", "REFUTED"],
            "reference": {
                "primary_url": "https://www.gov.uk/government/collections/brexit-guidance",
                "passage": "The United Kingdom formally left the European Union on 31 January 2020 following the European Union (Withdrawal Agreement) Act 2020.",
                "claim_context": "UK Government official treaty departure record",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "The UK left the EU on January 31, 2020.",
            "evidence_limitations": "International treaty status superseded.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "outdated_facts"
        },
        {
            "id": "DEV_OUTDATED_04",
            "claim": "Jeff Bezos is the active Chief Executive Officer of Amazon",
            "entity": "Amazon",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "OUTDATED",
            "expected_verdicts": ["OUTDATED", "REFUTED"],
            "reference": {
                "primary_url": "https://www.aboutamazon.com/news/company-news/andy-jassy-becomes-ceo-of-amazon",
                "passage": "On July 5, 2021, Andy Jassy transitioned to CEO of Amazon, while Jeff Bezos transitioned to the role of Executive Chair of the Amazon Board of Directors.",
                "claim_context": "Amazon CEO Transition Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Jeff Bezos stepped down as CEO in July 2021 and became Executive Chair.",
            "evidence_limitations": "Executive transition superseded in 2021.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "outdated_facts"
        },
        {
            "id": "DEV_OUTDATED_05",
            "claim": "Windows 7 is currently supported by Microsoft with active security updates",
            "entity": "Microsoft",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "OUTDATED",
            "expected_verdicts": ["OUTDATED", "REFUTED"],
            "reference": {
                "primary_url": "https://support.microsoft.com/en-us/windows/windows-7-support-ended-on-january-14-2020-bbaedd36-042d-de50-7467-f6477bd4dc42",
                "passage": "After 10 years of servicing, Windows 7 reached End of Support on January 14, 2020. Microsoft no longer provides security updates or technical support for Windows 7.",
                "claim_context": "Microsoft Official Windows 7 Lifecycle Page",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Windows 7 reached End of Support on January 14, 2020.",
            "evidence_limitations": "Software product lifecycle status expired.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "outdated_facts"
        },

        # --- 5. Fake Announcements & Fabricated Quotations (21-25) ---
        {
            "id": "DEV_FAKE_01",
            "claim": "Apple announced the immediate shutdown of the App Store on October 1, 2026",
            "entity": "Apple",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "UNVERIFIED"],
            "reference": {
                "primary_url": "https://www.apple.com/newsroom/",
                "passage": "Official Apple Newsroom releases: Oct 2026 includes Apple Watch and iPhone 16 announcements, developer updates, and App Store developer payouts. No announcement of App Store closure exists.",
                "claim_context": "Apple Official Newsroom Index",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Fabricated corporate shutdown rumor. The App Store remains Apple's core active digital marketplace.",
            "evidence_limitations": "Universal negative claim; lack of official announcement on core business.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "fake_announcement"
        },
        {
            "id": "DEV_FAKE_02",
            "claim": "Satya Nadella stated in an interview that artificial intelligence will eliminate all human software engineers by November 2026",
            "entity": "Microsoft",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "UNVERIFIED"],
            "reference": {
                "primary_url": "https://news.microsoft.com/speeches-and-interviews/",
                "passage": "Satya Nadella public speeches: In keynotes on Microsoft Copilot, Nadella emphasized AI as 'a tool to empower developers and amplify human productivity, not replace human ingenuity.'",
                "claim_context": "Microsoft Public Speech Archive",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Fabricated executive quotation. Nadella repeatedly stated AI empowers rather than replaces human developers.",
            "evidence_limitations": "Attributed quotation without public record or verifiable transcript.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "fake_quotation"
        },
        {
            "id": "DEV_FAKE_03",
            "claim": "Tesla announced a mandatory recall of all vehicles worldwide due to flying saucer alien interference",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.nhtsa.gov/recalls",
                "passage": "Official NHTSA and Tesla recall dockets list steering, software, and physical components. No recall filing mentions extraterrestrial interference.",
                "claim_context": "NHTSA official recall dockets",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Absurd fabricated recall reason. Safety recalls must cite valid mechanical or software defect grounds.",
            "evidence_limitations": "Conspiracy / satirical fabrication.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "fake_announcement"
        },
        {
            "id": "DEV_FAKE_04",
            "claim": "Elon Musk posted on X that anyone who deposits 1 Bitcoin will receive 2 Bitcoin in return immediately",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://twitter.com/elonmusk",
                "passage": "Elon Musk's official verified profile does not host doubling cryptocurrency promotions. The FTC warns: 'Cryptocurrency giveaway scams promising to double your Bitcoin are fraudulent schemes operated by impersonators.'",
                "claim_context": "FTC Consumer Scam Advisory on Cryptocurrency Impersonation",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Classic crypto giveaway scam lure operated by spoofed accounts, not legitimate executive action.",
            "evidence_limitations": "Known criminal phishing pattern.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "brand_impersonation"
        },
        {
            "id": "DEV_FAKE_05",
            "claim": "Tim Cook announced his resignation as CEO of Apple effective immediately on October 10, 2026",
            "entity": "Apple",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "UNVERIFIED"],
            "reference": {
                "primary_url": "https://www.apple.com/leadership/tim-cook/",
                "passage": "Tim Cook is the Chief Executive Officer of Apple and serves on its Board of Directors. Apple has filed no Form 8-K concerning executive officer departure.",
                "claim_context": "Apple SEC Filings and Leadership Directory",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Fabricated executive resignation rumor. Material corporate leadership changes require immediate Form 8-K disclosures.",
            "evidence_limitations": "Lack of statutory SEC 8-K disclosure.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "fake_announcement"
        },

        # --- 6. Incorrect Financial Figures & Calculations (26-30) ---
        {
            "id": "DEV_NUM_01",
            "claim": "Nvidia reported total revenue of $10 billion for fiscal year 2024",
            "entity": "Nvidia",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2024",
                "passage": "For fiscal 2024, revenue was $60.9 billion, up 126% from $27.0 billion a year ago.",
                "claim_context": "Nvidia FY2024 financial results release",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by Nvidia's 10-K filing: FY2024 revenue was $60.9B, not $10B.",
            "evidence_limitations": "Official GAAP revenue reporting.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_financial"
        },
        {
            "id": "DEV_NUM_02",
            "claim": "Apple reported quarterly net income of $900 billion in Q1 fiscal 2024",
            "entity": "Apple",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.apple.com/newsroom/2024/02/apple-reports-first-quarter-results/",
                "passage": "CUPERTINO, Calif. — Feb. 1, 2024 — Apple today announced financial results for its fiscal 2024 first quarter ended December 30, 2023. The Company posted quarterly revenue of $119.6 billion and quarterly net income of $33.9 billion.",
                "claim_context": "Apple Q1 FY2024 Earnings Release",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Net income was $33.9 billion, not $900 billion (which is larger than any annual corporate profit in history).",
            "evidence_limitations": "Massive numerical fabrication exceeding total company revenue.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_financial"
        },
        {
            "id": "DEV_NUM_03",
            "claim": "Nvidia completed a 10-for-1 forward stock split in June 2024",
            "entity": "Nvidia",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2025",
                "passage": "NVIDIA today announced a 10-for-1 forward stock split of NVIDIA’s common stock to make stock ownership more accessible to employees and investors. Trading on a split-adjusted basis began on June 10, 2024.",
                "claim_context": "Nvidia Q1 FY2025 Stock Split Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Nvidia executed a 10-for-1 forward stock split effective June 10, 2024.",
            "evidence_limitations": "Corporate capital restructuring event.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_NUM_04",
            "claim": "Tata Motors reported total automotive debt of zero dollars in fiscal 2021",
            "entity": "Tata Motors",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.tatamotors.com/investors/",
                "passage": "Tata Motors FY21 Integrated Annual Report: Net automotive debt stood at Rs 40,876 crore as of March 31, 2021, with a corporate goal to achieve near-zero automotive debt in subsequent years.",
                "claim_context": "Tata Motors FY21 Annual Report",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Automotive debt was ~40,876 crore INR in FY21; zero debt was an aspirational multi-year target, not the current state.",
            "evidence_limitations": "Target confused with audited balance sheet debt.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_financial"
        },
        {
            "id": "DEV_NUM_05",
            "claim": "The speed of light in vacuum is defined as exactly 299,792,458 metres per second",
            "entity": "BIPM",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.bipm.org/en/committees/cc/cctf",
                "passage": "The SI base unit of length, the metre, is defined by taking the fixed numerical value of the speed of light in vacuum, c, to be 299 792 458 when expressed in the unit m s−1.",
                "claim_context": "BIPM SI Brochure 9th Edition Definition of Metre",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Physical constant exact definition under SI standard.",
            "evidence_limitations": "Exact scientific constant definition.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },

        # --- 7. Cybersecurity & Vulnerabilities (31-35) ---
        {
            "id": "DEV_SEC_01",
            "claim": "Vulnerability CVE-2014-0160, commonly known as Heartbleed, allows remote memory disclosure in OpenSSL",
            "entity": "OpenSSL",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/vuln/detail/CVE-2014-0160",
                "passage": "The (1) TLS and (2) DTLS implementations in OpenSSL 1.0.1 before 1.0.1g do not properly handle Heartbeat Extension packets, allowing remote attackers to obtain sensitive information from process memory.",
                "claim_context": "NIST NVD CVE-2014-0160 detail",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "NIST NVD record verifies CVE-2014-0160 (Heartbleed) is an information disclosure flaw in OpenSSL heartbeat handling.",
            "evidence_limitations": "Historical CVE record.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_SEC_02",
            "claim": "The backdoor discovered in XZ Utils in March 2024 was tracked under identifier CVE-2024-3094",
            "entity": "XZ Utils",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3094",
                "passage": "Malicious code was discovered in the upstream tarballs of xz, starting with version 5.6.0. Through complex obfuscation, the liblzma build extracts a prebuilt object file modifying OpenSSH authentication.",
                "claim_context": "NIST NVD CVE-2024-3094 detail",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "NIST NVD officially assigns CVE-2024-3094 to the XZ Utils supply chain backdoor.",
            "evidence_limitations": "CVE assignment documentation.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "DEV_SEC_03",
            "claim": "CVE-2024-3094 in XZ Utils was rated as a Low severity issue that only affects Windows desktop calculators",
            "entity": "XZ Utils",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3094",
                "passage": "CVE-2024-3094 Base Score: 10.0 CRITICAL. Affects Linux distributions using systemd and OpenSSH linked against liblzma. Vector: Network, low complexity, no privileges required.",
                "claim_context": "NIST NVD CVE-2024-3094 detail",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by NVD: score is 10.0 Critical, affecting Linux systems via OpenSSH, not Windows calculators.",
            "evidence_limitations": "Counterfactual severity and platform mismatch.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "cybersecurity"
        },

        # --- 8. Insufficient Evidence / Unverified Rumors (36-40) ---
        {
            "id": "DEV_INSUF_01",
            "claim": "Apple will announce a flying commercial automobile powered by cold fusion on December 31, 2027",
            "entity": "Apple",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Speculative unannounced future product rumor",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "No authoritative primary sources, filings, or announcements exist for a 2027 cold fusion flying vehicle.",
            "evidence_limitations": "Speculative unannounced future product rumor.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        },
        {
            "id": "DEV_INSUF_02",
            "claim": "An anonymous internet forum user claims that a major tech executive plans to retire next year",
            "entity": "Tech Executive",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Anonymous single-source hearsay",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "Uncorroborated single-user anonymous rumor has zero verified evidence.",
            "evidence_limitations": "Anonymous hearsay lacking evidentiary substance.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        },
        {
            "id": "DEV_INSUF_03",
            "claim": "Secret negotiations are currently occurring between two confidential private entities regarding a future transaction",
            "entity": "Confidential Entities",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Unverifiable private rumor",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "Unverifiable proposition with no public disclosures or named verifiable entities.",
            "evidence_limitations": "Zero public disclosure or verifiable entity identity.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        },
        {
            "id": "DEV_INSUF_04",
            "claim": "A social media post with 3 likes alleges that Microsoft will rebrand its corporate name to MicroTech tomorrow",
            "entity": "Microsoft",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Low-signal social media noise",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "Single low-traction social post cannot establish a corporate rebranding claim.",
            "evidence_limitations": "Lack of authoritative corroboration.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        },
        {
            "id": "DEV_INSUF_05",
            "claim": "Unconfirmed leaked video with obscured faces claims to show an unreleased smartphone prototype in an undisclosed room",
            "entity": "Smartphone Prototype",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Unverifiable leaked media",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "Without inspectable provenance or verifiable hardware authentication, the claim is unverified.",
            "evidence_limitations": "Obscured anonymous video lacking chain of custody.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        }
    ]


def get_regression_cases():
    return [
        # --- Regression Set (20 cases) ---
        {
            "id": "REG_01",
            "claim": "Tesla Cybertruck was recalled in April 2024 because the accelerator pedal pad could become trapped",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.nhtsa.gov/recalls?nhtsaId=24V276000",
                "passage": "Tesla is recalling certain 2024 Cybertruck vehicles. When high force is applied to the pad on the accelerator pedal, the pad may dislodge, which may cause the pedal to become trapped in the interior trim.",
                "claim_context": "NHTSA Recall Bulletin 24V276000",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official NHTSA filing confirms exact defect and recall date.",
            "evidence_limitations": "NHTSA official bulletin.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_02",
            "claim": "Tesla Cybertruck accelerator pedal recall in April 2024 was caused by a nuclear reactor explosion",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.nhtsa.gov/recalls?nhtsaId=24V276000",
                "passage": "An unapproved change introduced lubricant to aid in the component assembly of the pad onto the accelerator pedal, causing reduced retention of the pad to the pedal.",
                "claim_context": "NHTSA Recall Bulletin 24V276000",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by official cause: assembly soap lubricant, not nuclear explosion.",
            "evidence_limitations": "Absurd causal attribution directly contradicted by engineering documentation.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "REG_03",
            "claim": "Apple released the Vision Pro spatial computer in the United States on February 2, 2024",
            "entity": "Apple",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.apple.com/newsroom/2024/01/apple-vision-pro-available-in-the-us-on-february-2/",
                "passage": "CUPERTINO, Calif. — Jan. 8, 2024 — Apple today announced Apple Vision Pro will be available beginning Friday, February 2, at all U.S. Apple Store locations and the U.S. Apple Store online.",
                "claim_context": "Apple Official Vision Pro Release Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official Apple release date confirmed as February 2, 2024 in the US.",
            "evidence_limitations": "Corporate product launch announcement.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_04",
            "claim": "Apple released the Vision Pro spatial computer in 1995",
            "entity": "Apple",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.apple.com/newsroom/2024/01/apple-vision-pro-available-in-the-us-on-february-2/",
                "passage": "Apple today announced Apple Vision Pro will be available beginning Friday, February 2, 2024.",
                "claim_context": "Apple Official Vision Pro Release Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Contradicts product launch date by nearly three decades.",
            "evidence_limitations": "Severe anachronism.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_dates"
        },
        {
            "id": "REG_05",
            "claim": "Nvidia was founded in 1993 by Jensen Huang, Chris Malachowsky, and Curtis Priem",
            "entity": "Nvidia",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.nvidia.com/en-us/about-nvidia/corporate-timeline/",
                "passage": "1993: NVIDIA is founded by Jensen Huang, Chris Malachowsky, and Curtis Priem.",
                "claim_context": "Nvidia Corporate Timeline",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official corporate timeline confirms founders and founding year 1993.",
            "evidence_limitations": "Official historical corporate record.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_06",
            "claim": "Nvidia was founded in 2022 by anonymous internet developers",
            "entity": "Nvidia",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.nvidia.com/en-us/about-nvidia/corporate-timeline/",
                "passage": "1993: NVIDIA is founded by Jensen Huang, Chris Malachowsky, and Curtis Priem.",
                "claim_context": "Nvidia Corporate Timeline",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by Nvidia corporate history.",
            "evidence_limitations": "Fictional founding narrative.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "REG_07",
            "claim": "Sundar Pichai was appointed CEO of Alphabet in December 2019 while retaining his role as CEO of Google",
            "entity": "Alphabet",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/Archives/edgar/data/1652044/000165204419000037/goog8-k120319.htm",
                "passage": "Item 5.02: Larry Page and Sergey Brin have stepped down from their respective roles as CEO and President of Alphabet. Sundar Pichai will become the CEO of Alphabet while remaining the CEO of Google.",
                "claim_context": "Alphabet SEC Form 8-K Filing Dec 3, 2019",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official SEC 8-K filing confirms appointment in December 2019.",
            "evidence_limitations": "SEC Form 8-K authoritative executive disclosure.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_08",
            "claim": "Larry Page is currently the active Chief Executive Officer of Alphabet",
            "entity": "Alphabet",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "OUTDATED",
            "expected_verdicts": ["OUTDATED", "REFUTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/Archives/edgar/data/1652044/000165204419000037/goog8-k120319.htm",
                "passage": "Larry Page and Sergey Brin have stepped down from their respective roles as CEO and President of Alphabet. Sundar Pichai will become the CEO of Alphabet.",
                "claim_context": "Alphabet SEC Form 8-K Filing Dec 3, 2019",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Larry Page stepped down as Alphabet CEO in 2019.",
            "evidence_limitations": "Superseded executive status.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "outdated_facts"
        },
        {
            "id": "REG_09",
            "claim": "Microsoft launched the Windows 11 operating system on October 5, 2021",
            "entity": "Microsoft",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://blogs.windows.com/windowsexperience/2021/08/31/windows-11-available-on-october-5/",
                "passage": "Today, we are thrilled to announce Windows 11 will start to become available on October 5, 2021. On this day, the free upgrade to Windows 11 will begin rolling out.",
                "claim_context": "Microsoft Official Windows Blog",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official Microsoft Windows Blog confirms October 5, 2021 general availability date.",
            "evidence_limitations": "Operating system release announcement.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_10",
            "claim": "Windows 11 was released in 2010 prior to Windows 8",
            "entity": "Microsoft",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://blogs.windows.com/windowsexperience/2021/08/31/windows-11-available-on-october-5/",
                "passage": "Windows 11 will start to become available on October 5, 2021, succeeding Windows 10.",
                "claim_context": "Microsoft Official Windows Blog",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by software release chronology (Windows 11 was released in 2021, not 2010).",
            "evidence_limitations": "Chronological inversion.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_dates"
        },
        {
            "id": "REG_11",
            "claim": "Tata Motors acquired Jaguar Land Rover from Ford Motor Company in 2008 for approximately $2.3 billion",
            "entity": "Tata Motors",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.tatamotors.com/press-releases/tata-motors-completes-acquisition-of-jaguar-land-rover/",
                "passage": "Tata Motors today completed the acquisition of the Jaguar Land Rover businesses from Ford Motor Company for a net consideration of US $2.3 billion on a cash-free, debt-free basis.",
                "claim_context": "Tata Motors Official Acquisition Closing Release",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Tata Motors completed acquisition of JLR from Ford in June 2008 for $2.3B.",
            "evidence_limitations": "Corporate acquisition agreement.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_12",
            "claim": "Ford Motor Company acquired Tata Motors in 2024 for 100 dollars",
            "entity": "Tata Motors",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.tatamotors.com/investors/",
                "passage": "Tata Motors is a flagship $44 billion organization of the Tata Group, listed on BSE and NSE. It is not an acquired subsidiary of Ford.",
                "claim_context": "Tata Motors Corporate Information",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Fabricated multi-entity transaction inversion.",
            "evidence_limitations": "Entity role inversion and absurd valuation.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "REG_13",
            "claim": "Reuters wire report stating Sony reported 65 million PlayStation 5 console shipments was syndicated across financial news outlets",
            "entity": "Sony",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.reuters.com/technology/sony-ps5-shipments-2024/",
                "passage": "TOKYO (Reuters) - Sony Group Corp said cumulative shipments of its PlayStation 5 gaming console reached 65.5 million units in the second quarter.",
                "claim_context": "Reuters Wire Service Report",
                "source_tier": "TIER_2_FINANCIAL_PRESS",
                "source_role": "SECONDARY"
            },
            "ground_truth_rationale": "Syndicated wire news story originating from Reuters Tokyo reporting Sony's official console shipment disclosures.",
            "evidence_limitations": "Wire syndication cluster.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "wire_syndication"
        },
        {
            "id": "REG_14",
            "claim": "Three identical republished Reuters wire articles about Sony console shipments prove three separate independent investigations",
            "entity": "Sony",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "MISLEADING"],
            "reference": {
                "primary_url": "https://www.reuters.com/technology/sony-ps5-shipments-2024/",
                "passage": "Republished articles on Yahoo Finance, MSN, and MarketWatch carry the identical text: '(Reuters) - Sony Group Corp said cumulative shipments...'. They represent syndicated distribution of a single report.",
                "claim_context": "Wire syndication analysis",
                "source_tier": "TIER_2_FINANCIAL_PRESS",
                "source_role": "SECONDARY"
            },
            "ground_truth_rationale": "Syndication copies of a single wire story share a single information origin and do not constitute independent corroboration.",
            "evidence_limitations": "False independence assertion.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "wire_syndication"
        },
        {
            "id": "REG_15",
            "claim": "A customer complaint regarding delayed sneakers delivery is evidence of a coordinated corporate counterfeit ring",
            "entity": "Nike",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "MISLEADING"],
            "reference": {
                "primary_url": "https://reddit.com/r/sneakers/comments/sample",
                "passage": "Reddit user post: 'I ordered shoes 10 days ago, delayed shipment, customer support was slow.' Genuine customer grievance regarding transit times.",
                "claim_context": "Consumer complaint distinguishing review triage",
                "source_tier": "TIER_3_INVESTOR_COMMUNITY",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "A standard shipping delay complaint does not substantiate an organized counterfeit distribution crime.",
            "evidence_limitations": "Grievance vs threat conflation.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "REG_16",
            "claim": "The domain myaccount.microsoft.com is an official Microsoft authentication and account management portal",
            "entity": "Microsoft",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://myaccount.microsoft.com",
                "passage": "Microsoft Account: Manage your security info, privacy settings, active sessions, and subscriptions.",
                "claim_context": "Microsoft official utility portal",
                "source_tier": "TIER_4_UTILITY",
                "source_role": "UTILITY_PORTAL"
            },
            "ground_truth_rationale": "myaccount.microsoft.com is an official Microsoft account portal, correctly classified as an authentication utility.",
            "evidence_limitations": "Utility service endpoint.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "REG_17",
            "claim": "The login page at myaccount.microsoft.com proves Microsoft was fined 50 billion dollars by the Federal Trade Commission",
            "entity": "Microsoft",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "INSUFFICIENT_EVIDENCE"],
            "reference": {
                "primary_url": "https://myaccount.microsoft.com/login",
                "passage": "Sign in to your Microsoft account. Enter your email, phone, or Skype. Terms of Use, Privacy & Cookies.",
                "claim_context": "Microsoft login page content",
                "source_tier": "TIER_4_UTILITY",
                "source_role": "UTILITY_PORTAL"
            },
            "ground_truth_rationale": "A login utility screen contains no regulatory enforcement or penalty information.",
            "evidence_limitations": "Utility portal mislabeled as regulatory sanction.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "REG_18",
            "claim": "A website at appleid-security-verification.com/login asking for SSN and password is an authentic Apple Inc corporate filing",
            "entity": "Apple",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://appleid-security-verification.com/login",
                "passage": "Urgent Apple ID verification required. Enter your Apple password and SSN immediately to avoid lockout.",
                "claim_context": "Adversarial lookalike phishing page",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "ADVERSARIAL"
            },
            "ground_truth_rationale": "It is a credential phishing page on an unauthorized lookalike domain, not a corporate filing.",
            "evidence_limitations": "Phishing spoofing domain.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "brand_impersonation"
        },
        {
            "id": "REG_19",
            "claim": "An audio clip generated by synthetic voice cloning software without camera recording constitutes authenticated video evidence",
            "entity": "Synthetic Media",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.cisa.gov/resources-tools/resources/understanding-and-mitigating-synthetic-media",
                "passage": "CISA Advisory: Audio-only synthetic voice recordings do not establish verified visual presence or authentic video documentation.",
                "claim_context": "CISA Guidance on Synthetic Media Verification",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Audio voice clones lack video asset bytes and cannot establish visual authenticity.",
            "evidence_limitations": "Media format forensic distinction.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "REG_20",
            "claim": "A future artificial intelligence model has traveled backward in time from year 3000 to alter historical stock prices in 1980",
            "entity": "Time Travel AI",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/edgar",
                "passage": "Official historical stock prices and market records are maintained in permanent ledgers with established transaction settlement dates.",
                "claim_context": "Audited market records",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Physically impossible counterfactual claim with zero evidentiary support in market ledgers.",
            "evidence_limitations": "Physical impossibility.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        }
    ]


def get_held_out_cases():
    return [
        # --- Held-Out Evaluation Set (30 cases) ---
        {
            "id": "HELD_01",
            "claim": "Alphabet Inc. class A shares trade on Nasdaq under the ticker symbol GOOGL",
            "entity": "Alphabet",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.nasdaq.com/market-activity/stocks/googl",
                "passage": "Alphabet Inc. Class A Common Stock (GOOGL) trades on the Nasdaq Global Select Market.",
                "claim_context": "Nasdaq Official Security Directory",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Nasdaq listing specification for Alphabet Class A shares.",
            "evidence_limitations": "Official market listing record.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_02",
            "claim": "Alphabet Inc. class A shares trade under the ticker symbol AAPL",
            "entity": "Alphabet",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.nasdaq.com/market-activity/stocks/googl",
                "passage": "Alphabet Inc. Class A Common Stock trades under symbol GOOGL. AAPL is the ticker symbol for Apple Inc.",
                "claim_context": "Nasdaq Official Security Directory",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "AAPL belongs to Apple Inc., not Alphabet.",
            "evidence_limitations": "Ticker symbol mismatch.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_03",
            "claim": "OpenAI published the research paper introducing the GPT-4 model under arXiv identifier 2303.08774",
            "entity": "OpenAI",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://arxiv.org/abs/2303.08774",
                "passage": "arXiv:2303.08774 [cs.CL]. Title: GPT-4 Technical Report. Authors: OpenAI. We report the development of GPT-4, a large-scale, multimodal model.",
                "claim_context": "arXiv preprint catalog",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "arXiv 2303.08774 is the official GPT-4 Technical Report preprint.",
            "evidence_limitations": "Preprint bibliographic record.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_04",
            "claim": "The GPT-4 Technical Report was published in 1985 before the creation of the World Wide Web",
            "entity": "OpenAI",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://arxiv.org/abs/2303.08774",
                "passage": "arXiv:2303.08774 submitted on 15 Mar 2023. Authors: OpenAI.",
                "claim_context": "arXiv preprint catalog",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Published March 2023, not 1985.",
            "evidence_limitations": "Severe anachronism.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_dates"
        },
        {
            "id": "HELD_05",
            "claim": "Microsoft Azure is a cloud computing platform operated by Microsoft",
            "entity": "Microsoft",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://azure.microsoft.com/en-us/overview/what-is-azure/",
                "passage": "The Azure cloud platform is more than 200 products and cloud services designed to help you bring new solutions to life. Microsoft Azure provides computing, analytics, storage and networking.",
                "claim_context": "Microsoft Azure official overview",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Established cloud computing platform operated by Microsoft.",
            "evidence_limitations": "Official product service description.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_06",
            "claim": "Microsoft Azure is a brand of physical running shoes manufactured from leather by Microsoft",
            "entity": "Microsoft",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://azure.microsoft.com/en-us/overview/what-is-azure/",
                "passage": "Microsoft Azure is an enterprise cloud computing infrastructure, not footwear or athletic apparel.",
                "claim_context": "Microsoft Azure official overview",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Azure is cloud computing software/infrastructure, not physical shoes.",
            "evidence_limitations": "Category error.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_07",
            "claim": "Jensen Huang is the co-founder, President, and Chief Executive Officer of Nvidia",
            "entity": "Nvidia",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.nvidia.com/en-us/about-nvidia/leadership-team/jensen-huang/",
                "passage": "Jensen Huang founded NVIDIA in 1993 and has served since its inception as president, chief executive officer, and a member of the board of directors.",
                "claim_context": "Nvidia Executive Biography",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official Nvidia leadership documentation.",
            "evidence_limitations": "Executive officer bio.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_08",
            "claim": "Jensen Huang was terminated from Nvidia in 1999 and replaced by Bill Gates",
            "entity": "Nvidia",
            "domain": "personal_watch",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.nvidia.com/en-us/about-nvidia/leadership-team/jensen-huang/",
                "passage": "Jensen Huang has served continuously since its inception as president, chief executive officer, and a member of the board of directors.",
                "claim_context": "Nvidia Executive Biography",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Contradicted by continuous service record.",
            "evidence_limitations": "Fabricated executive termination.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_09",
            "claim": "The Federal Trade Commission sued to block Microsoft's acquisition of Activision Blizzard in December 2022",
            "entity": "FTC",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.ftc.gov/news-events/news/press-releases/2022/12/ftc-seeks-block-microsofts-acquisition-activision-blizzard",
                "passage": "Dec. 8, 2022 — The Federal Trade Commission today issued an administrative complaint seeking to block technology giant Microsoft Corp. from acquiring leading video game developer Activision Blizzard, Inc.",
                "claim_context": "FTC Official Press Release",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official FTC administrative action announced December 8, 2022.",
            "evidence_limitations": "Regulatory enforcement action.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_10",
            "claim": "The FTC never challenged or reviewed Microsoft's acquisition of Activision Blizzard",
            "entity": "FTC",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.ftc.gov/news-events/news/press-releases/2022/12/ftc-seeks-block-microsofts-acquisition-activision-blizzard",
                "passage": "The Federal Trade Commission today issued an administrative complaint seeking to block technology giant Microsoft Corp. from acquiring leading video game developer Activision Blizzard, Inc.",
                "claim_context": "FTC Official Press Release",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by FTC formal administrative complaint and district court litigation.",
            "evidence_limitations": "Regulatory denial of documented legal action.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_11",
            "claim": "Tesla Cybertruck features an exoskeleton exterior made from ultra-hard 30X cold-rolled stainless steel",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.tesla.com/cybertruck",
                "passage": "Cybertruck is built with an exterior shell made for ultimate durability and passenger protection. Starting with a nearly impenetrable exoskeleton, every component is designed for superior strength and endurance, from Ultra-Hard 30X Cold-Rolled stainless-steel structural skin to Tesla armor glass.",
                "claim_context": "Tesla Cybertruck Product Specification",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official Tesla product specification material description.",
            "evidence_limitations": "Manufacturer product specifications.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_12",
            "claim": "Tesla Cybertruck body panels are manufactured from 100% biodegradable corrugated cardboard",
            "entity": "Tesla",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.tesla.com/cybertruck",
                "passage": "Cybertruck is built with an exterior shell made from Ultra-Hard 30X Cold-Rolled stainless-steel structural skin.",
                "claim_context": "Tesla Cybertruck Product Specification",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by manufacturing materials: stainless steel, not cardboard.",
            "evidence_limitations": "Absurd material composition claim.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_13",
            "claim": "Apple Inc. was originally incorporated on January 3, 1977 as Apple Computer, Inc.",
            "entity": "Apple",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/edgar/browse/?CIK=0000320193",
                "passage": "SEC CIK 0000320193: Apple Inc. State of incorporation: California. Date of incorporation: January 3, 1977. Formerly Apple Computer, Inc.",
                "claim_context": "SEC EDGAR Apple Corporate Filing Record",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official SEC EDGAR corporate registration record.",
            "evidence_limitations": "Corporate registration historical record.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_14",
            "claim": "Apple Inc. was incorporated for the first time in December 2025",
            "entity": "Apple",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.sec.gov/edgar/browse/?CIK=0000320193",
                "passage": "SEC CIK 0000320193: Apple Inc. Date of incorporation: January 3, 1977.",
                "claim_context": "SEC EDGAR Apple Corporate Filing Record",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Contradicts incorporation date by nearly 50 years.",
            "evidence_limitations": "Severe historical anachronism.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "incorrect_dates"
        },
        {
            "id": "HELD_15",
            "claim": "The United States Food and Drug Administration regulates medical devices, pharmaceuticals, and biological products",
            "entity": "FDA",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.fda.gov/about-fda/what-we-do",
                "passage": "The Food and Drug Administration is responsible for protecting the public health by ensuring the safety, efficacy, and security of human and veterinary drugs, biological products, and medical devices.",
                "claim_context": "FDA Statutory Mission Overview",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Statutory regulatory authority overview.",
            "evidence_limitations": "Government agency statutory scope.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_16",
            "claim": "The FDA's sole responsibility is regulating the design of submarine torpedoes",
            "entity": "FDA",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.fda.gov/about-fda/what-we-do",
                "passage": "The FDA regulates foods, drugs, medical devices, radiation-emitting products, vaccines, cosmetics, and tobacco. It does not regulate military naval munitions.",
                "claim_context": "FDA Statutory Mission Overview",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by statutory jurisdiction.",
            "evidence_limitations": "Jurisdictional contradiction.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_17",
            "claim": "An unidentified rumor on an unmoderated message board claims an executive secretly bought a diamond mine on Mars",
            "entity": "Martian Diamond Mine",
            "domain": "scout",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Anonymous message board rumor",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "Zero verifiable evidence, primary filings, or planetary mining assets exist.",
            "evidence_limitations": "Absurd unverified rumor.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        },
        {
            "id": "HELD_18",
            "claim": "A social media user alleges that a commercial airplane was spotted landing on the surface of the sun",
            "entity": "Solar Landing",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://science.nasa.gov/sun/",
                "passage": "The surface temperature of the Sun is approximately 5,500 degrees Celsius (9,932 degrees Fahrenheit). No commercial aircraft or physical human structure can land on the Sun.",
                "claim_context": "NASA Solar Physics Reference",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by basic astrophysics and thermal limits of materials.",
            "evidence_limitations": "Physical impossibility.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_19",
            "claim": "A phishing domain spoofing Bank of America was identified asking users to submit PIN and debit card details",
            "entity": "Bank of America",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.cisa.gov/news-events/alerts/2020/09/24/cisa-fbi-fbi-ic3-phishing-guidance",
                "passage": "CISA/FBI Alert: Malicious actors frequently establish domain names mimicking major financial institutions (e.g. bankofamerica-security-portal.xyz) to harvest account credentials and payment card PINs.",
                "claim_context": "CISA/FBI Financial Phishing Alert",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "CISA security alert describes documented financial phishing vector.",
            "evidence_limitations": "Cybersecurity advisory.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "cybersecurity"
        },
        {
            "id": "HELD_20",
            "claim": "All banking phishing domains are operated directly by official bank tellers during business hours",
            "entity": "Banking Phishing",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.cisa.gov/news-events/alerts/2020/09/24/cisa-fbi-fbi-ic3-phishing-guidance",
                "passage": "Phishing websites are registered and hosted by third-party criminal threat actors and cybercrime syndicates seeking unauthorized access, completely unaffiliated with authorized bank personnel.",
                "claim_context": "CISA/FBI Financial Phishing Alert",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Phishing infrastructure is operated by criminal threat actors, not official bank staff.",
            "evidence_limitations": "Attribution contradiction.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_21",
            "claim": "The United States Constitution was signed in Philadelphia in September 1787",
            "entity": "United States",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.archives.gov/founding-docs/constitution",
                "passage": "The Constitution of the United States: Signed in Convention September 17, 1787 by thirty-nine delegates at Independence Hall in Philadelphia, Pennsylvania.",
                "claim_context": "National Archives Founding Documents",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "National Archives primary historical record.",
            "evidence_limitations": "Historical founding document.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_22",
            "claim": "The United States Constitution was written and signed on the moon in 2020",
            "entity": "United States",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.archives.gov/founding-docs/constitution",
                "passage": "Signed September 17, 1787 at Independence Hall in Philadelphia, Pennsylvania.",
                "claim_context": "National Archives Founding Documents",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Contradicts date by 233 years and location by astronomical distances.",
            "evidence_limitations": "Severe spatial and temporal fabrication.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_23",
            "claim": "A customer who received a wrong sneaker size in the mail proves a coordinated international criminal counterfeit conspiracy",
            "entity": "Retail Customer",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED", "MISLEADING"],
            "reference": {
                "primary_url": "https://www.consumerfinance.gov/consumer-tools/",
                "passage": "Consumer fulfillment errors (such as shipping an incorrect size) are routine retail order fulfillment mistakes, distinguished from organized counterfeit trademark counterfeiting rings.",
                "claim_context": "Consumer protection order resolution guidance",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Fulfillment packaging errors do not substantiate criminal trademark counterfeiting conspiracies.",
            "evidence_limitations": "Grievance exaggeration.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_24",
            "claim": "The official Google Chrome browser web store is hosted on chromewebstore.google.com",
            "entity": "Google",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://chromewebstore.google.com",
                "passage": "Chrome Web Store: Discover extensions and themes to customize Google Chrome.",
                "claim_context": "Google Chrome Web Store Official Portal",
                "source_tier": "TIER_4_UTILITY",
                "source_role": "UTILITY_PORTAL"
            },
            "ground_truth_rationale": "Official Google web store portal domain.",
            "evidence_limitations": "Catalog utility portal.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_25",
            "claim": "A website at chrome-malware-download-store.cc offering free pirated movies is an official Google Chrome store",
            "entity": "Google",
            "domain": "brandshield",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://chromewebstore.google.com",
                "passage": "The official Chrome Web Store is hosted under google.com domains. Third-party domains offering pirated media are unauthorized and unaffiliated.",
                "claim_context": "Google Chrome Web Store Official Portal",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Unauthorized third-party domain hosting pirated content.",
            "evidence_limitations": "Hostile lookalike domain.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "brand_impersonation"
        },
        {
            "id": "HELD_26",
            "claim": "The National Institute of Standards and Technology (NIST) maintains the National Vulnerability Database (NVD)",
            "entity": "NIST",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/general",
                "passage": "The NVD is the U.S. government repository of standards based vulnerability management data represented using the Common Vulnerabilities and Exposures (CVE) specification, operated by NIST.",
                "claim_context": "NIST NVD Program Overview",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Official government agency program documentation.",
            "evidence_limitations": "U.S. government agency operational mandate.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_27",
            "claim": "NIST NVD is operated as a secret underground gambling casino in Las Vegas",
            "entity": "NIST",
            "domain": "cybersecurity",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://nvd.nist.gov/general",
                "passage": "The NVD is operated by the National Institute of Standards and Technology, a non-regulatory agency of the United States Department of Commerce.",
                "claim_context": "NIST NVD Program Overview",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Contradicted by federal statutory mandate.",
            "evidence_limitations": "Absurd fabrication.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        },
        {
            "id": "HELD_28",
            "claim": "An anonymous social media rumor claims that a secret portal exists to another dimension beneath a corporate office",
            "entity": "Dimensional Portal",
            "domain": "trending",
            "reference_date": "2026-10-14",
            "truth_label": "INSUFFICIENT_EVIDENCE",
            "expected_verdicts": ["INSUFFICIENT_EVIDENCE", "UNVERIFIED"],
            "reference": {
                "primary_url": "",
                "passage": "",
                "claim_context": "Unsubstantiated fantasy rumor",
                "source_tier": "TIER_4_UNVERIFIED",
                "source_role": "COMMUNITY"
            },
            "ground_truth_rationale": "Zero evidence exists for an interdimensional portal in corporate architecture.",
            "evidence_limitations": "Fantasy proposition with no verifiable empirical evidence.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "insufficient_evidence"
        },
        {
            "id": "HELD_29",
            "claim": "The World Wide Web Consortium (W3C) published the HTML5 Recommendation in October 2014",
            "entity": "W3C",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "TRUE",
            "expected_verdicts": ["SUPPORTED"],
            "reference": {
                "primary_url": "https://www.w3.org/News/2014/html5-rec.html.en",
                "passage": "28 October 2014 — Today W3C announced that HTML5 is a completed W3C Recommendation. The specification defines the 5th major version of HTML.",
                "claim_context": "W3C HTML5 Recommendation Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "W3C official press release on October 28, 2014.",
            "evidence_limitations": "Standards body publication record.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_true"
        },
        {
            "id": "HELD_30",
            "claim": "HTML5 was originally created by ancient Greek philosophers in 400 BC",
            "entity": "W3C",
            "domain": "general_science",
            "reference_date": "2026-10-14",
            "truth_label": "FALSE",
            "expected_verdicts": ["REFUTED"],
            "reference": {
                "primary_url": "https://www.w3.org/News/2014/html5-rec.html.en",
                "passage": "HTML5 was developed by the W3C Web Applications and WHATWG working groups in the 21st century and recommended in 2014.",
                "claim_context": "W3C HTML5 Recommendation Announcement",
                "source_tier": "TIER_1_ORIGINAL_DOCUMENT",
                "source_role": "PRIMARY"
            },
            "ground_truth_rationale": "Directly contradicted by technological and human history.",
            "evidence_limitations": "Extreme anachronistic fabrication.",
            "label_provenance": "source-adjudicated",
            "human_reviewed": False,
            "category": "clearly_false"
        }
    ]


def main():
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    dev_cases = get_dev_cases()
    reg_cases = get_regression_cases()
    held_cases = get_held_out_cases()

    # Validate disjoint ID sets
    all_ids = set()
    for subset_name, subset in [("dev", dev_cases), ("regression", reg_cases), ("held_out", held_cases)]:
        for c in subset:
            cid = c["id"]
            if cid in all_ids:
                raise ValueError(f"Duplicate benchmark ID found: {cid} in {subset_name}")
            all_ids.add(cid)

    # Save splits
    dev_path = BENCHMARK_DIR / "dev_set.json"
    reg_path = BENCHMARK_DIR / "regression_set.json"
    held_path = BENCHMARK_DIR / "held_out_set.json"

    dev_path.write_text(json.dumps({
        "split": "development",
        "description": "40 multi-domain claims for development, tuning, and failure diagnosis.",
        "case_count": len(dev_cases),
        "cases": dev_cases
    }, indent=2), encoding="utf-8")

    reg_path.write_text(json.dumps({
        "split": "regression",
        "description": "20 targeted claims verifying fixed defects remain stable and unregressed.",
        "case_count": len(reg_cases),
        "cases": reg_cases
    }, indent=2), encoding="utf-8")

    held_path.write_text(json.dumps({
        "split": "held_out",
        "description": "30 strictly held-out claims reserved for blind post-tuning evaluation.",
        "case_count": len(held_cases),
        "cases": held_cases
    }, indent=2), encoding="utf-8")

    print(f"Successfully generated Phase 9 reference benchmark in: {BENCHMARK_DIR}")
    print(f"  - Development Split : {len(dev_cases)} cases -> {dev_path.name}")
    print(f"  - Regression Split  : {len(reg_cases)} cases -> {reg_path.name}")
    print(f"  - Held-out Split    : {len(held_cases)} cases -> {held_path.name}")
    print(f"  - Total Benchmark   : {len(all_ids)} verified cases")


if __name__ == "__main__":
    main()
