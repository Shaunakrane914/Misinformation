"""Offline controls for expanded collection, not live provider acceptance."""
from dataclasses import FrozenInstanceError, replace
import base64
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from backend.services.agent_reach.channels import EvidenceFragment, QueryExecutionRecord, RetrievalResult
from backend.services.research.harvesting import (
    HarvestingEngine, _BudgetedService, acquisition_reason, diversified_queries, raw_source_type,
)
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.research_profiles import DEEP, QUICK, STANDARD, get_research_profile


def item(url, title="Acme quarterly earnings results", **kwargs):
    return EvidenceItem(id="id_" + str(abs(hash(url))), canonical_url=url, title=title, channel="web", **kwargs)


def body(title="Acme quarterly earnings results", links=(), scope="article", kind="ARTICLE_BODY"):
    return {"status": "success", "markdown": ("Acme reported quarterly earnings and revenue in its public release. " * 35),
            "page_metadata": {"title": title, "content_scope": scope,
                              "body_quality": {"body_kind": kind}, "observed_links": list(links)}}


class SavedService:
    """Explicit synthetic fixtures. No network or generation in this suite."""
    def __init__(self, leads=(), pages=None):
        self.leads = list(leads)
        self.pages = pages or {}
        self.queries = []
        self.reads = []

    def retrieve_many(self, plan, **kwargs):
        records = []
        self.queries.extend(plan.items())
        for channel, rows in plan.items():
            for row in rows:
                records.append(QueryExecutionRecord(query_id=row["query_id"], channel=channel,
                    query_text=row["query_text"], query_class=row.get("query_class", "general"),
                    status="SUCCESS" if self.leads else "NO_RESULTS"))
        return RetrievalResult(query="Acme", domain="financial", fragments=self.leads,
                               query_records=records, channel_health={"web": "AVAILABLE"})

    def read(self, url, max_chars=12_000):
        self.reads.append(url)
        return self.pages.get(url, {"status": "failed", "error": "HTTP 403", "status_code": 403})


def profile(**kwargs):
    return replace(QUICK, max_queries=3, host_spacing_seconds=0, **kwargs)


def test_profiles_are_immutable_and_have_substantial_deep_capacity():
    assert (DEEP.max_candidates, DEEP.max_reads, DEEP.timeout_seconds) == (100, 24, 240)
    assert QUICK.max_reads < STANDARD.max_reads < DEEP.max_reads
    with pytest.raises(FrozenInstanceError):
        DEEP.max_reads = 1000
    with pytest.raises(ValueError):
        replace(DEEP, max_reads=26)
    with pytest.raises(ValueError):
        replace(DEEP, max_host_reads=9)
    with pytest.raises(ValueError):
        replace(DEEP, discovery_seconds=200)
    smaller = get_research_profile("DEEP", timeout_seconds=40, max_reads=2)
    assert smaller.timeout_seconds == 40 and smaller.max_reads == 2
    with pytest.raises(ValueError):
        get_research_profile("UNLIMITED")


@pytest.mark.parametrize("domain,target,required", [
    ("financial", "Medtronic", "earnings"), ("brand", "Patagonia", "counterfeit"),
    ("personal", "Jensen Huang", "statement"), ("trending", "ocean carbon removal", "developments"),
])
def test_queries_diversify_actual_agent_objectives(domain, target, required):
    rows = diversified_queries(target, domain)
    assert len(rows) == 18
    assert {r["channel"] for r in rows} == {"news", "web", "rss"}
    assert all(target in row["query_text"] and "http" not in row["query_text"] for row in rows)
    assert any(required in row["query_text"] for row in rows)


def test_acquisition_does_not_require_date_or_claim_support():
    lead = item("https://publisher.test/reports/acme-earnings", published_at="", relevance_score=0)
    assert acquisition_reason(lead, "Acme", "financial") is None
    assert acquisition_reason(item("https://publisher.test/story", title="Pichai"), "Sundar Pichai", "personal")
    assert acquisition_reason(item("https://publisher.test/story", title="Unilever news"), "EV", "trending")
    assert acquisition_reason(item("https://publisher.test/story", title="Removal of carbon from the ocean"), "ocean carbon removal", "trending") is None
    assert acquisition_reason(item("https://publisher.test/picture.jpg"), "Acme") == "NON_DOCUMENT_ASSET"
    assert acquisition_reason(item("https://user:secret@publisher.test/story"), "Acme") == "INVALID_OR_CREDENTIAL_URL"


