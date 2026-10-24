"""Short genuine saved excerpt plus narrow synthetic attribution controls.

No network/model call or original capture modification. The fixture retains
17 exact source words and the original body hash/count, not the 783-word article.
Whole-body replay is a separately recorded terminal check from the temp pool.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend.services.research.harvesting import diversified_queries
from backend.services.research.passage_extractor import has_usable_passage, passage_extractor
from backend.services.research.passage_records import captured_passages, public_statement_attribution
from backend.services.research.research_models import EvidenceItem


def saved_quote():
    return json.loads((Path(__file__).parent / "fixtures" / "personal_quote_native_20261020.json").read_text(encoding="utf-8"))


def evidence():
    captured = saved_quote()
    return EvidenceItem(id=captured["source_id"], canonical_url=captured["source_url"], title="Captured attributed-quotation excerpt",
        content=captured["excerpt"], content_depth="PARTIAL_CONTENT", published_at=captured["published_at"],
        query_class="harvest_impersonation", metadata={"read_success": True,
            "acquisition_objective": "IDENTITY_THREAT", "page_metadata": captured["page_metadata"]})


def test_short_genuine_excerpt_has_exact_attribution_not_identity_proof():
    captured, item = saved_quote(), evidence()
    assert len(item.content.split()) <= 25
    assert captured["original_word_count"] == 783
    assert hashlib.sha256(item.content.encode()).hexdigest() == captured["excerpt_sha256"]
    original = item.content
    assert item.content == original
    assert item.metadata["acquisition_objective"] == "IDENTITY_THREAT"
    assert public_statement_attribution(item, item.content, "Sundar Pichai") == "REPORTED_QUOTATION"
    observed = [row for row in captured_passages(item, "personal", "Sundar Pichai") if row["attribution"] == "REPORTED_QUOTATION"]
    assert observed and all(row["claim_status"] == "UNVERIFIED" and row["content_role"] == "PUBLIC_STATEMENT" for row in observed)
    assert not item.is_authenticated


def test_synthetic_complete_prose_selects_exact_reported_paragraph():
    item = evidence()
    item.id = "synthetic_article"
    item.canonical_url = "https://publisher.test/research/aria-vale-statement"
    item.title = "Synthetic fictional-speaker attribution control"
    item.content = ('Aria Vale said: "This is a useful public observation, not authentication of an identity." '
                    'The article reports a public statement and is not independent proof that its attribution is correct.')
    passage_extractor.extract_passages([item], "Aria Vale", domain="personal")
    assert has_usable_passage(item)
    assert item.content[item.excerpt_start:item.excerpt_end] == item.relevant_excerpt
    assert public_statement_attribution(item, item.relevant_excerpt, "Aria Vale") == "REPORTED_QUOTATION"


@pytest.mark.parametrize("objective", ["PUBLIC_STATEMENT", "IDENTITY_THREAT"])
@pytest.mark.parametrize("text", [
    'A fabricated quote claims Sundar Pichai said "Buy the product immediately and make a profit."',
    'Sundar Pichai never said "Buy the product immediately and make a profit."',
    'A debunked claim suggests Sundar Pichai said "Buy the product immediately and make a profit."',
    'Sundar Pichai listened while Alex Doe said "Technology can shape an optimistic future."',
])
def test_new_article_path_never_promotes_false_or_other_speaker_quotes(text, objective):
    item = evidence()
    item.content = text
    item.metadata["acquisition_objective"] = objective
    if objective == "PUBLIC_STATEMENT" and "Alex Doe" in text:
        # The legacy author/section route is out of scope; exercise the new
        # incidental exact-full-speaker path for this unrelated-speaker check.
        item.metadata["acquisition_objective"] = "IDENTITY_THREAT"
    assert public_statement_attribution(item, text, "Sundar Pichai") is None


def test_snippet_profile_or_unobserved_body_cannot_use_incidental_attribution_path():
    original = evidence()
    paragraph = next(part for part in original.content.split("\n\n") if "Sundar Pichai said" in part)
    for change in ("metadata", "snippet", "not_acquired"):
        item = copy.deepcopy(original)
        if change == "metadata":
            item.content_depth = "PROFILE_METADATA"
        elif change == "snippet":
            item.metadata["page_metadata"].pop("body_quality", None)
            item.metadata["page_metadata"].pop("body_kind", None)
        else:
            item.metadata["read_success"] = False
        assert public_statement_attribution(item, paragraph, "Sundar Pichai") is None


def test_statement_discovery_scope_is_explicit_and_not_assigned_to_threat_queries():
    rows = diversified_queries("Unfamiliar Public Person", "personal", "monitor identity threats and impersonation")
    assert rows[0]["acquisition_objective"] == "IDENTITY_THREAT"
    threat_rows = [row for row in rows if row["query_class"] in {"harvest_impersonation", "harvest_identity"}
                   or "allegation" in row["query_text"]]
    assert threat_rows and all(row["acquisition_objective"] == "IDENTITY_THREAT" for row in threat_rows)
    statement_rows = [row for row in rows if row["acquisition_objective"] == "PUBLIC_STATEMENT"]
    assert statement_rows
    assert all(any(term in row["query_text"] for term in ("statement", "interview", "speech")) for row in statement_rows)
