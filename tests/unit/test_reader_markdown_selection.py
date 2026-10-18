"""Synthetic reader extraction controls, not independent research acceptance."""
import hashlib
import pytest
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_reader_markdown


@pytest.mark.parametrize("heading", ["# Incident report", "Incident report\n==============="])
def test_unique_observed_heading_preserves_article_after_long_navigation(heading):
    text = "Title: Incident report\n\nPublished Time: 2024-07-02T13:06:09-04:00\n\nMarkdown Content:\n" + (
        "[Navigation](https://example.org/menu)\n\n" * 200) + heading + "\n\nOfficials reported seizures. The seller denied the allegation.\n\nCorrection: disposition is pending."
    result = extract_reader_markdown(text)
    assert result["text"].startswith(heading)
    assert "seller denied" in result["text"] and "Correction:" in result["text"]
    assert "Navigation" not in result["text"]
    assert "Navigation" in result["raw_capture"]["text"]
    assert result["raw_capture"]["source_text_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert result["page_metadata"]["content_scope"] == "reader_heading_match"
    assert result["page_metadata"]["reader_declared_metadata_verified"] is False


def test_ambiguous_heading_does_not_silently_drop_an_account():
    text = "Title: Incident report\n\nMarkdown Content:\nNavigation\n\n# Incident report\n\nFirst account.\n\n# Incident report\n\nConflicting account."
    result = extract_reader_markdown(text)
    assert result["text"].startswith("Navigation")
    assert "First account" in result["text"] and "Conflicting account" in result["text"]
    assert result["page_metadata"]["content_scope"] == "reader_body_unscoped"


def test_bare_markdown_is_not_assigned_fabricated_metadata():
    text = "# Actual page\nThe allegation is not independently established."
    result = extract_reader_markdown(text)
    assert result["text"] == text and result["page_metadata"] == {}


def test_jina_fallback_selects_before_display_limit_and_keeps_raw(monkeypatch):
    from backend.infrastructure.acquisition.adapters.web import jina
    monkeypatch.setattr(jina, "is_safe_url", lambda _: (True, "public test control"))
    text = "Title: Incident report\n\nMarkdown Content:\n" + "Navigation\n\n" * 500 + "# Incident report\n\nThe allegation is not independently established."
    result = extract_reader_markdown(text)
    monkeypatch.setattr(jina, "read_article_via_jina", lambda *a, **kw: {
        "status": "success", "content": result["text"], "raw_capture": result["raw_capture"],
        "page_metadata": result["page_metadata"], "title": "Incident report"})
    view = jina.execute_web_read("https://example.org/report", max_chars=50)
    assert view["content"].startswith("# Incident report") and len(view["content"]) == 50
    assert view["truncated"] is True and "Navigation" in view["raw_capture"]["text"]
