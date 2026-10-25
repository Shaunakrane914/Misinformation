"""Unit tests for Personal Watch public statement planning and structural extraction."""
from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page, _semantic_root, _body_quality
from backend.services.agent_reach.source_planner import SourcePlanningEngine
from backend.services.research.content_roles import matches_objective


def test_personal_watch_objective_matches_statements_and_threats():
    assert matches_objective("Mary Barra announced the new automotive manufacturing initiative", "personal") is True
    assert matches_objective("General Motors CEO Mary Barra interview on electric vehicle strategy", "personal") is True
    assert matches_objective("Mary Barra speech at the economic summit remarks transcript", "personal") is True
    assert matches_objective("Deepfake video impersonating Mary Barra surfaces online", "personal") is True
    # Unrelated text
    assert matches_objective("10 best recipes for chocolate chip cookies", "personal") is False


def test_personal_watch_planning_separates_statements_from_threats():
    planner = SourcePlanningEngine()
    statement_plan = planner.plan(
        "Mary Barra public statement",
        entity="Mary Barra",
        domain="personal",
        agent="personal_watch",
    )
    categories = [a.source_category for a in statement_plan.actions]
    assert "public_statement_discovery" in categories
    # Public statement plan should not prioritize deepfake/impersonation at priority 0
    top_queries = [a.query for a in statement_plan.actions[:3]]
    assert any("speech" in q or "statement" in q or "remarks" in q for q in top_queries)
    assert not any("impersonation scam" in q for q in top_queries)

    # In contrast, an impersonation claim should prioritize identity threat
    threat_plan = planner.plan(
        "Mary Barra deepfake impersonation scam",
        entity="Mary Barra",
        domain="personal",
        agent="personal_watch",
    )
    threat_queries = [a.query for a in threat_plan.actions[:3]]
    assert any("impersonation scam" in q or "deepfake" in q for q in threat_queries)


def test_structural_extraction_regional_news_containers():
    # Economic Times style .artText container
    html = """
    <html>
      <body>
        <div class="wrapper">
          <div class="artText">
            <p>General Motors CEO Mary Barra addressed industry leaders on Tuesday regarding future clean energy transitions.</p>
            <p>Speaking at the automotive summit, Barra emphasized that supply chain partnerships remain vital to long-term manufacturing growth.</p>
            <p>The executive reiterated corporate commitments made earlier this fiscal quarter during investor briefings.</p>
          </div>
        </div>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    page = extract_readable_page(soup)
    assert page["content_scope"] == "publisher_article_container"
    assert page["body_quality"]["body_kind"] == "ARTICLE_BODY"
    assert "Mary Barra addressed" in page["text"]


def test_structural_extraction_jsonld_declared_article_fallback():
    # Page with declared NewsArticle in JSON-LD and substantive prose in fallback scope
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "headline": "CEO Remarks on Manufacturing Strategy",
          "datePublished": "2026-10-25T10:00:00Z"
        }
        </script>
      </head>
      <body>
        <div class="custom-layout-without-standard-article-tag">
          <p>Mary Barra confirmed that all major manufacturing targets for the current cycle are progressing according to plan.</p>
          <p>The company continues to expand operational footprint across domestic assembly facilities and technology research centers.</p>
        </div>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    page = extract_readable_page(soup)
    assert page["body_quality"]["body_kind"] == "ARTICLE_BODY"
    assert "Mary Barra confirmed" in page["text"]
