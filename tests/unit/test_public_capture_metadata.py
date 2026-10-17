"""Public metadata boundary: preserve extraction context, never auth envelopes."""
from backend.services.research.research_models import EvidenceItem


def test_public_metadata_retains_pdf_context_but_not_credentials():
    from backend.schemas.evidence_inspection import public_capture_metadata, inspect_evidence
    item = EvidenceItem(id="pdf", canonical_url="https://issuer.example/quarter.pdf", content="Captured financial text." * 4,
        content_depth="PARTIAL_CONTENT", metadata={"authorization": "private-token", "cookie": "private-cookie",
        "content_role": "DOCUMENT_INDEX", "page_metadata": {"content_scope": "PDF_TEXT_LAYER",
            "pdf_page_count": 3, "pdf_pages": [{"page": 1, "start": 0, "end": 40}, {"page": 2, "start": 40, "end": 200},
                                            {"page": 3, "start": 200, "end": 500}], "password": "secret"},
        "raw_capture": {"text": "Original raw text " * 20, "selection_method": "PYPDF_LAYOUT_TEXT_LAYER", "cookie": "secret"}})
    public = public_capture_metadata(item, max_chars=100)
    assert "authorization" not in public and "cookie" not in public
    assert "password" not in public["page_metadata"] and "cookie" not in public["raw_capture"]
    assert len(public["raw_capture"]["text"]) == 100 and public["raw_capture"]["truncated"]
    inspection = inspect_evidence({"content": item.content, "metadata": public, "content_depth": "PARTIAL_CONTENT"})
    pages = inspection["page_observations"]["pdf_pages"]
    assert len(pages) == 2 and pages[1]["end"] == len(item.content) and pages[1]["text_truncated"]
    assert inspection["source_observations"]["content_role"] == "DOCUMENT_INDEX"
    assert inspection["evidentiary_use"] == "DISCOVERY_ONLY"


def test_empty_metadata_preserves_legacy_truncation_contract():
    from backend.schemas.evidence_inspection import public_capture_metadata
    assert public_capture_metadata(EvidenceItem(id="empty")) == {"truncated": False}
