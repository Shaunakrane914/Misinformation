"""Offline controls for acquisition usefulness, never a live recall assertion."""
import pytest

from backend.services.research.passage_records import public_statement_attribution
from backend.services.research.publisher_links import observed_publisher_articles
from backend.services.research.research_models import EvidenceItem


def article(body, objective="PUBLIC_STATEMENT"):
    return EvidenceItem(id="captured", canonical_url="https://publisher.example/article", title="Interview",
        content=body, content_depth="DEEP_READ", acquired_id="native-capture",
        metadata={"read_success": True, "acquisition_objective": objective,
                  "page_metadata": {"body_kind": "ARTICLE_BODY"}})


@pytest.mark.parametrize("intent", [
    "Research public statements and identity threats, including impersonation and synthetic media allegations",
    "Elena Rivera identity threat",
])
def test_default_interview_queries_keep_matching_routing_objective(intent):
    from backend.services.research.harvesting import diversified_queries
    queries = diversified_queries("Elena Rivera", "personal", intent=intent)
    statement_queries = [row for row in queries if row["query_text"] == '"Elena Rivera" interview']
    assert {row["channel"] for row in statement_queries} == {"news", "web", "rss"}
    assert all(row["acquisition_objective"] == "PUBLIC_STATEMENT" for row in statement_queries)
    paragraph = '"We will publish the complete audited figures next month," Rivera, who joined the council in 2017, said in a statement.'
    body = "Chief Executive Elena Rivera addressed the Council\n\n" + paragraph
    # Either transport can complete first; neither may change the meaning of
    # identical captured bytes. This remains source attribution, not identity.
    for row in statement_queries:
        assert public_statement_attribution(article(body, row["acquisition_objective"]), paragraph, "Elena Rivera") == "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"


def test_replaced_query_and_explicit_task_keep_their_own_objectives():
    from backend.services.research.harvesting import diversified_queries
    explicit = diversified_queries("Elena Rivera", "personal", intent="identity impersonation allegation")
    assert explicit[0]["query_text"] == "Elena Rivera identity impersonation allegation"
    assert explicit[0]["acquisition_objective"] == "IDENTITY_THREAT"
    tasks = diversified_queries("Elena Rivera", "personal", intent="public statement",
                                specialist_tasks=("IMPERSONATION",))
    assert all(row["acquisition_objective"] == "IDENTITY_THREAT" for row in tasks)
    assert all("impersonation" in row["query_text"] or "fake account" in row["query_text"] for row in tasks)


@pytest.mark.parametrize("attribution", [
    "Rivera said", "said Rivera", "Rivera, who joined the council in 2017, said",
])
def test_observed_unambiguous_surname_with_job_title_and_relative_clause(attribution):
    paragraph = '"We will publish the complete audited figures next month," ' + attribution + ' in a statement. The proposal still requires board approval.'
    body = "Chief Executive Elena Rivera addressed the Council\n\nAdvt\n\n" + paragraph
    assert public_statement_attribution(article(body), paragraph, "Elena Rivera") == "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"


def test_saved_mary_article_keeps_reported_quote_from_incidental_discovery():
    import json
    import hashlib
    from pathlib import Path
    from backend.services.research.passage_extractor import PassageExtractor
    source=json.loads((Path(__file__).parent/'fixtures/oct28_mary_reported_statement_capture.json').read_text(encoding='utf-8'))
    body=source['readable_text']
    assert hashlib.sha256(body.encode()).hexdigest()==source['raw_content_hash']
    item=article(body, objective='IDENTITY_THREAT')
    PassageExtractor().extract_passages([item], 'Mary Barra', domain='personal')
    assert item.extraction_status=='SUCCESS' and item.relevant_excerpt
    assert public_statement_attribution(item,item.relevant_excerpt,'Mary Barra')=='REPORTED_QUOTATION_SURNAME_IN_CAPTURE'
    assert item.metadata['evidence_passages'] and item.content==body
    item.content += '\n\nJessica Barra also commented on the announcement.'
    assert public_statement_attribution(item,item.relevant_excerpt,'Mary Barra') is None
    item.content=body
    item.metadata['page_metadata']['body_kind']='NEWS_INDEX'
    assert public_statement_attribution(item,item.relevant_excerpt,'Mary Barra') is None