def test_real_native_reader_collects_bodies_before_strict_filtering():
    leads = [EvidenceFragment(platform="web", title=f"Acme quarterly results {i}", url=f"https://p{i}.test/acme-results") for i in range(6)]
    service = SavedService(leads, {lead.url: body(lead.title) for lead in leads})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile())
    assert len(result.captures) == 6
    assert result.metrics["article_bodies"] == 6
    assert result.metrics["raw_article_words"] > 1000
    assert result.metrics["qualification_status"] == "PENDING_SECOND_LAYER"
    assert all(i.metadata["qualification_status"] == "PENDING" and i.content for i in result.captures)
    assert result.metrics["provider_http_request_count"] is None
    assert result.metrics["observed_publisher_hosts"] == 6
    assert len(result.query_records) == 3


def test_homepage_and_snippet_are_not_article_bodies():
    lead = EvidenceFragment(platform="web", title="Acme", url="https://publisher.test/", content="Search snippet only")
    service = SavedService([lead], {lead.url: body(scope="body", kind="UNCLASSIFIED_PAGE")})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile())
    assert len(result.captures) == 1
    assert result.metrics["article_bodies"] == 0
    assert raw_source_type(result.captures[0]) == "PUBLISHER_HOMEPAGE"
    assert result.captures[0].content != "Search snippet only"


def test_observed_hub_feed_article_chain_preserves_read_cap():
    root = EvidenceFragment(platform="web", title="Acme investor newsroom", url="https://publisher.test/newsroom")
    feed = "https://publisher.test/feed.xml"
    article = "https://publisher.test/2026/acme-quarterly-results"
    service = SavedService([root], {
        root.url: body(scope="NEWS_INDEX", kind="UNCLASSIFIED_PAGE", links=[{"url": feed, "text": "Published feed", "kind": "FEED_INDEX"}]),
        feed: body(scope="FEED_INDEX", kind="UNCLASSIFIED_PAGE", links=[{"url": article, "text": "Acme quarterly results", "published": "2026-10-01"}]),
        article: body(),
    })
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile())
    assert service.reads == [root.url, feed, article]
    assert result.metrics["reads_attempted"] == 3
    assert result.metrics["article_bodies"] == 1
    assert result.captures[-1].published_at == "2026-10-01"
    assert result.captures[-1].metadata["observed_parent_id"]


def test_blocked_article_does_not_stop_other_publisher_or_become_body():
    leads = [EvidenceFragment(platform="web", title="Acme quarterly results", url=f"https://p{i}.test/acme") for i in range(2)]
    service = SavedService(leads, {leads[1].url: body()})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile())
    assert result.metrics["reads_attempted"] == 2
    assert result.metrics["article_bodies"] == 1
    assert result.metrics["failure_categories"] == {"HTTP_FAILURE": 1}


def test_url_duplicates_and_unrelated_leads_do_not_consume_reads():
    leads = [EvidenceFragment(platform="web", title="Acme quarterly results", url="https://p.test/acme#x"),
             EvidenceFragment(platform="news", title="Acme quarterly results", url="https://p.test/acme#y"),
             EvidenceFragment(platform="web", title="Completely unrelated football", url="https://q.test/sports")]
    service = SavedService(leads, {leads[0].url: body()})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile())
    assert result.metrics["reads_attempted"] == 1
    assert result.metrics["discarded_by_reason"]["DUPLICATE_URL"] == 1
    assert result.metrics["discarded_by_reason"]["SUBJECT_NOT_OBSERVED_IN_LEAD"] == 1


def test_expired_deadline_never_contacts_service():
    service = SavedService()
    result = HarvestingEngine(service).run("Acme", profile=profile(), deadline=time.monotonic() - 1)
    assert not service.reads and not service.queries
    assert result.metrics["reads_attempted"] == 0 and result.metrics["deadline_exhausted"]


def test_operation_and_host_caps_are_shared_by_concurrent_reads():
    service = SavedService(pages={"https://p.test/acme": body()})
    bounded = _BudgetedService(service, profile(max_operations=3, max_host_reads=1), time.monotonic() + 3)
    assert bounded.read("https://p.test/acme")["status"] == "success"
    assert bounded.read("https://p.test/again")["error"] == "HOST_READ_BUDGET_EXHAUSTED"
    assert len(service.reads) == 1
    bounded.close()
    with pytest.raises(TimeoutError):
        bounded.read("https://q.test/late")


