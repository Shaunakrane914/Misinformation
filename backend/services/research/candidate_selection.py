"""Evidence-yield-first read prioritization: deterministic, explainable, bounded.

A score orders leads that are *already eligible* for reading. It does not qualify
evidence, prove relevance, independence or truth, and it never turns a search
snippet into an acquired article: only the normal reader can set captured content.
Final body, subject, objective and publication-date gates run unchanged afterwards.

Signals (each named in the returned components, so every ordering is auditable):

1. exact target / objective match in the lead's own title and URL,
2. correct publication window where it is relevant (Trending),
3. observed primary/official source flags (discovery claims, never verified here),
4. an actual article/document URL rather than a wrapper, index or hub,
5. publisher diversity as a soft, continuous penalty,
6. historical publisher yield as a weak, bounded routing signal only.

Nothing here suppresses a publisher permanently. A strong lead from a publisher that
disappointed twice still outranks a weak lead from a new one.
"""
import re
from collections import Counter
from urllib.parse import urlsplit

MULTIPART_SUFFIXES = {"co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "co.in", "co.jp", "co.nz", "com.br", "com.sg",
                      "com.hk", "com.cn", "co.za", "com.mx"}
_INDEX_SEGMENT = re.compile(r"(?:^|/)(?:tags?|categor(?:y|ies)|topics?|search|feeds?|rss|archives?|authors?|sitemap(?:s)?|page/\d+)(?:/|\.xml|\.html?|$)")
_FILE_ENDING = re.compile(r"\.(?:html?|php|aspx?|cms|shtml)$")
READ_FLOOR = 1.0     # below this a lead is "low expected yield": read only if nothing better can arrive


def publisher_group(host):
    """Registrable-domain approximation. An observed host group, never an owner."""
    labels = [part for part in (host or "").lower().strip(".").split(".") if part]
    if labels[:1] == ["www"]:
        labels = labels[1:]
    if len(labels) <= 2:
        return ".".join(labels)
    return ".".join(labels[-3:]) if ".".join(labels[-2:]) in MULTIPART_SUFFIXES else ".".join(labels[-2:])


def group_of_url(url):
    try:
        return publisher_group(urlsplit(url or "").hostname or "")
    except ValueError:
        return ""


def _tokens(text):
    return re.findall(r"[^\W_]+", str(text or "").casefold(), re.UNICODE)


def _norm(text):
    return " ".join(_tokens(text))


def article_shaped(url):
    """True for a path that looks like one document: a descriptive slug or a dated path.

    Shape is a prior, not proof: a slug proves nothing about the page body.
    """
    try:
        path = urlsplit(url or "").path.lower()
    except ValueError:
        return False
    segments = [s for s in path.split("/") if s]
    if not segments or _INDEX_SEGMENT.search(path.strip("/")):
        return False
    slug = _FILE_ENDING.sub("", segments[-1])
    words = [w for w in re.split(r"[-_]+", slug) if w]
    dated = bool(re.search(r"/(?:19|20)\d\d/\d{1,2}(?:/|$)", path) or re.search(r"(?:19|20)\d\d-\d\d-\d\d", path))
    # Many genuine publishers put descriptive article slugs at the host root.
    # Path depth alone must not demote those observed URLs to non-articles.
    if len(words) >= 4:
        return True
    return dated and len(words) >= 2


def is_index_like(url):
    try:
        path = urlsplit(url or "").path.lower().strip("/")
    except ValueError:
        return True
    return not path or bool(_INDEX_SEGMENT.search(path)) or bool(re.fullmatch(r"[a-z]{2}(?:[-/][a-z]{2})?", path))


