"""Lexical headline joins for URL discovery, not claim support or entailment."""
import re


def provisional_topic_overlap(target, observed):
    """Partial topic recall for discovery only, never final entity/evidence fit.

    Publisher headlines often omit modifiers (e.g. the scale of a technology).
    Require two distinct whole meaningful words and at least half the topic.
    Two-token names/topics cannot pass on just one token. No synonyms, bodies,
    dates or source credibility are inferred here.
    """
    from backend.services.research.entity_resolver import GENERAL_STOPWORDS
    expected = {word for word in re.findall(r"[a-z0-9]+", str(target).casefold())
                if len(word) >= 3 and word not in GENERAL_STOPWORDS}
    actual = set(re.findall(r"[a-z0-9]+", str(observed).casefold()))
    overlap = len(expected & actual)
    return len(expected) >= 3 and overlap >= 2 and overlap / len(expected) >= .5


def headline_overlap(expected, observed):
    # Site scope is a query operator, not part of the article headline. Do not
    # lower the actual 75% headline join when an observed publisher is supplied.
    headline = re.sub(r"\bsite:\S+\s*", "", str(expected or ""), flags=re.I)
    terms = set(re.findall(r"[a-z0-9]+", headline.casefold()))
    actual = set(re.findall(r"[a-z0-9]+", str(observed or "").casefold()))
    return len(terms & actual) / len(terms) if terms else 0.0