@pytest.mark.parametrize("prefix,objective,paragraph", [
    ("Elena Rivera and Jessica Rivera attended.", "PUBLIC_STATEMENT", '"We will publish complete figures next month," Rivera said.'),
    ("Chief Executive Elena Rivera and Jessica Rivera attended.", "IDENTITY_THREAT", '"We will publish complete figures next month," Rivera said.'),
    ("Chief Executive Elena Rivera attended.", "PUBLIC_STATEMENT", 'The fake quote falsely attributed to Rivera said "We will publish complete figures next month."'),
    ("No full name was captured.", "PUBLIC_STATEMENT", '"We will publish complete figures next month," Rivera said.'),
])
def test_surname_does_not_attribute_disputed_ambiguous_or_unintroduced_quotes(prefix, objective, paragraph):
    assert public_statement_attribution(article(prefix + "\n\n" + paragraph, objective), paragraph, "Elena Rivera") is None


def test_surname_or_full_name_does_not_borrow_someone_elses_quote():
    for speaker in ("Rivera", "Elena Rivera"):
        paragraph = speaker + ' said the board remains cautious. "We intend to restate all figures," said finance chief Amy Chen.'
        assert public_statement_attribution(article("Elena Rivera attended.\n\n" + paragraph), paragraph, "Elena Rivera") is None


def test_same_middle_name_is_not_identity_equivalence():
    paragraph = '"We will release the complete figures next month," Rivera said.'
    body = "Elena Marie Rivera and Jessica Marie Rivera attended.\n\n" + paragraph
    assert public_statement_attribution(article(body), paragraph, "Elena Marie Rivera") is None


def test_accented_competing_given_name_and_name_suffix_are_not_identity():
    paragraph = '"We will release the complete figures next month," Rivera said.'
    assert public_statement_attribution(article("Elena Rivera and José Rivera attended.\n\n" + paragraph), paragraph, "Elena Rivera") is None
    paragraph = 'John Michael Smith said "We intend to restate all figures."'
    assert public_statement_attribution(article(paragraph), paragraph, "Michael Smith") is None


def parent(links):
    return EvidenceItem(id="hub", canonical_url="https://publisher.example/news", title="Observed news hub",
        content="Observed publisher index", acquired_id="capture", metadata={"read_success": True,
        "page_metadata": {"observed_links": links}})


def test_topic_continuations_do_not_spend_reads_on_one_word_or_generic_events():
    hub = parent([
        {"url": "https://publisher.example/battery-storage", "text": "Battery storage prices announced"},
        {"url": "https://publisher.example/recycling-batteries", "text": "Recycling of batteries proposed"},
        {"url": "https://publisher.example/football", "text": "Local match announced"},
        {"url": "https://publisher.example/rss", "text": "Observed feed", "kind": "FEED_INDEX"},
    ])
    audit = []
    children = observed_publisher_articles(hub, "trending", audit, "battery recycling", max_children=10)
    assert {x.canonical_url for x in children} == {
        "https://publisher.example/recycling-batteries", "https://publisher.example/rss"}
    assert any(x.get("discard_reason") == "OFF_SUBJECT_CONTINUATION" for x in audit)


def test_personal_continuations_require_the_subject_not_just_interview_keywords():
    hub = parent([
        {"url": "https://publisher.example/elena-rivera-interview", "text": "Elena Rivera interview"},
        {"url": "https://publisher.example/jessica-rivera-interview", "text": "Jessica Rivera interview"},
        {"url": "https://publisher.example/elena-adams-statement", "text": "Elena Adams statement"},
    ])
    children = observed_publisher_articles(hub, "personal", [], "Elena Rivera", max_children=10)
    assert [x.canonical_url for x in children] == ["https://publisher.example/elena-rivera-interview"]


def test_observed_issuer_host_can_keep_unnamed_financial_document_lead():
    hub = parent([])
    hub.canonical_url = "https://quartztools.example/investors"
    hub.metadata["page_metadata"]["observed_links"] = [
        {"url": "https://quartztools.example/reports/report.pdf", "text": "Annual report"}]
    result = observed_publisher_articles(hub, "financial", [], "Quartz Tools")
    assert len(result) == 1 and result[0].content_depth == "INDEX_SNIPPET"


