"""Keep presentation instructions out of discovery without rewriting claims."""
import re


_DIRECTIVE = r"(?:research|investigate|find|analy[sz]e|compare|identify|prioritize|preserve|distinguish|separate|include|clearly distinguish|present|use)"
_REPORT_DIRECTIVE = r"(?:identify\s+actual\s+documented|(?:clearly\s+)?distinguish|separate|preserve|present|include)"


def is_research_instruction(text):
    # Topic-first requests often put the actual instruction after a delimiter.
    # Do not turn that instruction into a proposition or use it as search terms.
    if re.search(r"[;:]\s*(?:show|identify|preserve|distinguish|separate|include)\b", text, re.I):
        head = re.split(r"[;:]\s*(?:show|identify|preserve|distinguish|separate|include)\b", text, maxsplit=1, flags=re.I)[0]
        finite = re.search(r"\b(?:is|are|was|were|has|have|had|said|says|recalled|resigned|announced|filed|acquired|denied|reported)\b", head, re.I)
        nominal = re.search(r"\b(?:latest|recent|original)\s+(?:reported\s+)?(?:quarterly\s+|annual\s+|public\s+)?(?:results|statements|interviews|coverage|developments)\b", head, re.I)
        if not finite or nominal:
            return True
    return bool(re.match(r"^(?:please\s+)?" + _DIRECTIVE + r"\b", text, re.I)
                and not re.match(r"^research\s+(?:shows|showed|found|indicates|suggests|confirms|was|is|has|by|from|at)\b", text, re.I))


def discovery_objective(text, entity):
    """Remove a leading imperative and trailing report instructions only.

    The original objective remains in the plan for task routing and synthesis.
    Literal quotations, propositions, negation, dates and site restrictions are
    never shortened. A known entity is required; do not infer a replacement.
    """
    if not entity or not is_research_instruction(text) or re.search(r'["“”]|https?://|\bsite:', text, re.I):
        return text
    text = re.split(r"[;:]\s*(?:show|identify|preserve|distinguish|separate|include)\b", text, maxsplit=1, flags=re.I)[0] if not re.search(
        r"[;:].*\d|[;:].*\b(?:not|never|false|denied|before|after|since|until)\b", text, re.I) else text
    # Only a sentence introducing another imperative is a report instruction.
    # Do not split abbreviations, decimals or subsequent factual sentences.
    parts = re.split(r"(?<=[.!?])\s+(?=(?:please\s+)?" + _REPORT_DIRECTIVE + r"\b)", text, maxsplit=1, flags=re.I)
    # A later instruction can carry an explicit time/number/negation constraint.
    # Keep it intact rather than guessing which of its words are expendable.
    if len(parts) > 1 and re.search(
            r"\d|\b(?:january|february|march|april|may|june|july|august|september|october|november|december|"
            r"last|past|today|yesterday|since|until|before|after|not|never|false|denied)\b", parts[1], re.I):
        return text
    objective = parts[0]
    objective = re.sub(r"^(?:please\s+)?" + _DIRECTIVE + r"\s+", "", objective, count=1, flags=re.I).rstrip(".?! ")
    if entity.casefold() not in objective.casefold():
        return text
    return objective
