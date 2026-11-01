"""Unit tests for Claim Intelligence Core.

Tests Deliverable 1 (Allegation vs. Evidence Matrix) and Deliverable 2
(Corroboration Illusion Detector / Source Independence Graph), verifying all
epistemic qualification contracts, non-negotiable invariants, and W3C PROV-O alignment.
"""
import pytest

from backend.services.claim_intelligence import (
    AllegationAssessmentEngine,
    AllegationMatrixItem,
    AtomicClaim,
    ClaimExtractor,
    CorroborationDetector,
    CorroborationGroup,
    CorroborationSummary,
    DeceptiveFramingType,
    EpistemicOutcome,
    EvidenceLink,
    MisinformationDossier,
    SourceRelationship,
    SourceRelationType,
    StanceAnalyzer,
    StanceType,
    assessment_engine,
    claim_extractor,
    corroboration_detector,
    stance_analyzer,
)


class TestAtomicClaimExtraction:
    """Verifies atomic claim decomposition, scope extraction, and qualifier preservation."""

    def test_extract_simple_claim_with_temporal_and_scope(self):
        query = "Company X recalled all products today due to contamination"
        claims = claim_extractor.extract_claims(query, entity="Company X")

        assert len(claims) == 1
        claim = claims[0]
        assert claim.target_entity == "Company X"
        assert claim.predicate == "recalled"
        assert claim.temporal_scope == "today"
        assert claim.subject_scope == "global_or_universal"
        assert not claim.is_negated
        assert claim.claim_id.startswith("clm_")

    def test_extract_preserves_qualifiers_and_uncertainty(self):
        query = "Pfizer allegedly settled a secret lawsuit regarding toxic batches"
        claims = claim_extractor.extract_claims(query, entity="Pfizer")

        assert len(claims) == 1
        claim = claims[0]
        assert "allegedly" in claim.extracted_qualifiers
        assert claim.predicate == "legal_or_regulatory_action"
        assert claim.subject_scope == "specific_batch"

    def test_extract_compound_claims(self):
        query = "Apple recalled defective batteries and also CFO resigned amid probe"
        claims = claim_extractor.extract_claims(query, entity="Apple")

        assert len(claims) == 2
        assert any(c.predicate == "recalled" for c in claims)
        assert any(c.predicate == "resigned_or_terminated" for c in claims)


class TestPassageStanceAndCorporateDenial:
    """Verifies passage stance scoring, byte hashing, and corporate denial isolation."""

    def test_corporate_denial_is_evidence_of_denial_not_falsity(self):
        claim = AtomicClaim.create(
            raw_allegation="Company X recalled products today",
            target_entity="Company X",
            predicate="recalled",
            temporal_scope="today",
        )
        passage = (
            "A spokesperson for Company X stated that no recall has occurred, "
            "calling circulating social media reports completely unfounded rumors."
        )

        link = stance_analyzer.evaluate_passage(
            claim=claim,
            passage_text=passage,
            source_id="src_pr_01",
            source_url="https://companyx.com/news/statement",
            publisher="Company X PR",
            full_source_text=f"PRESS RELEASE: {passage} Additional text follows.",
        )

        # Invariant check: stance is CONTRADICTS with is_corporate_denial=True
        assert link.stance == StanceType.CONTRADICTS
        assert link.is_corporate_denial is True
        assert "corporate denial" in link.rationale.lower()
        # Byte offset and hash validation
        assert link.passage_offsets[0] > 0
        assert len(link.content_hash) == 64

    def test_historical_event_temporal_mismatch(self):
        claim = AtomicClaim.create(
            raw_allegation="Company X recalled products today",
            target_entity="Company X",
            predicate="recalled",
            temporal_scope="today",
        )
        # Passage describes a real historical recall from 2021
        passage = "In March 2021, Company X recalled 4,000 units of lotion due to trace bacterial contamination."

        link = stance_analyzer.evaluate_passage(
            claim=claim,
            passage_text=passage,
            source_id="src_fda_2021",
            source_url="https://fda.gov/recalls/2021/companyx",
            publisher="FDA Enforcement Report",
        )

        assert link.temporal_match is False
        assert link.stance == StanceType.MENTIONS
        assert "potential misleading context" in link.rationale.lower()

    def test_affirmative_primary_support(self):
        claim = AtomicClaim.create(
            raw_allegation="Company X recalled products",
            target_entity="Company X",
            predicate="recalled",
        )
        passage = "Company X announced a formal recall of its flagship product following safety inspections."

        link = stance_analyzer.evaluate_passage(
            claim=claim,
            passage_text=passage,
            source_id="src_reuters_01",
            source_url="https://reuters.com/business/companyx-recall",
            publisher="Reuters",
        )

        assert link.stance == StanceType.SUPPORTS
        assert link.confidence >= 0.85
        assert link.is_corporate_denial is False