def test_engine_does_not_re_admit_helper_rejections():
    from backend.services.research.harvesting import HarvestingEngine
    hub = parent([{"url": "https://publisher.example/battery-storage", "text": "Battery storage announced"},
                  {"url": "https://publisher.example/batteries-recycling", "text": "Recycling batteries"}])
    audit = []
    result = HarvestingEngine._observed_children(hub, "battery recycling", "trending", audit)
    assert [x.canonical_url for x in result] == ["https://publisher.example/batteries-recycling"]
    assert any(x.get("discard_reason") == "OFF_SUBJECT_CONTINUATION" for x in audit)


def test_acquired_article_can_follow_observed_citation_but_does_not_inherit_ownership():
    from backend.services.research.harvesting import HarvestingEngine
    item = article("Quartz Tools reported audited financial figures in the linked statement.")
    item.source_name = "Example News"
    item.metadata["requested_specialist_tasks"] = ["PUBLIC_STATEMENT"]
    item.metadata["page_metadata"]["observed_links"] = [
        {"url": "https://quartztools.example/release", "text": "Press release"},
        {"url": "https://other.example/unknown", "text": "Unrelated source report"},
        {"url": "http://127.0.0.1/report", "text": "Quartz Tools financial report"},
    ]
    children = HarvestingEngine._observed_children(item, "Quartz Tools", "financial", [])
    assert len(children) == 1
    child = children[0]
    assert child.canonical_url == "https://quartztools.example/release"
    assert child.metadata["source_citation"] is True and child.metadata["observed_parent_id"] == item.id
    assert child.metadata["requested_specialist_tasks"] == ["PUBLIC_STATEMENT"]
    assert not child.content and not child.primary_source and not child.official_source and not child.source_name


def test_article_citation_count_and_depth_stay_bounded():
    from backend.services.research.harvesting import HarvestingEngine
    item = article("Quartz Tools financial results were reported in the captured article.")
    item.metadata["page_metadata"]["observed_links"] = [
        {"url": "https://issuer.example/quartz-tools-report-" + str(i), "text": "Quartz Tools source report"}
        for i in range(20)]
    children = HarvestingEngine._observed_children(item, "Quartz Tools", "financial", [])
    assert len(children) == 4
    child = children[0]
    child.metadata.update(read_success=True, page_metadata=item.metadata["page_metadata"])
    assert not HarvestingEngine._observed_children(child, "Quartz Tools", "financial", [])


def test_hub_continuation_does_not_exceed_24_children():
    from backend.services.research.harvesting import HarvestingEngine
    hub = parent([{"url": "https://publisher.example/quartz-tools-" + str(i),
                   "text": "Quartz Tools reported results " + str(i)} for i in range(40)])
    assert len(HarvestingEngine._observed_children(hub, "Quartz Tools", "financial", [])) == 24


def test_document_index_navigation_and_cited_hub_keep_their_boundaries():
    from backend.services.research.harvesting import HarvestingEngine
    hub = parent([{ "url": "https://publisher.example/quartz-report.pdf", "text": "Quartz Tools annual report"},
                  { "url": "https://publisher.example/quartz-quarter.pdf", "text": "Quartz Tools quarterly report"}])
    hub.canonical_url = "https://publisher.example/company/quartz-files"
    hub.metadata["content_role"] = "DOCUMENT_INDEX"
    assert len(HarvestingEngine._observed_children(hub, "Quartz Tools", "financial", [])) == 2
    hub.metadata["source_citation"] = True
    assert not HarvestingEngine._observed_children(hub, "Quartz Tools", "financial", [])
    item = article("Quartz Tools reported financial results.")
    item.metadata["page_metadata"]["discovery_links"] = [{"url": "https://quartztools.example/results", "text": "Financial results"}]
    assert not HarvestingEngine._observed_children(item, "Quartz Tools", "financial", [])


def test_article_citation_reaches_actual_read_within_original_budget():
    from dataclasses import replace
    from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import QUICK
    class SavedService:
        def __init__(self):
            self.reads = []
        def retrieve_many(self, *args, **kwargs):
            return RetrievalResult(query="Quartz Tools", domain="financial", fragments=[EvidenceFragment(
                platform="web", url="https://publisher.example/quartz-tools-results",
                title="Quartz Tools reported financial results", content_depth="INDEX_SNIPPET")])
        def read(self, url, max_chars):
            self.reads.append(url)
            page = {"body_kind": "ARTICLE_BODY", "content_scope": "article"}
            if url == "https://publisher.example/quartz-tools-results":
                page["observed_links"] = [{"url": "https://quartztools.example/release", "text": "Press release"}]
            return {"status": "success", "title": "Quartz Tools financial statement",
                "content": "Quartz Tools reported annual revenue of USD 40 million in the captured financial statement. The reported figures have not been independently audited.",
                "page_metadata": page}
    service = SavedService()
    profile = replace(QUICK, max_queries=1, max_reads=2, concurrency=1, max_candidates=8, host_spacing_seconds=0)
    result = HarvestingEngine(service).run("Quartz Tools", "financial", profile=profile,
        query_plan=[{"channel": "web", "query_text": "Quartz Tools financial results"}])
    assert service.reads == ["https://publisher.example/quartz-tools-results", "https://quartztools.example/release"]
    assert result.read_telemetry["attempted"] == 2
    assert any(item.content and item.canonical_url == "https://quartztools.example/release" for item in result.captures)


