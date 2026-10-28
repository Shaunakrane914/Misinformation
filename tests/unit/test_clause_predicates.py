"""Finite-predicate recognition (replaces a hand-picked verb list) and the ECS regression.

Offline only: synthetic sentences plus saved captures. The ECS fixture is the genuine
2026-10-24 battery-recycling article captured by a Trending run whose relevant paragraphs were
rejected as NO_RELEVANT_PASSAGE because "will present", "covers", "states" and "evaluates"
were not on the old verb list. No network, model or provider call is made here.
"""
import hashlib
import importlib
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from backend.services.research.clause_predicates import find_finite_predicate, has_finite_predicate
from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage
from backend.services.research.passage_records import captured_passages
from backend.services.research.raw_pool import RawAcquisitionPool
from scripts.audits.requalify_raw_pool import requalify_payload

FIXTURES = Path(__file__).parent / "fixtures"
LEGACY_VERBS = re.compile(r"\b(?:is|are|was|were|has|have|allows|contains|includes|limits|rated)\b", re.I)


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 40]


# ── The mechanism, on synthetic sentences ────────────────────────────────────────────────────

@pytest.mark.parametrize("sentence, verb", [
    ("Researchers from the institute will present work on thermal-runaway mitigation at the meeting.", "will"),
    ("The third area covers battery recycling and failure diagnostics.", "covers"),
    ("The institute states that this research evaluates practical recycling processes.", "states"),
    ("The study evaluates how recycled cathodes perform after repeated charging cycles.", "evaluates"),
    ("The company announced a new recycling plant in Texas on Tuesday.", "announced"),
    ("He invested $10,600 in Warren Buffett's Berkshire Hathaway in 1980.", "invested"),
    ("SEC states that the filing remains under review by the staff.", "states"),
    ("High-bandwidth memory, or HBM, has become important to the industry.", "has"),
    ("EPS of $5.80 is below last quarter's figure, signaling slower growth.", "is"),
    ("“We are seeing strong demand,” the chief executive told Reuters.", "are"),
    ("We are announcing a leadership transition that takes effect next year.", "are"),
    ("The agency could not confirm whether the report is accurate.", "could"),
    ("Analysts have also warned that margins may narrow over the next quarter.", "have"),
    ("That could make the current cycle more durable than traditional semiconductor upcycles.", "could"),
    ("The study found that it could reduce costs for recyclers across the region.", "found"),
    ("The department funded a pilot in the region last year.", "funded"),
])
def test_ordinary_finite_clauses_are_recognized(sentence, verb):
    assert find_finite_predicate(sentence) == verb
    assert has_finite_predicate(sentence)


@pytest.mark.parametrize("text, why", [
    ("Why Toyota Tsusho is leaning into EV-battery recycling", "unpunctuated headline"),
    ("Royal Mail announces plans to cut up to 2,500 jobs", "unpunctuated headline"),
    ("AI Has Won the Shopping Trip. Not the Wallet.", "Title Case: capitalized verb, no clause"),
    ("Is Justice Being Served or Is It Just Political Maneuvering?", "question"),
    ("What children face online that parents may not see.", "wh-word fragment"),
    ("Discover how Upstage dramatically improved AI model training speed.", "imperative call to action"),
    ("Battery recycling research results at the 250th meeting in Calgary.", "noun phrase: plural noun, not a verb"),
    ("Lock in 4% p.a. stable yields with US Treasuries.", "adjective + plural noun"),
    ("3 states report battery recycling targets for the coming decade.", "number + plural noun"),
    ("Battery recycling services and charging stations across the region.", "words ending in s are not verbs"),
    ("Expert-curated, low-volatility funds designed to outperform money market yields.", "reduced relative before 'to'"),
    ("Customers highlighted include Accenture, Merck and SAP.", "participle followed by the real verb"),
    ("A pilot funded by the department in the region.", "participle in a noun phrase, no finite verb"),
    ("Rising recycled content mandates in the EU and US drive demand.", "clause-initial -ing modifier"),
    ("NC mail-in ballot requests plunge 33% as the deadline looms.", "compound noun + base verb"),
    ("Keywords: battery safety, thermal runaway, lithium-ion, sodium-ion batteries, battery recycling.", "metadata label"),
    ("Article Title: UL Research Institutes to present battery safety research at the meeting.", "metadata label"),
    ("This site uses cookies to improve the experience of every visitor.", "cookie boilerplate"),
    ("Subscribe to our newsletter to get the latest updates every single week.", "newsletter boilerplate"),
    ("Put your idle cash to work and watch your savings grow faster.", "copy addressed to the reader"),
    ("THE BEST BATTERY RECYCLING DEALS ARE ON SALE THIS WEEKEND ONLY.", "all caps banner"),
    ("A full-lifecycle field study found that foliar sprays of copper oxide reduced stress ...", "truncated snippet"),
    ("<p>Dyson is represented by Baker McKenzie.</p>", "markup"),
    ("In this photo taken from video, officials stand in a glass cage during a hearing.", "photo caption"),
    ("Share on Facebook Share on Twitter Share on Linkedin Share on Reddit Share on Telegram", "share row"),
    ("Do not ignore these signs and stop to ask for help if unsure.", "plural demonstrative + noun, not pronoun + verb"),
    ("Engineered to capture dust and microscopic particles, which can build up over time.", "relative clause only, no main clause"),
    ("To find strong companies that may deliver above-average returns, please check out the screener.", "call to action"),
])
def test_structural_negative_controls_are_not_propositions(text, why):
    assert find_finite_predicate(text) is None, why
    assert not has_usable_passage({"content": text, "content_depth": "FULL_ARTICLE"}), why


