"""Observed event/subject roles for passage ranking, not event truth or virality."""
import re

_ACTION = re.compile(r"\b(?:announced|released|launched|unveiled|introduced|deployed|opened|approved|filed|recalled|reported|began|started|signed|appointed|denied)\b|\b(?:is|are)\s+(?:now\s+)?(?:testing|launching|opening|deploying)\b", re.I)
_BACKGROUND = re.compile(r"\b(?:historically|historical background|in the past|originally developed|at the time|since (?:19|20)\d{2})\b", re.I)
_COMPETITION = re.compile(r"\b(?:compet(?:e|es|ing|ition|itor)|rival|rivals|pressure|presses|challeng\w*|attacking|stronghold|stranglehold|taking.{0,20}shot)\b", re.I)


def _competitive_target_relation(title, lead, escaped):
    """Require an observed relation to the target, not general difficulty words."""
    before = (r"\b(?:challeng(?:e|es|ed|ing)|pressur(?:e|es|ed|ing)|presses|attacking|"
              r"compet(?:e|es|ing)\s+(?:with|against)|(?:rival|competitor)s?\s+(?:of|to)|"
              r"taking.{0,30}shot\s+at)\s+(?:the\s+)?" + escaped + r"\b")
    owned = r"\b" + escaped + r"['’]s\s+(?:[\w-]+\s+){0,3}(?:stronghold|stranglehold|rivals?|competitors?)\b"
    for unit in [title or '', *re.split(r'(?<=[.!?])\s+', lead)]:
        if re.search(before, unit, re.I) or re.search(owned, unit, re.I):
            return True
    return False


def event_priority(paragraph, position):
    """Prefer actual lead announcements to number-rich history, preserving bytes.

    A publication timestamp alone never establishes when an event happened.
    Only rank the source's own words; negative/conditional statements are not
    rewritten into affirmative events.
    """
    lead = re.split(r"(?<=[.!?])\s+", paragraph.strip(), maxsplit=1)[0]
    action = bool(_ACTION.search(lead)) and not _BACKGROUND.search(lead)
    return (4.0 if position < 3 and action else 0.0) - (3.0 if _BACKGROUND.search(paragraph) and not action else 0.0)


def classify_source_context(title, body, target, *, is_topic=False):
    """Conservative subject-role labels from captured title/lead, not a new gate.

    Competitive reporting remains inspectable and explicitly labeled. A former
    affiliation alone cannot turn somebody else's interview into a development
    about the investigated organization.
    """
    target = re.sub(r"\([^)]*\)", "", target or "").strip()
    if not target or is_topic:
        return {"classification": "PRIMARY_TOPIC", "reason": "TOPIC_QUERY", "is_heuristic": True}
    escaped = re.escape(target)
    lead = " ".join(re.split(r"\n\s*\n", body or "")[:3])[:2500]
    affiliation = re.search(r"\b(?:ex[-\s]+|former\s+)" + escaped + r"\b|\b" + escaped + r"[-\s]+turned[-\s]", title or "", re.I)
    target_action = re.search(r"\b" + escaped + r"(?:['’]s)?(?:\s+[\w-]+){0,3}\s+(?:has\s+|have\s+)?(?:announced|released|launched|unveiled|introduced|deployed|filed|recalled|appointed|denied)\b", lead, re.I)
    allegation = re.search(r"\b(?:alleges?|accuses?|investigat\w*|lawsuit|scandal)\b.{0,80}\b" + escaped + r"\b|\b" + escaped + r"\b.{0,80}\b(?:lawsuit|investigat\w*|scandal)\b", (title or "") + " " + lead, re.I)
    if affiliation and not target_action and not allegation:
        return {"classification": "INCIDENTAL_MENTION", "reason": "FORMER_AFFILIATION_NOT_TARGET_EVENT", "is_heuristic": True}
    # Competition vocabulary alone does not demote an article whose observed
    # headline is principally about the target (e.g. "Aster faces pressure").
    # This is a source-role heuristic, never authentication or event entailment.
    target_headline = re.match(r"\s*" + escaped + r"\b", title or "", re.I)
    if (_COMPETITION.search((title or "") + " " + lead)
            and _competitive_target_relation(title, lead, escaped)
            and not target_action and not target_headline):
        return {"classification": "COMPETITIVE_CONTEXT", "reason": "SOURCE_REPORTS_COMPETITIVE_IMPACT_NOT_TARGET_ANNOUNCEMENT", "is_heuristic": True}
    return {"classification": "PRIMARY_TOPIC", "reason": "TARGET_REPORTING_CONTEXT", "is_heuristic": True}