def test_family_search_matches_existing_task_without_enlarging_budget():
    from backend.services.research.source_diversity import diversify_search_plan
    rows = [{"channel": "web", "query_text": "Quartz Tools " + query, "specialist_task": task}
        for query, task in [("counterfeit", "COUNTERFEIT"), ("impersonation", "IMPERSONATION"),
                             ("phishing complaints", "PHISHING"), ("product safety recall", "PRODUCT_SAFETY")]]
    result = diversify_search_plan(rows * 3, "Quartz Tools", "brand", 12)
    hints = {row["source_family"]: row for row in result if row.get("source_family")}
    assert len(result) <= 12
    assert hints["consumer_safety"]["specialist_task"] == "PRODUCT_SAFETY"
    assert hints["enforcement_reports"]["specialist_task"] == "COUNTERFEIT"
    assert hints["consumer_protection"]["specialist_task"] == "PHISHING"


def test_family_hints_preserve_explicit_false_quote_task_and_literal_quote():
    from backend.services.research.source_diversity import diversify_search_plan
    query = 'Elena Rivera did not say "audited figures are complete"'
    rows = [{"channel": "web", "query_text": query, "specialist_task": "FALSE_QUOTE"}]
    result = diversify_search_plan(rows, "Elena Rivera", "personal", 12)
    assert all(row["query_text"].startswith(query) and row["specialist_task"] == "FALSE_QUOTE" for row in result)


def test_adjacent_financial_context_preserves_bytes_without_changing_winner():
    from backend.services.research.passage_extractor import PassageExtractor
    anchor = "Quartz Tools reported annual revenue of USD 40 million, according to the company's captured financial statement. The reported figures have not been independently audited."
    context = "The company reported operating profit of USD 8 million for the same reporting period. Its statement says the comparison excludes discontinued operations."
    item = article(anchor + "\n\n" + context)
    item.title = "Quartz Tools annual financial results"
    item.metadata["layer2_eligible"] = True
    PassageExtractor().extract_passages([item], "Quartz Tools", domain="financial")
    assert item.relevant_excerpt == anchor
    passages = item.metadata["evidence_passages"]
    assert [x["text"] for x in passages] == [anchor, context]
    assert passages[1]["context_labels"]["subject_context"] == "HEURISTIC_ADJACENT_ISSUER_CONTEXT"
    assert all(item.content[x["start"]:x["end"]] == x["text"] for x in passages)


@pytest.mark.parametrize("separator,title", [
    ("Boreal Industries reported its own earnings for the year.", "Quartz Tools results"),
    ("Related stories", "Quartz Tools results"),
    ("", "Quartz Tools versus Boreal Industries earnings comparison"),
    ("", "Quartz Tools discusses Boreal Industries results"),
])
def test_financial_context_does_not_cross_subjects_headings_or_comparisons(separator, title):
    from backend.services.research.evidence_workbench import _adjacent_issuer_paragraphs
    body = "Quartz Tools reported annual revenue of USD 40 million for the reporting period."
    body += "\n\n" + (separator + "\n\n" if separator else "")
    body += "The company reported operating profit of USD 8 million in its financial statement."
    item = article(body)
    item.title = title
    assert not _adjacent_issuer_paragraphs(item, "Quartz Tools")


def test_issuer_mention_reporting_other_company_does_not_anchor_context():
    from backend.services.research.evidence_workbench import _adjacent_issuer_paragraphs
    item = article("Quartz Tools reported that Boreal Industries earned revenue of USD 40 million.\n\nThe company reported operating profit of USD 8 million in its statement.")
    item.title = "Quartz Tools results"
    assert not _adjacent_issuer_paragraphs(item, "Quartz Tools")
    item.content = "Quartz Tools reported annual revenue of USD 40 million. Boreal Industries reported revenue of USD 50 million.\n\nThe company reported operating profit of USD 8 million."
    assert not _adjacent_issuer_paragraphs(item, "Quartz Tools")