class TestCorroborationIllusionDetector:
    """Verifies Source Independence Graph and detection of syndicated echo-chambers."""

    def test_detects_corroboration_illusion_when_multiple_publishers_reprint_single_origin(self):
        # 4 publishers sharing identical or syndicated text from BlogOrigin
        base_text = (
            "According to unconfirmed sources, Company X has secretly halted production "
            "across all manufacturing plants following serious safety violations and regulatory scrutiny."
        )

        sources = [
            {
                "source_id": "src_1",
                "url": "https://blogorigin.com/leak",
                "publisher": "BlogOrigin",
                "body": base_text,
            },
            {
                "source_id": "src_2",
                "url": "https://aggregator1.com/story",
                "publisher": "Aggregator One",
                "body": f"Breaking update: {base_text} - originally reported by BlogOrigin.",
            },
            {
                "source_id": "src_3",
                "url": "https://newsrepost.org/article",
                "publisher": "News Repost",
                "body": base_text,
            },
            {
                "source_id": "src_4",
                "url": "https://viralfeeds.net/post",
                "publisher": "Viral Feeds",
                "body": f"Reports indicate that {base_text}",
            },
        ]

        summary, relationships = corroboration_detector.analyze_sources(sources)

        assert summary.total_sources_scanned == 4
        assert summary.unique_publishers == 4
        assert summary.independent_evidence_chains == 1
        assert summary.corroboration_illusion_detected is True
        assert summary.corroboration_ratio <= 0.40
        assert "CORROBORATION ILLUSION DETECTED" in summary.warning_message

        # Check provenance edges
        assert len(relationships) >= 1
        assert any(
            r.relation_type in {SourceRelationType.EXPLICIT_REPRINT, SourceRelationType.QUOTES, SourceRelationType.HIGH_TEXT_SIMILARITY}
            for r in relationships
        )

    def test_independent_sources_do_not_trigger_illusion(self):
        sources = [
            {
                "source_id": "src_sec",
                "url": "https://sec.gov/edgar/filings",
                "publisher": "SEC EDGAR",
                "body": "Form 8-K: Material disclosure regarding regulatory compliance settlement and board resolution.",
            },
            {
                "source_id": "src_reuters",
                "url": "https://reuters.com/markets/story",
                "publisher": "Reuters",
                "body": "Trading volume surged 45% following quarterly revenue guidance revision by executive committee.",
            },
            {
                "source_id": "src_bloomberg",
                "url": "https://bloomberg.com/news/article",
                "publisher": "Bloomberg",
                "body": "Central bank interest rate decisions weighed heavily on tech sector equities this afternoon.",
            },
        ]

        summary, relationships = corroboration_detector.analyze_sources(sources)

        assert summary.total_sources_scanned == 3
        assert summary.unique_publishers == 3
        assert summary.independent_evidence_chains == 3
        assert summary.corroboration_illusion_detected is False
        assert summary.corroboration_ratio == 1.0