class YieldMemory:
    """Per-publisher-group outcome counts for ONE investigation.

    Two bounded, recoverable signals; neither defers, blocks or bans a publisher:

    * ``signal``: the smoothed hit rate versus the observed ~28% base rate (+/-0.5 at most);
    * ``streak_penalty``: consecutive reads without a usable passage cost up to 2.0 points,
      and one usable read clears it. A strong lead (title/URL match, article URL, +5 or more)
      from a publisher that disappointed repeatedly can therefore still be read.
    """

    def __init__(self):
        self.reads = Counter()
        self.usable = Counter()
        self.streak = Counter()

    def record(self, group, usable):
        if group:
            self.reads[group] += 1
            self.usable[group] += int(bool(usable))
            self.streak[group] = 0 if usable else self.streak[group] + 1

    def signal(self, group):
        n = self.reads[group]
        if n < 2:
            return 0.0
        raw = (self.usable[group] + 0.5) / (n + 1.0) - 0.28
        return max(-0.5, min(0.5, 1.2 * raw))

    def streak_penalty(self, group):
        return -min(2.0, 0.5 * max(0, self.streak[group] - 1)) if self.streak[group] >= 2 else 0.0

    def snapshot(self):
        return {g: {"reads": self.reads[g], "usable": self.usable[g], "zero_yield_streak": self.streak[g]} for g in self.reads}


class SelectionContext:
    def __init__(self, target, domain, memory=None, group_reads=None):
        self.target = target
        self.domain = domain
        self.target_tokens = [t for t in _tokens(target)]
        self.target_phrase = " ".join(self.target_tokens)
        self.memory = memory or YieldMemory()
        self.group_reads = group_reads if group_reads is not None else Counter()


def score_candidate(item, ctx, *, is_wrapper, is_index):
    """Return ``(score, components)``. ``is_wrapper``/``is_index`` come from the engine's own predicates."""
    from backend.services.research.content_roles import OBJECTIVE_TERMS, matches_objective
    url = item.canonical_url or ""
    title = _norm(item.title)
    snippet_title = _norm((item.title or "") + " " + (item.snippet or ""))
    c = {}
    tokens = ctx.target_tokens
    if tokens:
        present = sum(1 for t in tokens if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", title))
        fraction = present / len(tokens)
        if ctx.target_phrase and ctx.target_phrase in title:
            c["target_in_title"] = 3.0
        elif fraction == 1.0:
            c["target_in_title"] = 3.0
        elif ctx.domain == "personal":
            c["target_in_title"] = 2.0 * fraction if fraction == 1.0 else 0.5 * fraction
        else:
            c["target_in_title"] = 2.0 * fraction
        slug = " ".join(_tokens(urlsplit(url).path + " " + (urlsplit(url).hostname or "")))
        if all(re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", slug) for t in tokens):
            c["target_in_url"] = 2.0
    if ctx.domain in OBJECTIVE_TERMS and matches_objective(snippet_title, ctx.domain):
        c["objective_match"] = 1.0
    if ctx.domain == "personal" and re.search(r"\b(?:statement|interview|transcript|speech|remarks|testimony)\b", title):
        c["observed_statement_format"] = 1.5
    if is_wrapper:
        c["opaque_wrapper"] = -3.0
    elif is_index:
        c["index_or_hub"] = -3.0
    elif article_shaped(url):
        c["article_url"] = 2.0
    if ctx.domain == "trending":
        priority = item.metadata.get("harvest_temporal_priority")
        c["publication_window"] = {0: 1.5, 1: 0.0, 2: -2.5, 3: -3.0}.get(priority, 0.0)
    elif item.published_at:
        c["dated_lead"] = 0.5
    if item.primary_source or item.official_source:
        c["observed_primary_or_official_flag"] = 1.0
    group = group_of_url(url)
    if group and ctx.group_reads[group]:
        c["publisher_diversity"] = -min(2.4, 0.6 * ctx.group_reads[group])
    memory = ctx.memory.signal(group)
    if memory:
        c["publisher_history_weak"] = round(memory, 3)
    streak = ctx.memory.streak_penalty(group)
    if streak:
        c["in_run_zero_yield_streak"] = streak
    return round(sum(v for v in c.values() if v), 3), {k: v for k, v in c.items() if v}