def test_same_host_requests_never_overlap():
    class Slow(SavedService):
        active = 0
        peak = 0
        lock = threading.Lock()

        def read(self, url, max_chars=12_000):
            with self.lock:
                self.active += 1
                self.peak = max(self.peak, self.active)
            time.sleep(0.01)
            with self.lock:
                self.active -= 1
            return body()
    service = Slow()
    bounded = _BudgetedService(service, profile(), time.monotonic() + 2)
    threads = [threading.Thread(target=bounded.read, args=(f"https://p.test/{i}",)) for i in range(3)]
    for worker in threads:
        worker.start()
    for worker in threads:
        worker.join()
    assert service.peak == 1 and bounded.actual_read_starts == 3


def test_advice_uses_existing_optional_helper_and_same_service_budget(monkeypatch):
    observed = []
    def advice(request, candidates, service, timeout):
        observed.append((request.target, service, timeout))
        return None, {"status": "DISABLED", "advisory_only": True}
    monkeypatch.setattr("backend.services.research.search_advice.expand_with_advice", advice)
    result = HarvestingEngine(SavedService()).run("Acme", profile=profile(),
        request=ResearchRequest(target="Acme", domain="financial"))
    assert len(observed) == 1
    assert result.metrics["ai_search_advice"]["status"] == "DISABLED"


def test_wrapper_limit_reserves_native_article_opportunities():
    leads = [item(f"https://news.google.com/articles/{i}", metadata={"publisher_source_url": f"https://p{i}.test"}) for i in range(5)]
    leads.append(item("https://direct.test/acme"))
    class Reader:
        def deep_read(self, selected, **kwargs):
            rows = [{"candidate_id": i.id, "url": i.canonical_url, "status": "FAILED",
                     "failure_kind": "PUBLISHER_UNRESOLVED" if "google.com" in i.canonical_url else "HTTP_FAILURE"} for i in selected]
            return [], {"attempted": len(selected), "failed": len(selected), "acquisition_attempts": rows}
    result = HarvestingEngine(SavedService(), Reader()).run("Acme", "financial", profile=profile(), initial_candidates=leads)
    attempts = result.read_telemetry["acquisition_attempts"]
    assert sum("google.com" in row["url"] for row in attempts) == 1
    assert any("direct.test" in row["url"] for row in attempts)


def test_full_discovery_pool_reserves_capacity_for_observed_article_links():
    hub = "https://p.test/newsroom"
    article = "https://p.test/acme-results"
    leads = [EvidenceFragment(platform="web", title="Acme news", url=hub)]
    leads += [EvidenceFragment(platform="web", title=f"Acme results {i}", url=f"https://p{i}.test/acme") for i in range(30)]
    service = SavedService(leads, {hub: body(scope="NEWS_INDEX", kind="UNCLASSIFIED_PAGE",
        links=[{"url": article, "text": "Acme quarterly results"}]), article: body()})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile(max_candidates=10))
    assert len(result.candidates) <= 10
    assert article in service.reads
    assert result.metrics["article_bodies"] == 1
    assert result.metrics["discarded_by_reason"]["DISCOVERY_RESERVED_CONTINUATION_CAP"]


def test_transport_exception_records_each_query_instead_of_empty_success():
    class Failed(SavedService):
        def retrieve_many(self, plan, **kwargs):
            raise TimeoutError("synthetic offline timeout")
    result = HarvestingEngine(Failed()).run("Acme", "financial", profile=profile())
    assert len(result.query_records) == 3
    assert all(row.status == "TIMEOUT" for row in result.query_records)
    assert result.metrics["article_bodies"] == 0


def test_observed_bing_news_redirects_have_distinct_identity_and_real_publisher_reads():
    publisher_urls = ["https://one.test/acme/results?report=q1", "https://two.test/acme/results?report=q2"]
    leads = [EvidenceFragment(platform="web", title="Acme quarterly results", url=
        "https://www.bing.com/news/apiclick.aspx?" + urlencode({"url": url, "tid": "observed"})) for url in publisher_urls]
    assert leads[0].evidence_id == leads[1].evidence_id  # actual legacy failure control
    service = SavedService(leads, {url: body() for url in publisher_urls})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile())
    assert set(service.reads) == set(publisher_urls)
    assert len({capture.id for capture in result.captures}) == 2
    assert len({capture.discovered_id for capture in result.captures}) == 2
    assert all(capture.discovered_id == "cand_disc_" + capture.id for capture in result.captures)
    assert result.metrics["observed_publisher_hosts"] == 2
    assert all(i.metadata["upstream_id_ambiguous"] for i in result.candidates)
    assert all(i.metadata["upstream_ids_are_citation_aliases"] is False for i in result.candidates)
    assert all("bing.com/news/apiclick.aspx" in i.metadata["observed_discovery_url"] for i in result.candidates)


