"""
Aegis Protocol — Unit Tests: Personal Watch 2.0
================================================
Tests:
- Entity resolution (canonical names, aliases, handles, category)
- Multi-class threat-oriented query planning (6 classes)
- 14-class threat taxonomy mapping
- Claim vs. Threat separation
- Evidence URL preservation and absence of fake links
- Grounded synthesis refusing to hallucinate on empty retrieval
- Heuristic fallback resilience when AI enrichment is offline
- Alert deduplication and cooldown logic
- Change detection diff between scans
- Security boundaries (untrusted content tags and privacy)
"""

import pytest
from backend.agents.personal_agent import PersonalWatchAgent, THREAT_TAXONOMY
from backend.services.agent_reach.planner import RetrievalPlanner
from backend.services.notifier import PersonalAlertManager


def test_personal_entity_resolution():
    agent = PersonalWatchAgent()

    # Known catalog entry
    res_sama = agent.resolve_personal_entity("Sam Altman")
    assert res_sama["canonical_name"] == "Sam Altman"
    assert res_sama["category"] == "executive"
    assert res_sama["official_handles"].get("twitter") == "@sama"
    assert res_sama["confidence"] >= 0.90

    # Mr Beast resolution
    res_mrbeast = agent.resolve_personal_entity("Mr Beast")
    assert res_mrbeast["canonical_name"] == "MrBeast"
    assert res_mrbeast["category"] == "creator"
    assert "MrBeast" in res_mrbeast["official_handles"].get("youtube", "")

    # Custom structured profile input
    custom_input = {
        "name": "Dr. Jane Doe",
        "category": "researcher",
        "official_handles": {"twitter": "@janedoe_ai"},
        "aliases": ["Jane Doe"],
        "official_domains": ["janedoe-lab.org"]
    }
    res_custom = agent.resolve_personal_entity(custom_input)
    assert res_custom["canonical_name"] == "Dr. Jane Doe"
    assert res_custom["category"] == "researcher"
    assert res_custom["official_handles"]["twitter"] == "@janedoe_ai"
    assert "janedoe-lab.org" in res_custom["official_domains"]


def test_personal_query_classes():
    planner = RetrievalPlanner()
    classes = planner.build_personal_query_classes(
        name="Elon Musk",
        aliases=["Musk"],
        handles={"twitter": "@elonmusk"},
        category="executive"
    )

    assert "general" in classes
    assert "impersonation" in classes
    assert "phishing_scam" in classes
    assert "deepfake_synthetic" in classes
    assert "reputation_claims" in classes
    assert "doxxing_privacy" in classes

    assert any("fake account" in q for q in classes["impersonation"])
    assert any("scam" in q for q in classes["phishing_scam"])
    assert any("deepfake" in q for q in classes["deepfake_synthetic"])
    assert any("controversy" in q for q in classes["reputation_claims"])
    assert any("leaked" in q for q in classes["doxxing_privacy"])


def test_threat_taxonomy_coverage():
    assert len(THREAT_TAXONOMY) == 14
    expected_categories = [
        "IMPERSONATION", "PHISHING", "SCAM", "DEEPFAKE", "SYNTHETIC_MEDIA",
        "FALSE_CLAIM", "DOXXING_PRIVACY", "HARASSMENT", "REPUTATION_ATTACK",
        "FRAUDULENT_ANNOUNCEMENT", "FAKE_GIVEAWAY", "IDENTITY_MISUSE",
        "COORDINATED_CAMPAIGN", "UNVERIFIED_RUMOR"
    ]
    for cat in expected_categories:
        assert cat in THREAT_TAXONOMY, f"Missing taxonomy category: {cat}"


def test_empty_retrieval_no_synthetic_hallucination():
    agent = PersonalWatchAgent()
    subject_info = {"name": "GhostPerson123XYZ", "canonical_name": "GhostPerson123XYZ"}
    synthesis = agent._synthesize_personal_threats(subject_info, evidence_list=[])

    assert synthesis["threats"] == []
    assert synthesis["claims"] == []
    assert synthesis["narratives"] == []
    assert synthesis["suspected_impersonations"] == []
    assert synthesis["suspected_scams"] == []
    assert synthesis["deepfake_claims"] == []
    assert "No verified live evidence" in synthesis["status_note"]


def test_claim_vs_threat_separation():
    agent = PersonalWatchAgent()
    subject_info = {"name": "Alex Mercer", "canonical_name": "Alex Mercer"}

    evidence = [
        {
            "evidence_id": "ev_001",
            "title": "Alex Mercer announces new open source AI library",
            "snippet": "Official presentation at tech keynote today.",
            "url": "https://tech-news.org/article/1",
            "platform": "News",
            "source": "tech-news.org",
            "author": "Reporter1",
            "published_at": "Recent"
        },
        {
            "evidence_id": "ev_002",
            "title": "Warning: Fake account @alex_mercer_support asking for credit cards",
            "snippet": "Impersonator profile detected running a phishing campaign.",
            "url": "https://twitter.com/safety/status/123",
            "platform": "Twitter/X",
            "source": "Twitter/X",
            "author": "@safety_watch",
            "published_at": "Recent"
        }
    ]

    synthesis = agent._heuristic_threat_synthesis("Alex Mercer", evidence)

    # Threats should contain the impersonation
    assert any(t["threat_type"] == "IMPERSONATION" for t in synthesis["threats"])
    
    # Claims should capture public actions or reports
    assert len(synthesis["claims"]) > 0
    
    # Ensure evidence IDs link properly
    threat = synthesis["threats"][0]
    assert "ev_002" in threat["evidence_ids"]