class TestAllegationVsEvidenceMatrixAssessment:
    """Verifies Module A Allegation vs Evidence Matrix 6-state synthesis."""

    def test_product_recall_rumor_scenario_misleading_context(self):
        """Tests the canonical recall rumor scenario from the architectural specification."""
        claim = AtomicClaim.create(
            raw_allegation="Company X recalled all its products today due to contamination.",
            target_entity="Company X",
            predicate="recalled",
            temporal_scope="today",
            subject_scope="global_or_universal",
        )

        # 1 historical recall from 2021 (temporal mismatch)
        hist_link = EvidenceLink.create(
            claim_id=claim.claim_id,
            source_id="src_old",
            source_url="https://fda.gov/recalls/2021",
            publisher="FDA Archives",
            passage_text="In 2021, Company X conducted a voluntary recall of lot #44.",
            passage_offsets=(0, 60),
            stance=StanceType.MENTIONS,
            confidence=0.75,
            rationale="Passage confirms a historical recall from 2021, but does not match 'today'.",
            temporal_match=False,
        )

        # 1 corporate denial
        denial_link = EvidenceLink.create(
            claim_id=claim.claim_id,
            source_id="src_denial",
            source_url="https://companyx.com/news/recall-statement",
            publisher="Company X PR",
            passage_text="Company X strongly denies social media rumors of a nationwide recall.",
            passage_offsets=(0, 70),
            stance=StanceType.CONTRADICTS,
            confidence=0.85,
            rationale="Passage records an explicit corporate denial.",
            is_corporate_denial=True,
            temporal_match=True,
        )

        item = assessment_engine.assess_claim(
            claim=claim,
            evidence_links=[hist_link, denial_link],
        )

        assert item.verdict == EpistemicOutcome.MISLEADING_CONTEXT
        assert DeceptiveFramingType.OUT_OF_CONTEXT_MEDIA in item.deceptive_framing_flags
        assert len(item.corporate_denials) == 1
        assert "historical" in item.verified_record_summary.lower()
        assert "CONTEXT WARNING" in item.action_advisory

    def test_corporate_denial_alone_yields_unverified_not_refuted(self):
        """Verifies corporate denial invariant: denial != proof of falsity."""
        claim = AtomicClaim.create(
            raw_allegation="Company X executives were subpoenaed today",
            target_entity="Company X",
            predicate="legal_or_regulatory_action",
            temporal_scope="today",
        )

        denial_link = EvidenceLink.create(
            claim_id=claim.claim_id,
            source_id="src_spokesperson",
            source_url="https://companyx.com/press",
            publisher="Company X Communications",
            passage_text="A spokesperson denied reports of any subpoenas, stating business continues normally.",
            passage_offsets=(0, 85),
            stance=StanceType.CONTRADICTS,
            confidence=0.85,
            rationale="Passage records an explicit corporate denial.",
            is_corporate_denial=True,
        )

        item = assessment_engine.assess_claim(
            claim=claim,
            evidence_links=[denial_link],
        )

        # Invariant: Must be UNVERIFIED, NOT REFUTED!
        assert item.verdict == EpistemicOutcome.UNVERIFIED
        assert item.verdict != EpistemicOutcome.REFUTED
        assert any("corporate denial alone" in gap.lower() for gap in item.unresolved_uncertainty)

    def test_supported_claim_generates_schema_org_dossier(self):
        claim = AtomicClaim.create(
            raw_allegation="Company X acquired Startup Y for $500M",
            target_entity="Company X",
            predicate="acquisition",
        )

        sec_link = EvidenceLink.create(
            claim_id=claim.claim_id,
            source_id="src_sec",
            source_url="https://sec.gov/Archives/edgar/data/companyx-8k.htm",
            publisher="SEC EDGAR",
            passage_text="Company X completed acquisition of Startup Y for aggregate consideration of $500 million.",
            passage_offsets=(100, 203),
            stance=StanceType.SUPPORTS,
            confidence=0.95,
            rationale="Official regulatory filing directly substantiates acquisition.",
        )

        item = assessment_engine.assess_claim(
            claim=claim,
            evidence_links=[sec_link],
        )

        assert item.verdict == EpistemicOutcome.SUPPORTED

        corrob_summary = CorroborationSummary(
            total_sources_scanned=1,
            unique_publishers=1,
            independent_evidence_chains=1,
            syndicated_reprints_count=0,
            corroboration_illusion_detected=False,
            corroboration_ratio=1.0,
            groups=[
                CorroborationGroup(
                    group_id="grp_1",
                    primary_origin_publisher="SEC EDGAR",
                    primary_origin_url="https://sec.gov/Archives/edgar/data/companyx-8k.htm",
                    reprint_publishers=[],
                    all_source_ids=["src_sec"],
                    is_independent=True,
                    syndication_ratio=0.0,
                )
            ],
        )

        dossier = assessment_engine.build_dossier(
            investigation_id="inv_test_001",
            query="Company X acquired Startup Y",
            entity="Company X",
            agent="Scout",
            matrix_items=[item],
            corroboration_summary=corrob_summary,
        )

        assert dossier.overall_verdict == EpistemicOutcome.SUPPORTED
        assert dossier.claim_review_schema is not None
        assert dossier.claim_review_schema["@type"] == "ClaimReview"
        assert dossier.claim_review_schema["reviewRating"]["alternateName"] == "True"
        assert dossier.claim_review_schema["reviewRating"]["ratingValue"] == 5


class TestReportBuilderClaimIntegration:
    """Verifies that all native agents receive Allegation Matrix and Corroboration Summary."""

    def test_scout_report_contains_allegation_matrix_and_corroboration_summary(self):
        from backend.services.report_builder import ReportBuilder

        scout_payload = {
            "entity": "Apple",
            "summary": "SEC 10-Q filing confirmed quarterly revenue growth.",
            "sources": [
                {
                    "source_id": "sec_01",
                    "url": "https://sec.gov/edgar/apple",
                    "publisher": "SEC EDGAR",
                    "snippet": "Apple Inc. reported quarterly revenue of $94.9 billion, up 6 percent year over year.",
                    "is_primary": True,
                },
                {
                    "source_id": "reuters_01",
                    "url": "https://reuters.com/tech/apple-results",
                    "publisher": "Reuters",
                    "snippet": "Apple beat Wall Street revenue forecasts on strong iPhone sales.",
                    "is_primary": False,
                },
            ],
            "findings": ["Quarterly revenue reached $94.9B."],
        }

        report = ReportBuilder.from_scout_result(
            query="Apple quarterly revenue growth",
            scout_data=scout_payload,
        )

        # Unified report properties
        report_dict = report.to_dict()
        assert "allegation_matrix" in report_dict
        assert len(report_dict["allegation_matrix"]) >= 1
        item = report_dict["allegation_matrix"][0]
        assert "verdict" in item
        assert "allegation_summary" in item
        assert "verified_record_summary" in item
        assert "action_advisory" in item

        assert "corroboration_summary" in report_dict
        assert "corroboration_illusion_detected" in report_dict["corroboration_summary"]

        assert "misinformation_dossier" in report_dict
        assert report_dict["misinformation_dossier"]["claim_review_schema"]["@type"] == "ClaimReview"

