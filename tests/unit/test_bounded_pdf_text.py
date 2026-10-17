"""Real local PDF parser controls; no network or historical data."""
from io import BytesIO
import subprocess

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def pdf_bytes(pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 50 700 Td (Acme Q1 2026 revenue was USD 10 million, not USD 20 million.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("fixture-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_real_pdf_text_preserves_negation_and_page_offsets():
    from backend.infrastructure.acquisition.adapters.web.pdf_text import extract_pdf_text
    result = extract_pdf_text(pdf_bytes())
    assert "not USD 20 million" in result["text"]
    page = result["pages"][0]
    assert result["text"][page["start"]:page["end"]].startswith("[PDF page 1]")
    assert result["table_structure_verified"] is False and not result["truncated"]


def test_pdf_page_limit_and_encryption_are_explicit():
    from backend.infrastructure.acquisition.adapters.web.pdf_text import extract_pdf_text
    result = extract_pdf_text(pdf_bytes(pages=10))
    assert len(result["pages"]) == 8 and result["page_count"] == 10 and result["truncated"]
    with pytest.raises(ValueError):
        extract_pdf_text(pdf_bytes(encrypted=True))


@pytest.mark.parametrize("body", [b"<html>not a PDF</html>", b"%PDF-" + b"x" * 1_000_000, b"%PDF-invalid"], ids=["html", "oversized", "malformed"])
def test_invalid_and_oversized_pdf_rejected(body):
    from backend.infrastructure.acquisition.adapters.web.pdf_text import extract_pdf_text
    with pytest.raises(ValueError):
        extract_pdf_text(body)


def test_parser_deadline_and_credentials_not_inherited(monkeypatch):
    from backend.infrastructure.acquisition.adapters.web import pdf_text
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-secret")
    def timeout(*args, **kwargs):
        assert "GEMINI_API_KEY" not in kwargs["env"]
        assert kwargs["timeout"] <= 2.5
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(pdf_text.subprocess, "run", timeout)
    with pytest.raises(TimeoutError):
        pdf_text.extract_pdf_text(b"%PDF-fixture")


def test_native_pdf_uses_existing_bounded_transport_and_exports_inspection(monkeypatch):
    from backend.services.agent_reach.native import executor
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    from backend.schemas.evidence_inspection import inspect_evidence
    monkeypatch.setattr(executor, "is_safe_url", lambda url: (True, ""))
    calls = []
    def fetch(url, **kwargs):
        calls.append(kwargs)
        return BoundedHTTPResponse(pdf_bytes(), url, 200, "application/pdf", {}, 1, 1)
    monkeypatch.setattr(executor, "fetch_public_http", fetch)
    result = executor.NativeExecutor().execute_web_read("https://issuer.example/q1.pdf")
    assert len(calls) == 1 and calls[0]["max_bytes"] == 1_000_000
    inspection = inspect_evidence({"content": result["content"], "url": result["url"],
        "content_depth": "PARTIAL_CONTENT", "metadata": {"page_metadata": result["page_metadata"]}})
    assert inspection["page_observations"]["pdf_pages"][0]["page"] == 1
    assert inspection["source_observations"]["table_structure_verified"] is False