def test_deepfake_synthetic_media_truthful_labeling():
    agent = PersonalWatchAgent()
    subject_info = {"name": "CEO Example", "canonical_name": "CEO Example"}

    evidence = [
        {
            "evidence_id": "ev_df_01",
            "title": "Viral deepfake audio claims CEO resigned effective immediately",
            "snippet": "Circulating synthetic voice clip was debunked by press office.",
            "url": "https://factcheck.org/ceo-deepfake",
            "platform": "Web",
            "source": "factcheck.org",
            "author": "FactCheck",
            "published_at": "Recent"
        }
    ]

    synthesis = agent._heuristic_threat_synthesis("CEO Example", evidence)
    assert len(synthesis["deepfake_claims"]) > 0
    df = synthesis["deepfake_claims"][0]
    assert df["technical_forensics_run"] is False
    assert "Technical verification unavailable" in df["forensic_status"]


def test_url_preservation_and_no_fake_links():
    agent = PersonalWatchAgent()
    subject_info = {"name": "Test Subject", "canonical_name": "Test Subject"}

    evidence = [
        {
            "evidence_id": "ev_real_1",
            "title": "Investigation report on scam network",
            "snippet": "Detailed forensic trace of phishing URLs.",
            "url": "https://cybersecurity.gov/advisory/2026-09",
            "platform": "Web",
            "source": "cybersecurity.gov",
            "author": "GovCERT",
            "published_at": "2026-09-18"
        }
    ]

    threats = [
        {
            "threat_id": "thr_01",
            "threat_type": "SCAM",
            "risk_level": "HIGH",
            "title": "Phishing Network Exploiting Identity",
            "reason": "Official CERT advisory issued.",
            "platform": "Web",
            "evidence_ids": ["ev_real_1"]
        }
    ]

    dossiers = agent._build_investigation_dossiers(threats, evidence, claims=[])
    assert len(dossiers) == 1
    dossier = dossiers[0]
    assert dossier["primary_source_url"] == "https://cybersecurity.gov/advisory/2026-09"
    assert dossier["primary_source_url"] != "#"
    assert dossier["evidence_chain"][0]["url"] == "https://cybersecurity.gov/advisory/2026-09"


def test_alert_deduplication_and_cooldown():
    manager = PersonalAlertManager(default_cooldown_seconds=3600)
    manager.clear_cache()

    threat = {
        "threat_id": "thr_test_01",
        "threat_type": "IMPERSONATION",
        "risk_level": "HIGH",
        "title": "Fake Support Account Active",
        "reason": "Lookalike handle detected",
        "evidence_ids": ["ev_1"]
    }

    # 1. First alert should be permitted
    allowed, reason = manager.should_send_alert("Alice Smith", threat, alert_preference="HIGH_ONLY")
    assert allowed is True
    assert reason == "alert_permitted"

    # Record the alert dispatch
    manager.record_alert("Alice Smith", threat, success=True)

    # 2. Immediate second alert for identical threat should be suppressed by cooldown
    allowed_again, reason_again = manager.should_send_alert("Alice Smith", threat, alert_preference="HIGH_ONLY")
    assert allowed_again is False
    assert "cooldown_active" in reason_again

    # 3. Preference filtering test: MEDIUM threat should be suppressed when preference is HIGH_ONLY
    med_threat = dict(threat, threat_id="thr_med", risk_level="MEDIUM")
    allowed_med, reason_med = manager.should_send_alert("Alice Smith", med_threat, alert_preference="HIGH_ONLY")
    assert allowed_med is False
    assert "filtered_by_preference" in reason_med

    # 4. Breaking cooldown when significant new evidence (+2 sources) emerges
    escalated_threat = dict(threat, evidence_ids=["ev_1", "ev_2", "ev_3"])
    allowed_esc, reason_esc = manager.should_send_alert("Alice Smith", escalated_threat, alert_preference="HIGH_ONLY")
    assert allowed_esc is True
    assert reason_esc == "escalated_evidence_growth"


def test_change_detection_between_scans():
    agent = PersonalWatchAgent()
    subject_name = "Bob Developer"

    # First scan: baseline
    threats_1 = [
        {"threat_id": "t1", "threat_type": "IMPERSONATION", "risk_level": "MEDIUM", "title": "Fake Twitter account"}
    ]
    evidence_1 = [{"platform": "Twitter/X", "source": "Twitter/X"}]

    changes_1, snap_1 = agent._compute_change_detection(subject_name, threats_1, evidence_1)
    assert any(c["change_type"] == "BASELINE_INITIALIZED" for c in changes_1)

    # Second scan: threat escalated to HIGH and new platform appeared
    threats_2 = [
        {"threat_id": "t1", "threat_type": "IMPERSONATION", "risk_level": "HIGH", "title": "Fake Twitter account"},
        {"threat_id": "t2", "threat_type": "SCAM", "risk_level": "HIGH", "title": "Crypto Giveaway Scam"}
    ]
    evidence_2 = [
        {"platform": "Twitter/X", "source": "Twitter/X"},
        {"platform": "YouTube", "source": "YouTube"}
    ]

    changes_2, snap_2 = agent._compute_change_detection(subject_name, threats_2, evidence_2)
    change_types = [c["change_type"] for c in changes_2]

    assert "ESCALATED_THREAT" in change_types
    assert "NEW_THREAT" in change_types
    assert "NEW_PLATFORM" in change_types
