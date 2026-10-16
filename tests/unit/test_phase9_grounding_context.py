"""Adversarial context controls, not externally adjudicated accuracy cases."""
import pytest

from backend.services.research.proposition_grounding import (
    extract_numeric_tokens, is_authoritative_registry_or_filing, relation,
)
from backend.services.research.research_models import EvidenceItem


def evidence(text, **kwargs):
    return EvidenceItem(id="context", title="Example results", canonical_url="https://example.org/results",
                        content=text, content_depth="PARTIAL_CONTENT", **kwargs)


@pytest.mark.parametrize("claim,passage", [
    ("Example revenue was $50 billion in 2025.", "Example net income was $10 billion in 2025."),
    ("Example revenue was $50 billion in 2025.", "Example revenue was $10 billion in 2024."),
    ("Example revenue was $50 billion in 2025.", "Example revenue was EUR 10 billion in 2025."),
    ("Example revenue increased 20% in 2025.", "Example profit increased 80% in 2025."),
    ("Example profit margin increased 20 percentage points.", "Example profit margin increased 80 percent."),
])
def test_different_metrics_periods_currencies_and_units_abstain(claim, passage):
    assert relation(claim, "Example", evidence(passage))[0] == "NONE"


def test_secondary_number_does_not_refute_matching_revenue():
    claim = "Example revenue was $50 billion in 2025."
    item = evidence("Example revenue was $50 billion in 2025. Net income was $10 billion in 2025.")
    assert relation(claim, "Example", item)[0] == "SUPPORT"


def test_matching_metric_wrong_value_remains_refutable():
    assert relation("Example revenue was $50 billion in 2025.", "Example",
                    evidence("Example revenue was $10 billion in 2025."))[0] == "CONTRADICT"


def test_currency_scale_equivalence_is_supported():
    assert relation("Example revenue was $1 billion in 2025.", "Example",
                    evidence("Example revenue was $1000 million in 2025."))[0] == "SUPPORT"


def test_percentage_symbol_and_percentage_points_are_distinct():
    assert extract_numeric_tokens("20% growth")[0]["val"] == 20
    assert extract_numeric_tokens("20 percentage points")[0]["type"] == "percentage_points"


def test_profile_metadata_cannot_prove_employment():
    item = evidence("Example is the chief executive officer of Corporation.")
    item.content_depth = "PROFILE_METADATA"
    assert relation("Example is the chief executive officer of Corporation.", "Example", item)[0] == "NONE"


def test_utility_host_suffix_spoof_is_not_authoritative():
    item = evidence("An account portal.", source_role="UTILITY_PORTAL")
    item.canonical_url = "https://microsoft.com.attacker.example/login"
    assert not is_authoritative_registry_or_filing(item)


def test_current_role_cannot_be_proved_by_someone_elses_appointment():
    item = evidence("Jordan Hill is chief executive officer of Example. Morgan Lane stepped down as CEO in 2024.")
    assert relation("Morgan Lane is the current chief executive officer of Example.", "Example", item)[0] != "SUPPORT"


def test_identifier_year_is_not_a_financial_reporting_period():
    item = evidence("Base Score: 10.0 CRITICAL.")
    item.canonical_url = "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    assert relation("NIST rated CVE-2021-44228 a CVSS score of 2.1.", "NIST", item)[0] == "CONTRADICT"


def test_missing_quotation_cannot_be_supported_by_a_related_announcement():
    item = evidence("Example announced its acquisition of Widget Corporation in September 2023.")
    assert relation('Example said "the Earth is flat" in its Widget acquisition announcement.', "Example", item)[0] == "NONE"


def test_supported_first_premise_does_not_establish_unobserved_second_premise():
    item = evidence("Example announced Widget 15 in September 2023.")
    assert relation("Example announced Widget 15 in September 2023 and it has a physical keyboard.", "Example", item)[0] == "NONE"


def test_other_identifier_is_not_a_refutation_of_the_requested_record():
    item = evidence("NIST rated CVE-2025-10001 a CVSS score of 9.8.")
    item.canonical_url = "https://nvd.nist.gov/vuln/detail/CVE-2025-10001"
    assert relation("NIST rated CVE-2025-10002 a CVSS score of 9.8.", "NIST", item)[0] == "NONE"


def test_flattened_bibliographic_authors_are_not_part_of_the_title():
    item = evidence("arXiv:1706.03762 Title: Attention Is All You Need Authors: A. Researcher, B. Scientist Abstract: A research abstract.")
    item.canonical_url = "https://arxiv.org/abs/1706.03762"
    assert relation("The title of arXiv paper 1706.03762 is Attention Is All You Need.", "arXiv", item)[0] == "SUPPORT"
    assert relation("The title of arXiv paper 1706.03762 is Recurrence Is All You Need.", "arXiv", item)[0] == "CONTRADICT"


def test_related_wire_mentions_do_not_prove_independent_investigations():
    item = evidence("Republished articles carry identical Example shipment reporting. They represent syndicated distribution of a single report.")
    claim = "Identical republished articles about Example shipments prove separate independent investigations."
    assert relation(claim, "Example", item)[0] == "CONTRADICT"
