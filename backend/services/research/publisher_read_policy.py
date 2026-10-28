"""Per-investigation publisher read reservations; routing only, never evidence.

All counters are coordinator-owned. Reservations partition the existing host cap;
they do not authorize requests or replace the secured service's actual host cap.
"""
import re
from collections import Counter
from urllib.parse import urlsplit


def discovery_kind(item, is_index=False):
    path = urlsplit(item.canonical_url).path.casefold()
    title = (item.title or "").casefold()
    if ((re.search(r"(?:^|/)comments?(?:/|$)", path) and "feed" in path)
            or is_index and title.startswith(("comments for ", "comments on "))):
        return "COMMENT_FEED"
    if not is_index and item.metadata.get("discovery_kind") != "FEED_INDEX":
        return "ARTICLE"
    if re.search(r"(?:^|/)(?:feed|rss|atom)(?:/|\.|$)", path) or re.search(r"\.(?:rss|atom)$", path):
        return "MAIN_FEED"
    if "sitemap" in path:
        return "SITEMAP"
    if urlsplit(item.canonical_url).query or re.search(r"(?:^|/)search(?:/|$)", path):
        return "SEARCH"
    return "HUB"


class PublisherReadPolicy:
    def __init__(self, host_cap):
        self.host_cap = host_cap
        self.article_reserve = max(1, host_cap // 2)
        self.discovery_cap = max(0, host_cap - self.article_reserve)
        self.initial_discovery = min(2, self.discovery_cap)
        self.discovery = Counter()
        self.articles = Counter()
        self.unusable_articles = Counter()
        self.discovery_kinds = {}

    def reason(self, host, kind, has_articles, host_busy=False):
        if kind == "COMMENT_FEED":
            return "DEFERRED_COMMENT_FEED_FOR_ARTICLE_TASK"
        if kind == "ARTICLE":
            return None
        if self.discovery[host] >= self.discovery_cap:
            return "DISCOVERY_SHARE_RESERVED_FOR_ARTICLES"
        if self.discovery[host] >= self.initial_discovery and self.unusable_articles[host] < 2:
            if has_articles or host_busy:
                return "ADAPTIVE_DISCOVERY_WAITING_FOR_ARTICLE_FEEDBACK"
        return None

    def priority(self, host, kind, temporal_priority):
        # Discovery dates are hints only. Body qualification remains unchanged.
        if kind == "ARTICLE" and temporal_priority == 0:
            return 0
        if kind in {"MAIN_FEED", "SITEMAP", "SEARCH"}:
            return 1 if self.unusable_articles[host] >= 2 else 3
        if kind == "ARTICLE":
            return 2 if temporal_priority in {None, 1} else 5
        return 6  # homes/comments do not beat observed useful discovery paths

    def submit(self, host, kind):
        if kind == "ARTICLE":
            self.articles[host] += 1
        else:
            self.discovery[host] += 1
            self.discovery_kinds.setdefault(host, Counter())[kind] += 1

    def observe(self, host, feedback):
        if not feedback or feedback.get("source_type") not in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT"}:
            return
        reason = str(feedback.get("reason") or "")
        if feedback.get("usable_passage"):
            self.unusable_articles[host] = 0
        elif reason:
            self.unusable_articles[host] += 1

    def snapshot(self):
        hosts = set(self.discovery) | set(self.articles)
        return {"host_cap_unchanged": self.host_cap, "article_reserve": self.article_reserve,
                "initial_discovery": self.initial_discovery, "maximum_discovery": self.discovery_cap,
                "adaptive_reservation": max(0, self.discovery_cap - self.initial_discovery),
                "hosts": {host: {"discovery_reads": self.discovery[host], "article_reads": self.articles[host],
                    "consecutive_unusable_articles": self.unusable_articles[host],
                    "discovery_kinds": dict(self.discovery_kinds.get(host, {}))} for host in sorted(hosts)},
                "scope": "Reservations within original cap, not requests made or final evidence acceptance"}