def test_bing_decoder_preserves_ordinary_uri_semantics_and_known_envelope_only():
    from backend.services.agent_reach.native.source_discovery import resolve_bing_redirect
    target = "https://publisher.test/a%2Fb?q=x%26y#fragment"
    assert resolve_bing_redirect(target) == target
    wrapper = "https://www.bing.com/news/apiclick.aspx?" + urlencode({"url": target})
    assert resolve_bing_redirect(wrapper) == target
    base = base64.urlsafe_b64encode(target.encode()).decode().rstrip("=")
    assert resolve_bing_redirect("https://bing.com/ck/a?u=a1" + base) == target
    for invalid in ("javascript:alert(1)", "https://name:secret@publisher.test/story", "//publisher.test/story",
                    "https://publisher.test/a\x00b"):
        url = "https://www.bing.com/news/apiclick.aspx?" + urlencode({"url": invalid})
        assert resolve_bing_redirect(url) == url
    for wrong_host in ("bing.com.attacker.test", "notbing.com"):
        url = f"https://{wrong_host}/news/apiclick.aspx?" + urlencode({"url": target})
        assert resolve_bing_redirect(url) == url
    duplicate = "https://www.bing.com/news/apiclick.aspx?" + urlencode({"url": [target, "https://other.test"]}, doseq=True)
    assert resolve_bing_redirect(duplicate) == duplicate
    bad_base64 = "https://bing.com/ck/a?u=a1!"
    assert resolve_bing_redirect(bad_base64) == bad_base64


def test_unsubmitted_queries_have_explicit_lifecycle_records():
    service = SavedService()
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile(), deadline=time.monotonic() - 1)
    assert len(result.query_records) == 3
    assert all(row.status == "NOT_SUBMITTED" and row.provider_started is False for row in result.query_records)
    assert all(row.error == "DISCOVERY_DEADLINE_EXHAUSTED" for row in result.query_records)
    assert not service.queries


def test_fresh_trending_leads_rank_first_without_accepting_claims():
    leads = [EvidenceFragment(platform="web", title="Acme storage research", url="https://old.test/acme", published="6 days ago"),
             EvidenceFragment(platform="web", title="Acme storage research", url="https://fresh.test/acme", published="1 hour ago")]
    service = SavedService(leads, {lead.url: body(lead.title) for lead in leads})
    result = HarvestingEngine(service).run("Acme storage", "trending", profile=profile(max_reads=1))
    assert service.reads == [leads[1].url]
    assert all(item.metadata["harvest_acquisition_eligible"] for item in result.candidates)
    assert result.captures[0].metadata["qualification_status"] == "PENDING"
    queries = diversified_queries("Acme storage", "trending", "investigate recent discourse")
    assert all("when:2d" in row["query_text"] for row in queries if row["channel"] in {"rss", "news"})


def test_explicit_user_source_is_read_but_never_claimed_as_autonomous_discovery():
    url = "https://publisher.test/a-report"
    service = SavedService(pages={url: body()})
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile(), source_url=url)
    assert service.reads == [url]
    assert result.metrics["article_bodies"] == 1
    assert result.metrics["autonomously_discovered_article_bodies"] == 0
    assert result.captures[0].metadata["source_kind"] == "USER_SUPPLIED_SOURCE"
    assert result.captures[0].metadata["qualification_status"] == "PENDING"
    invalid = HarvestingEngine(SavedService()).run("Acme", profile=profile(), source_url="https://user:secret@publisher.test/a")
    assert invalid.metrics["reads_attempted"] == 0


def test_only_registered_explicit_extra_channels_replace_tail_of_bounded_plan():
    service = SavedService()
    service.registry = SimpleNamespace(channel_names={"web", "news", "rss", "github", "arxiv", "youtube"})
    plan = [{"channel": channel, "query_text": "Acme research", "query_class": "caller_validated"}
            for channel in ("github", "arxiv", "youtube", "unknown_unregistered")]
    result = HarvestingEngine(service).run("Acme", "financial", profile=profile(), query_plan=plan)
    assert result.metrics["queries_generated"] == 3
    assert set(result.channel_queries) == {"news", "github", "arxiv"}
    assert not any(channel in {"youtube", "unknown_unregistered"} for channel, _ in service.queries)
