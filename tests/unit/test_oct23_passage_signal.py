"""Fictional adversarial controls for selection, not new live-source proof."""
import copy

import pytest

from backend.services.research.content_roles import NON_EVENT_ROLES, paragraph_role
from backend.services.research.financial_context import (
    extract_financial_metrics_and_scales, financial_passage_context,
)
from backend.services.research.passage_extractor import has_usable_passage, passage_extractor
from backend.services.research.passage_records import captured_passages
from backend.services.research.research_models import EvidenceItem


def source(text, **kwargs):
    return EvidenceItem(id="fixture", canonical_url="https://publisher.test/reports/lumen",
        title="Lumen quarterly financial results", content=text, content_depth="PARTIAL_CONTENT", **kwargs)


@pytest.mark.parametrize("text", [
    "Which of the following is the red indicator that has declined in inverse proportion to Lumen's revenue?",
    "Did Lumen report USD 12 billion of revenue in the third quarter?",
    "Question 3: How much revenue did Lumen report in FY2026?",
    "Choose the correct answer below: Lumen revenue rose by 10% or 20%.",
    "Select one of the following revenue figures for Lumen: USD 12 million or USD 13 million.",
])
def test_questions_and_quiz_prompts_are_inspectable_not_financial_propositions(text):
    item = source(text)
    original = copy.deepcopy(item.content)
    assert paragraph_role(text) in NON_EVENT_ROLES
    assert not has_usable_passage(item)
    passage_extractor.extract_passages([item], "Lumen", domain="financial")
    assert not item.relevant_excerpt
    assert item.content == original
    assert not financial_passage_context(text)["financial_assessment_eligible"]
    assert all(row["relevance"] != "DIRECTLY_RELEVANT"
               for row in captured_passages(source(text), "financial", "Lumen"))


@pytest.mark.parametrize("text,domain,target", [
    ('Lumen reported revenue of USD 12 million; the auditor asked "Were these figures verified?"', "financial", "Lumen"),
    ('Aria Vale said "How can people identify a fake account? Verify the original source before sending money."', "personal", "Aria Vale"),
    ('Lumen warns about phishing: do not provide passwords to accounts asking "Do you want a refund?"', "brand", "Lumen"),
    ('Police reported that Lumen counterfeit goods were seized after victims asked "Is this seller authorized?"', "brand", "Lumen"),
    ('Why did Lumen revenue fall? Lumen reported that sales fell 12 percent after the factory closed.', "financial", "Lumen"),
])
def test_reported_questions_safety_warnings_incidents_and_answers_survive(text, domain, target):
    item = source(text, metadata={"read_success": True, "page_metadata": {"body_kind": "ARTICLE_BODY"}})
    passage_extractor.extract_passages([item], target, domain=domain)
    assert item.relevant_excerpt == text
    assert item.content[item.excerpt_start:item.excerpt_end] == text


def test_direct_reported_amount_outranks_investor_call_logistics_and_quiz():
    logistics = "Lumen will webcast its third quarter FY2026 earnings conference call at 2:00 p.m. from its investor relations website. Earnings documents are posted before the call."
    quiz = "Which of the following is the red indicator that has declined in inverse proportion to Lumen's revenue?"
    result = "Lumen achieved revenue of USD 6.76 billion in its third quarter of FY2026, representing 13% year-over-year growth. Diluted earnings per share was USD 4.62 on a GAAP basis."
    text = logistics + "\n\n" + quiz + "\n\n" + result
    item = source(text)
    passage_extractor.extract_passages([item], "Lumen", domain="financial")
    assert item.relevant_excerpt == result
    assert item.content == text
    assert text[item.excerpt_start:item.excerpt_end] == result


def test_single_issuer_assertion_outranks_list_of_company_names():
    roundup = "The publisher reported its list of companies likely to issue earnings surprises. This week's list includes Aster, Lumen, Cedar and Birch, whose reports are due soon."
    result = "Lumen reported quarterly revenue of USD 3 billion, an increase of 8 percent compared with the prior-year quarter."
    item = source(roundup + "\n\n" + result)
    passage_extractor.extract_passages([item], "Lumen", domain="financial")
    assert item.relevant_excerpt == result


def test_exact_source_title_is_not_a_body_passage_even_without_h1_span_metadata():
    headline = "Lumen reports earnings with revenue of USD 6.76 billion, beating estimates"
    body = "Lumen reported third quarter revenue of USD 6.76 billion, an increase of 13 percent. The report also described the basis of its adjusted earnings."
    item = source(headline + "\n\n" + body)
    item.title = headline
    passage_extractor.extract_passages([item], "Lumen", domain="financial")
    assert item.relevant_excerpt == body
    assert item.content[item.excerpt_start:item.excerpt_end] == body


def test_reported_amount_and_consensus_range_do_not_share_actual_result_role():
    text = "Lumen reported revenue of USD 6.618 billion, above the analyst consensus of USD 6.46 billion to USD 6.58 billion."
    rows = extract_financial_metrics_and_scales(text)
    assert [row["amount_role"] for row in rows] == [
        "REPORTED_AMOUNT", "FORECAST_OR_ESTIMATE", "FORECAST_OR_ESTIMATE"]
    assert all(text[row["start"]:row["end"]] == row["amount_text"] for row in rows)


def test_explicit_forecast_metrics_never_become_reported_actuals():
    text = "Lumen expects revenue of USD 9 billion to USD 10 billion next quarter."
    assert {row["amount_role"] for row in extract_financial_metrics_and_scales(text)} == {"FORECAST_OR_ESTIMATE"}


def test_question_context_cannot_unlock_financial_assessment_with_recent_date():
    text = "Did Lumen report net profit of USD 12 million in Q3 FY2026?"
    context = financial_passage_context(text, published_at="2026-10-22", observed_at="2026-10-23", issuer="Lumen")
    assert not context["financial_assessment_eligible"]
    assert context["content_kind"] == "NON_ASSERTIVE_PROMPT"
    assert not context["normalized_metrics"]


@pytest.mark.parametrize("currency,expected", [("USD", "USD"), ("US$", "USD"),
    ("INR", "INR"), ("EUR", "EUR"), ("GBP", "GBP"), ("$", "DOLLAR_SYMBOL_UNSPECIFIED")])
def test_financial_observation_currency_is_only_the_observed_label(currency, expected):
    from backend.services.research.financial_observations import financial_observations
    text = f"For the quarter ended June 30, 2026. Revenue was {currency}12 million."
    rows = financial_observations(text, "source")
    assert rows[0]["currency"] == expected
    assert text[rows[0]["start"]:rows[0]["end"]] == rows[0]["text"]


def test_matching_bare_dollar_symbols_do_not_establish_comparable_currency():
    from backend.services.research.financial_observations import financial_observations, compare_financial_observations
    text = "For the quarter ended June 30, 2026. Revenue was $12 million."
    result = compare_financial_observations(text, financial_observations(text, "source"))
    assert result[0]["status"] == "INSUFFICIENT_COMPARABLE_CONTEXT"
