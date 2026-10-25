"""Offline source-span/paragraph-boundary controls, not live yield evidence."""
import copy

from backend.schemas.evidence_inspection import inspect_evidence
from backend.services.research.evidence_workbench import build_evidence_workbench, select_source_passages
from backend.services.research.passage_extractor import PassageExtractor
from backend.services.research.research_models import EvidenceItem


FIRST = ("Quartz Tools reported revenue of USD 40 million for the quarter. "
         "The figures have not been independently audited.")
SECOND = ("Quartz Tools reported operating profit of USD 8 million for the same quarter. "
          "Its statement excludes discontinued operations.")


def capture(body, identity):
    item = EvidenceItem(id=identity, canonical_url="https://publisher.example/" + identity,
        title="Quartz Tools results", content=body, content_depth="DEEP_READ", acquired_id="capture",
        metadata={"layer2_eligible": True, "read_success": True,
                  "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    PassageExtractor().extract_passages([item], "Quartz Tools", domain="financial")
    return item


def public(item):
    return {"evidence_id": item.id, "url": item.canonical_url, "title": item.title,
            "extraction": inspect_evidence(item)}


def test_merged_syndicated_paragraph_does_not_double_published_words():
    split = capture(FIRST + "\n\n" + SECOND, "split")
    merged = capture(FIRST + " " + SECOND, "merged")
    before = copy.deepcopy([split.to_dict(), merged.to_dict()])
    result = build_evidence_workbench([public(split), public(merged)])
    assert len(result["passages"]) == 1
    row = result["passages"][0]
    assert row["text"] == merged.content
    assert merged.content[row["start"]:row["end"]] == row["text"]
    assert row["captured_text_sha256"] == inspect_evidence(merged)["captured_text_sha256"]
    assert result["accounting"]["published_unique_words"] == len(merged.content.split())
    assert result["accounting"]["contained_text_observations"] == 2
    assert {alias["evidence_id"] for alias in row["contained_source_observations"]} == {"split"}
    assert not row.get("also_reported_by")
    assert [split.to_dict(), merged.to_dict()] == before


def test_containment_preserves_qualifications_and_exact_identical_aliases():
    short = capture(FIRST, "short")
    short_alias = capture(FIRST, "short_alias")
    qualified = capture(FIRST + " The company later corrected the figure to USD 32 million.", "qualified")
    qualified_alias = capture(qualified.content, "qualified_alias")
    result = build_evidence_workbench([public(item) for item in
        (short, short_alias, qualified, qualified_alias)])
    row, = result["passages"]
    assert row["text"] == qualified.content
    assert [alias["evidence_id"] for alias in row["also_reported_by"]] == ["qualified_alias"]
    assert {alias["evidence_id"] for alias in row["contained_source_observations"]} == {"short", "short_alias"}
    assert result["accounting"]["identical_text_observations"] == 2
    assert result["accounting"]["published_unique_words"] == len(qualified.content.split())


def test_source_selection_never_repeats_multi_paragraph_winner_spans():
    body = FIRST + "\n\n" + SECOND
    item = capture(body, "window")
    rows, accounting = select_source_passages(item, [(2.0, FIRST), (2.0, SECOND)],
        body, "financial", "Quartz Tools")
    assert [row["text"] for row in rows] == [body]
    assert accounting["overlapping_source_spans_omitted"] == 2
    assert item.content[rows[0]["start"]:rows[0]["end"]] == body


def test_workbench_defends_against_overlapping_valid_stored_spans():
    item = capture(FIRST + " " + SECOND, "stored")
    rows = item.metadata["evidence_passages"]
    overlap = {**rows[0], "passage_id": "overlap", "text": FIRST, "end": len(FIRST)}
    rows.append(overlap)
    result = build_evidence_workbench([public(item)])
    assert len(result["passages"]) == 1
    assert result["accounting"]["overlapping_source_spans_omitted"] == 1
    assert result["accounting"]["published_unique_words"] == len(item.content.split())


def test_partial_cross_source_context_is_not_clipped_or_silently_dropped():
    first = capture(FIRST + " " + SECOND, "first")
    third = "Quartz Tools denied that these figures constitute audited results and asked readers to inspect the full filing."
    second = capture(SECOND + " " + third, "second")
    result = build_evidence_workbench([public(first), public(second)])
    assert {row["text"] for row in result["passages"]} == {first.content, second.content}
    assert result["accounting"]["contained_text_observations"] == 0


def test_blank_stored_passage_is_invalid_without_breaking_projection():
    item = capture(FIRST, "blank")
    data = public(item)
    row = data["extraction"]["evidence_passages"][0]
    data["extraction"]["evidence_passages"] = [{**row, "text": "   "}]
    result = build_evidence_workbench([data])
    assert result["passages"] == []
    assert result["accounting"]["invalid_passage_records"] == 1