@pytest.mark.parametrize("body", [
    "Ce message propose une offre Quartz Tools pour les clients. Il s'agit d'une arnaque et cette page demande votre numéro de carte pour recevoir le produit.",
    "Este mensaje de Quartz Tools es una estafa para los clientes. La página solicita los datos de la tarjeta con una oferta que no pertenece a la empresa.",
])
def test_acquired_french_spanish_prose_can_be_inspected_without_translation(body):
    from backend.services.research.passage_extractor import PassageExtractor
    item = article(body)
    item.title = "Quartz Tools reported allegation"
    item.metadata["layer2_eligible"] = True
    PassageExtractor().extract_passages([item], "Quartz Tools", domain="brand")
    assert item.extraction_status == "SUCCESS" and item.relevant_excerpt == body
    assert item.metadata["evidence_passages"][0]["claim_status"] == "UNVERIFIED"


@pytest.mark.parametrize("body", [
    "Cuidado: este mensaje de Quartz Tools es una estafa para los clientes. La página solicita los datos de la tarjeta con una oferta que no pertenece a la empresa.",
    "Ne cliquez pas: cette offre Quartz Tools est une arnaque pour les clients. La page demande votre numéro de carte avec une fausse offre de produit.",
])
def test_native_language_warning_never_becomes_an_attacker(body):
    from backend.agents.brandshield.intelligence import classify_brand_source
    from backend.services.research.passage_records import classify_passage
    result = classify_brand_source({"evidence_id": "capture", "url": "https://publisher.example/article",
        "content": body, "content_depth": "PARTIAL_CONTENT"}, "Quartz Tools")
    assert classify_passage(body, domain="brand") == "SAFETY_WARNING"
    assert result["classification"] == "WARNING_ADVISORY" and result["actor_url"] is None


def test_source_url_and_word_list_are_not_foreign_prose():
    from backend.services.research.content_roles import local_prose_predicate
    assert not local_prose_predicate("https://maldita.es/example la los las con que para")


def test_brand_context_preserves_payment_mechanism_without_new_actor_claim():
    from backend.services.research.passage_extractor import PassageExtractor
    first = "Cuidado: este mensaje de Quartz Tools es una estafa para los clientes con una oferta que no pertenece a la empresa."
    second = "Esta página solicita los datos personales y los datos de la tarjeta para recibir una oferta que no pertenece a la empresa."
    item = article(first + "\n\n" + second)
    item.title = "Cuidado con esta oferta Quartz Tools"
    item.metadata["layer2_eligible"] = True
    PassageExtractor().extract_passages([item], "Quartz Tools", domain="brand")
    passages = item.metadata["evidence_passages"]
    assert [p["text"] for p in passages] == [first, second]
    assert passages[1]["context_labels"]["subject_context"] == "HEURISTIC_ADJACENT_BRAND_CONTEXT"
    assert all(p["claim_status"] == "UNVERIFIED" for p in passages)


@pytest.mark.parametrize("text", [
    "Quartz Tools no es una estafa para los clientes; la empresa ofrece los datos de la garantía.",
    "Quartz Tools n'est pas une arnaque pour les clients; cette page offre les détails de la garantie.",
    "Estas ofertas de Quartz Tools no son estafas para los clientes; la empresa ofrece los datos de la garantía.",
    "Ces messages Quartz Tools ne sont pas des arnaques pour les clients; cette page offre les détails de la garantie.",
    "Quartz Tools no se trata de una estafa para los clientes; la empresa ofrece los datos de la garantía.",
    "Quartz Tools ne constitue pas une arnaque pour les clients; cette page offre les détails de la garantie.",
])
def test_native_negations_are_not_positive_threats(text):
    from backend.agents.brandshield.intelligence import classify_brand_source
    from backend.services.research.passage_records import classify_passage
    assert classify_passage(text, domain="brand") == "DISPUTED_CLAIM"
    result = classify_brand_source({"content": text, "content_depth": "PARTIAL_CONTENT",
        "url": "https://publisher.example/article"}, "Quartz Tools")
    assert result["classification"] == "INSUFFICIENT_EVIDENCE" and result["actor_url"] is None