def test_a_reduced_relative_never_supplies_the_verb_but_the_main_clause_does():
    # "funded" is a participle modifying "pilot"; the finite verb of this sentence is "received".
    assert find_finite_predicate("A pilot funded by the department received public attention.") == "received"
    assert find_finite_predicate("The department funded a pilot in the region last year.") == "funded"


def test_second_person_inside_a_quotation_is_still_reported_speech():
    assert has_finite_predicate('The spokesperson said "if you pay late, we will charge a fee" on Monday.')
    assert not has_finite_predicate("If you pay late, the company will charge you a fee on Monday.")


def test_a_bare_keyword_is_not_enough():
    # The old condition could be satisfied by any "is"; the new one never keys on the topic word.
    assert not has_finite_predicate("Battery recycling battery safety electric vehicles energy storage analysis.")


# ── The genuine saved ECS capture ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ecs_pool():
    return _load("oct25_ecs_battery_recycling_raw_pool.json")


@pytest.fixture(scope="module")
def ecs_record(ecs_pool):
    return ecs_pool["sources"][0]


def test_ecs_capture_is_the_unmodified_saved_source(ecs_pool, ecs_record):
    text = ecs_record["readable_text"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == ecs_record["raw_content_hash"]
    assert ecs_record["raw_content_hash"] == ecs_pool["_fixture_provenance"]["readable_text_sha256"]
    assert ecs_record["source_url"].startswith("https://bioengineer.org/battery-safety-sodium-ion")
    assert ecs_record["word_count"] == len(text.split()) == 801
    assert ecs_record["source_type"] == "ARTICLE_BODY"


def test_formerly_rejected_paragraphs_now_pass_and_the_rest_stay_rejected(ecs_record):
    verdict = {p: has_usable_passage({"content": p, "content_depth": "PARTIAL_CONTENT"})
               for p in _paragraphs(ecs_record["readable_text"])}

    def verdicts_for(prefix):
        return [ok for paragraph, ok in verdict.items() if paragraph.startswith(prefix)]

    assert verdicts_for("Researchers from UL Research Institutes") == [True]          # "will present"
    assert verdicts_for("The third area covers battery recycling") == [True]          # "covers", "states", "evaluates"
    # Navigation and metadata rows must remain rejected.
    for prefix in ("Share on Facebook", "Subject of Research:", "Article Title:", "Article References:",
                   "Keywords:", "News Source:", "Tags:"):
        assert verdicts_for(prefix) == [False], prefix
    # Three paragraphs were accepted before ("said", "focuses", "works"); three more are newly accepted
    # ("will present", "addresses", "covers"/"states"/"evaluates"). The seven label/navigation rows are not.
    assert sum(verdict.values()) == 6 and len(verdict) == 13


def _with_legacy_predicate(monkeypatch):
    module = importlib.import_module("backend.services.research.passage_extractor")
    monkeypatch.setattr(module, "has_finite_predicate", lambda text: bool(LEGACY_VERBS.search(text)))


def test_before_after_requalification_of_the_exact_capture(ecs_pool, monkeypatch):
    reference = datetime.fromisoformat(ecs_pool["created_at"])
    _with_legacy_predicate(monkeypatch)
    before = requalify_payload(ecs_pool, target="battery recycling", domain="trending", reference_time=reference)
    row = before["requalification"]["decisions"][0]
    assert (row["qualification_status"], row["reasons"], row["passage"]) == ("REJECTED", ["NO_EXACT_USABLE_PASSAGE"], None)
    monkeypatch.undo()

    after = requalify_payload(ecs_pool, target="battery recycling", domain="trending", reference_time=reference)
    row = after["requalification"]["decisions"][0]
    assert row["qualification_status"] == "QUALIFIED" and row["reasons"] == []
    assert row["observed_published_at"] == "2026-10-24T15:38:21+01:00"
    passage = row["passage"]
    body = ecs_pool["sources"][0]["readable_text"]
    assert body[passage["start"]:passage["end"]] == passage["text"]           # exact citation offsets
    assert (passage["start"], passage["end"], passage["word_count"]) == (3315, 4088, 100)
    assert passage["text"].startswith("The third area covers battery recycling and failure diagnostics.")
    assert passage["text"].endswith("post-mortem failure analysis.")
    assert passage["claim_support"] == "NOT_ADJUDICATED"                       # relevance, not a verified finding
    # The saved pool is never rewritten and its source hash is carried through unchanged.
    assert after["raw_acquisition_pool"]["sources"][0]["raw_content_hash"] == ecs_pool["sources"][0]["raw_content_hash"]
    assert after["original_pool_sha256"] == before["original_pool_sha256"]


def test_citation_ids_and_offsets_cover_the_exact_paragraphs(ecs_pool, ecs_record):
    item = next(iter(RawAcquisitionPool.from_export(ecs_pool).to_evidence_items()))
    passages = captured_passages(item, "trending", "battery recycling")
    assert passages and len({p["passage_id"] for p in passages}) == len(passages)
    for p in passages:
        assert item.content[p["start"]:p["end"]] == p["text"]
        assert p["evidence_id"] == item.id
        digest = hashlib.sha256((str(item.id) + ":" + str(p["start"]) + ":" + p["text"]).encode()).hexdigest()[:16]
        assert p["passage_id"] == "ps_" + digest
        assert p["claim_status"] == "UNVERIFIED"
    spans = {(p["start"], p["end"]) for p in passages}
    assert (3315, 4088) in spans                                              # the newly qualified paragraph


def test_extractor_selection_is_exact_for_the_formerly_rejected_article(ecs_pool):
    item = next(iter(RawAcquisitionPool.from_export(ecs_pool).to_evidence_items()))
    item.metadata.update(temporal_required=True, temporal_eligible=True, layer2_eligible=True)
    extracted = PassageExtractor().extract_passages([item], "battery recycling", domain="trending")[0]
    assert extracted.extraction_status == "SUCCESS"
    assert item.content[extracted.excerpt_start:extracted.excerpt_end] == extracted.relevant_excerpt
    assert "covers battery recycling" in extracted.relevant_excerpt


# ── Corpus-derived controls (saved native reports, 2026-10-16..25) ───────────────────────────

CONTROLS = _load("predicate_controls_20261025.json")["controls"]


@pytest.mark.parametrize("control", CONTROLS, ids=lambda c: c["category"] + ":" + c["text"][:28])
def test_saved_corpus_controls(control):
    usable = has_usable_passage({"content": control["text"], "content_depth": "FULL_ARTICLE"})
    assert usable is (control["expected"] == "usable")


def test_controls_cover_every_negative_family_and_real_prose():
    categories = {c["category"].split(":")[1] for c in CONTROLS}
    assert {"markup", "boilerplate_caption_or_cta", "question_headline", "truncated_snippet",
            "unpunctuated_headline_or_label", "reader_addressed_copy", "navigation_or_metadata",
            "newly_accepted", "kept"} <= categories
    assert all(len(c["source_sha256"]) == 64 for c in CONTROLS)
    # Every old false positive in the controls really was accepted by the legacy verb condition
    # or a signal marker, so the controls demonstrate removal, not a case that never passed.
    assert all(c["old_rule_accepted"] for c in CONTROLS if c["category"].startswith("old_false_positive"))
