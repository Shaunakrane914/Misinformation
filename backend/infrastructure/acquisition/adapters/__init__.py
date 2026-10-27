"""
Aegis Protocol — Acquisition Platform Adapters
================================================
Platform-specific adapters for evidence acquisition across Web, Social, Financial,
Academic, Governance, Regulatory, and Encyclopedic platforms.
"""

def __getattr__(name: str):
    if name == "PlatformAdapter":
        from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
        return PlatformAdapter
    if name == "WikipediaAdapter":
        from backend.infrastructure.acquisition.adapters.encyclopedia.wikipedia import WikipediaAdapter
        return WikipediaAdapter
    if name == "SecFilingsFullAdapter":
        from backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full import SecFilingsFullAdapter
        return SecFilingsFullAdapter
    if name == "ArxivAdapter":
        from backend.infrastructure.acquisition.adapters.academic.arxiv import ArxivAdapter
        return ArxivAdapter
    if name == "SubstackAdapter":
        from backend.infrastructure.acquisition.adapters.news.substack import SubstackAdapter
        return SubstackAdapter
    if name == "YahooFinanceAdapter":
        from backend.infrastructure.acquisition.adapters.financial.yahoo_finance import YahooFinanceAdapter
        return YahooFinanceAdapter
    if name == "ConsumerReviewAdapter":
        from backend.infrastructure.acquisition.adapters.consumer.trustpilot import ConsumerReviewAdapter
        return ConsumerReviewAdapter
    if name == "RedditDeepAdapter":
        from backend.infrastructure.acquisition.adapters.social.reddit_deep import RedditDeepAdapter
        return RedditDeepAdapter
    if name == "WikidataExecutiveAdapter":
        from backend.infrastructure.acquisition.adapters.governance.wikidata_exec import WikidataExecutiveAdapter
        return WikidataExecutiveAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ArxivAdapter",
    "ConsumerReviewAdapter",
    "PlatformAdapter",
    "RedditDeepAdapter",
    "SecFilingsFullAdapter",
    "SubstackAdapter",
    "WikidataExecutiveAdapter",
    "WikipediaAdapter",
    "YahooFinanceAdapter",
]
