"""Deterministic finite-predicate recognition for prose selection.

A source paragraph is a candidate proposition only when some sentence has a
finite verb with a subject before it and something after it. This replaces a
hand-picked verb list (``is/are/has/...``) that rejected ordinary prose such as
"The institute states that ..." or "Researchers will present ...", while it
accepted headlines such as "Why Toyota Tsusho is leaning into EV-battery
recycling" because they happened to contain "is".

This is an explicitly heuristic, dependency-free filter. It is not a parser and
does not judge relevance, truth, date, authority, or entailment. It never edits
source text, so exact offsets and hashes are unaffected. Where English is
ambiguous it prefers a false negative (the paragraph stays inspectable in the raw
capture) over a false positive (a heading, label, menu or advertisement becoming
qualified evidence). The rules, in order of strength:

* a sentence must be a finished declarative: it ends with a period (not ``?``,
  ``!``, ``:``, a truncation ellipsis, or nothing) and is not ALL CAPS;
* verbs must be lowercase in the source, so Title Case headlines never match;
* the verb needs a subject head before it (one comma-delimited aside is allowed)
  and a complement after it, and a third-person verb must agree with it;
* a third-person present verb needs subject evidence, because most "-s" forms
  are also plural nouns ("states", "results", "experiences"): a pronoun, a
  proper-noun head ("SEC states"), or a determiner-led noun phrase ("The area
  covers ...") must precede it;
* past forms are rejected as agentless reduced relatives ("funded by ...");
* labels, menus, cookie/newsletter/promotional boilerplate, photo captions,
  markup, questions, imperatives and copy addressed to the reader ("you",
  "your") never count.
"""
import re

__all__ = ["has_finite_predicate", "find_finite_predicate"]

_TOKEN = re.compile(r"([^\W\d_][\w'’-]*)|(\d[\w.,%'’-]*)|([,;:—–])")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])[\"”’)\]]*\s+(?=[\"“‘(\[]?[A-Z0-9])|\n+")
_PARENTHETICAL = re.compile(r"\([^()]{0,240}\)")
_MARKUP = re.compile(r"</?[a-z][^>]{0,200}>|<!\[CDATA\[|\]\]>", re.I)
_MD_LINK = re.compile(r"!?\[([^\]]{0,200})\]\([^)]{0,500}\)")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)

# Metadata rows, menus, cookie/newsletter/ad copy: never propositions even when
# they contain a verb ("This site uses cookies to improve your experience").
_LABEL = re.compile(
    r"^\W*(?:article\s+title|title|subject\s+of\s+research|keywords?|tags?|news\s+source|"
    r"article\s+references?|references?|doi|image\s+credits?|photo(?:\s+credit)?|credits?|"
    r"captions?|disclaimer|categor(?:y|ies)|posted\s+(?:in|on|by)|filed\s+under|source|sources|author|"
    r"related(?:\s+(?:articles?|posts?|stories|topics))?|topics?|share|advertisement)\s*[:—–-]",
    re.I)
_BOILERPLATE = re.compile(
    r"\b(?:cookies?(?:\s+(?:policy|settings|consent|preferences|notice))?|accept\s+all|"
    r"subscribe\s+(?:to|now|today|for)|sign\s+up\s+(?:for|to|now|today)|newsletter|"
    r"log\s*in\s+to|create\s+(?:an\s+)?account|click\s+here|read\s+(?:more|full|the\s+full)|continue\s+reading|"
    r"learn\s+more|get\s+started|(?:request|book)\s+a\s+(?:demo|quote|call)|try\s+(?:it\s+)?free|"
    r"please\s+(?:check|visit|click|see|read|contact|email|call)|check\s+out|"
    r"advertisements?|sponsored\s+(?:content|post|by)|follow\s+us|share\s+(?:this|on)|"
    r"terms\s+(?:of\s+(?:use|service)|and\s+conditions)|privacy\s+policy|all\s+rights\s+reserved|"
    r"copyright|buy\s+now|shop\s+now|order\s+now|add\s+to\s+(?:cart|basket)|limited[- ]time|"
    r"free\s+(?:shipping|delivery|trial)|promo(?:tion(?:al)?)?\s+code|discount\s+code|coupon|"
    r"\d+\s?%\s+off|save\s+up\s+to|contact\s+us|feel\s+free\s+to|your\s+privacy|"
    r"(?:consent|agree)\s+to\s+(?:our|the|third)|ad\s+feature|"
    r"photo\s+(?:by|credit)|image\s+credits?|file\s+photo|getty\s+images|shutterstock|nurphoto|ap\s+photo|"
    r"(?:this|these)\s+(?:combination\s+|composite\s+|file\s+|undated\s+|handout\s+)?"
    r"(?:photos?|images?|photographs?|video|illustration|graphic|frame)\b|the\s+graphic\s+(?:does|shows|depicts)|"
    r"pictured|illustration\s+by)\b|©", re.I)
_FILE_CAPTION = re.compile(r"^\W*FILE\b")
# Prose addressed to the reader ("your", "you can") is advertising or instruction,
# not a reported source proposition. First-person plural is deliberately NOT
# excluded: executive and company statements ("We are announcing ...") are
# exactly the primary statements the agents need to keep.
_SECOND_PERSON = re.compile(r"\b(?:you|your|yours|yourself|you['’](?:re|ll|ve|d))\b", re.I)
_QUOTED = re.compile(r"“[^”]{0,600}”|\"[^\"]{0,600}\"")
_QUESTION_START = re.compile(r"^\W*(?:what|why|how|who|whom|whose|which|when|where|whether)\b", re.I)
_IMPERATIVE_START = re.compile(
    r"^\W*(?:discover|learn|find|read|see|explore|meet|get|join|download|watch|sign|try|start|stop|lock|head|check|"
    r"click|subscribe|follow|share|visit|contact|call|order|buy|shop|save|enjoy|experience|unlock|stay|keep|"
    r"remember|stream|listen|view|browse|choose|select|book|apply|register|enter|win|claim|upgrade|compare)\b", re.I)
# Footnote/asterisk-led disclaimers ("¹When used in ...", "* Disclaimer: ...").
_FOOTNOTE_START = re.compile(r"^\s*(?:[¹²³⁰-⁹*†‡§]|\(?\d{1,2}\s*[.)]\s|\([a-z]\)\s)")

_MODALS = frozenset("will would can could may might must shall should cannot".split())
_AUXILIARIES = frozenset("is are was were has have had does did".split())
# is/are/was/were/has/have are accepted without agreement checks, as before.
_UNCONDITIONAL = frozenset("is are was were has have".split())
_NEGATED = re.compile(r"^(?:is|are|was|were|has|have|had|does|did|do|ca|could|would|should|must|wo)n't$|^can't$|^won't$")

_DETERMINERS = frozenset(
    "the a an its their his her our your my each every another any some all both no several many few such "
    "other more most less one two three".split())
_PRONOUNS = frozenset("it he she they we you i who which that this these those".split())
_PREPOSITIONS = frozenset(
    "of in on at by for with from to into over under about per via across between among within without through "
    "during after before against toward towards upon than as like off onto near around amid beyond despite "
    "except since until unless if when while because whether though although whereas whose".split())
_CONJUNCTIONS = frozenset("and or but nor yet so then".split())
_ADVERBS = frozenset(
    "also not never now still already soon just only even often usually typically generally currently recently "
    "previously newly formally officially publicly later first next further once ever always simply largely mostly "
    "mainly partly fully both either too very quite rather".split())
_NOT_ADVERBS = frozenset("family supply reply assembly anomaly monopoly rally belly bully early only july italy".split())

# Stems whose third-person/past forms are rarely nouns/adjectives.
_VERB_STEMS = """
accept accompany accomplish accuse achieve acknowledge acquire act adapt add address adopt advise advocate affect affirm
agree aim alert allege allow analyze analyse announce answer anticipate appeal appear apply appoint approve argue arrange
arrest ask assert assess assist assume assure attempt attend attract attribute authorize avoid await bar beat become begin
believe benefit blame block bring build calculate cancel capture carry cause celebrate challenge characterize chart choose
circulate cite clarify classify collaborate collect combine commence comment commit communicate compare compete complain
complete comply comprise conceal conclude condemn conduct confirm confront connect consider consist constitute consult
contact contain contend continue contribute convene convert convict coordinate correct create criticize cross debate decide
declare decline defend define delay deliver demand demonstrate deny depend depict deploy describe deserve detail detect
determine develop devote differ disclose discover discuss dismiss display dispute distribute document dominate draw drive
earn emerge emphasize employ enable encourage endorse enforce engage ensure enter establish evaluate examine exceed exclude
execute exhibit exist expand expect experience explain explore express extend facilitate fail fall feel fight finalize find
finish follow forecast form found frame generate give govern grant grow guarantee handle happen hire highlight hope identify
illustrate implement imply impose improve include incorporate indicate inform inspect install integrate intend interview
introduce invest investigate invite involve join justify keep kill know launch learn leave lend let link list locate lose
maintain make manage mandate mean meet mention merge monitor motivate negotiate nominate notify obtain observe occur operate
oppose organize outline oversee own participate partner pay perform permit pledge point portray possess predict prefer
prepare preserve prevent probe produce promise promote propose prosecute protect prove provide publish pursue put quote
raise ratify reach read realize receive recognize recommend recover recruit recycle reduce refer reflect refuse regard
register regulate reinforce reject relate release rely remain remove render repeat replace represent require rescue resign
resolve respond restore restrict retain retire reveal revise reward rise rule satisfy say schedule score secure see seek
select sell send serve settle share shape shift shut sign specialize specify speculate speak spend sponsor spread stay
stress struggle submit succeed suffer suggest summarize supply suspect sustain take teach tell tend testify think threaten
track train transfer treat trigger try turn undergo underline underscore understand undertake unveil update urge utilize
validate verify visit vow wait want warn wear welcome win wish withdraw witness worry write yield
""".split()
# Further stems, many of which are also common nouns ("report", "state", "cover").
_MORE_STEMS = """
aim approach article back base benefit boost call change charge check claim close cost count cover cut deal design drive drop
end estimate face feature figure file focus forecast form gain grant guide head hold host impact increase issue jump lead
launch limit look mark market match mean measure model move name need note offer open order pick place plan point post present
press price process profit project push rate reach record release report request research result return review rise rule run
service set shift show sign signal state step stock study support surge switch talk target test tip track trade trend turn
update use value view vote watch way win work
""".split()
# Common newswire/market/science verbs. Their past forms are usually clauses, so
# they carry no extra restriction.
_NEWS_STEMS = """
add caution climb debut decrease edge enact fine fuel fund hike indict insist lag lift loom lower miss narrow outpace
outperform pass play plunge prompt repeal roll run sentence shrink slash slip slump soar spark sue surpass tighten top
trail trim tumble underperform veto weigh widen
""".split()
# Stems whose past form is most often a participle inside a noun phrase ("batteries
# stored in a warehouse", "cells sourced from Asia"); a clause needs real subject evidence.
_PARTICIPLE_PRONE_STEMS = """
cap engineer export extract import manufacture mine power refine separate source store
""".split()
_STEMS = frozenset(_VERB_STEMS) | frozenset(_MORE_STEMS) | frozenset(_NEWS_STEMS) | frozenset(_PARTICIPLE_PRONE_STEMS)

# Past forms that, after a bare common noun, are usually reduced relatives
# ("funds designed to ...") rather than a finite clause.
_PARTICIPLE_BEFORE_TO = frozenset("designed intended expected scheduled required meant used aimed built made".split())

_IRREGULAR_PAST = frozenset(
    "began became brought built bought came chose drew drove fell felt found gave got grew held kept knew led made met "
    "paid ran said sold sent showed spoke spent stood took taught told thought understood won wore wrote rose sought "
    "lost meant withdrew undertook overtook underwent put set cut hit shut spread".split())


def _third_person(stem):
    if stem.endswith(("s", "x", "z", "ch", "sh", "o")):
        return {stem + "es"}
    if stem.endswith("y") and len(stem) > 2 and stem[-2] not in "aeiou":
        return {stem[:-1] + "ies"}
    return {stem + "s"}


def _past(stem):
    if stem.endswith("e"):
        return {stem + "d"}
    if stem.endswith("y") and len(stem) > 2 and stem[-2] not in "aeiou":
        return {stem[:-1] + "ied"}
    forms = {stem + "ed"}
    if len(stem) >= 3 and stem[-1] in "bdgklmnprt" and stem[-2] in "aeiou" and stem[-3] not in "aeiou":
        forms.add(stem + stem[-1] + "ed")
    return forms


_PARTICIPLE_PRONE_PAST = frozenset(form for stem in _PARTICIPLE_PRONE_STEMS for form in _past(stem))
_THIRD = set()
_PAST = set(_IRREGULAR_PAST)
for _stem in _STEMS:
    _THIRD |= _third_person(_stem)
    _PAST |= _past(_stem)
# Auxiliaries and modals are matched structurally, never as lexical forms.
_THIRD -= _AUXILIARIES | _MODALS
_PAST -= _AUXILIARIES | _MODALS


class _Token:
    __slots__ = ("kind", "surface", "lower")

    def __init__(self, kind, surface):
        self.kind = kind                      # "w" word, "n" number, "p" clause punctuation
        self.surface = surface.rstrip("-'’") or surface
        self.lower = self.surface.casefold().replace("’", "'")

    @property
    def starts_lower(self):
        return self.kind == "w" and self.surface[0].islower()

    @property
    def starts_upper(self):
        return self.kind == "w" and self.surface[0].isupper()


def _tokenize(sentence):
    tokens = []
    for match in _TOKEN.finditer(sentence):
        word, number, punctuation = match.groups()
        if word:
            tokens.append(_Token("w", word))
        elif number:
            tokens.append(_Token("n", number))
        else:
            tokens.append(_Token("p", punctuation))
    return tokens


def _is_adverb(token):
    """Closed adverb list plus lowercase "-ly" words; names like "Firefly" are not adverbs."""
    if token.kind != "w":
        return False
    if token.lower in _ADVERBS:
        return True
    return (token.surface[0].islower() and len(token.lower) > 4 and token.lower.endswith("ly")
            and token.lower not in _NOT_ADVERBS)


def _all_caps(words):
    letters = [c for w in words for c in w.surface if c.isalpha()]
    return len(letters) >= 12 and sum(c.isupper() for c in letters) / len(letters) > 0.7


def _subject_before(tokens, index, allow_number=False):
    """Return ``(subject_index, hopped)`` for the subject head before a verb.

    Adverbs are skipped. A figure can be the subject of an auxiliary/copula
    ("EPS of $5.80 is below ...") but not of a lexical verb ("3 states report"
    is a noun phrase). One comma-delimited aside ("Memory, or HBM, has become
    ...") may sit between subject and verb; colons and dashes never bridge a clause.
    """
    k = index - 1
    hopped = False
    while True:
        while k >= 0 and _is_adverb(tokens[k]):
            k -= 1
        if k > 0 and not hopped and tokens[k].kind == "p" and tokens[k].surface in (",", "—", "–"):
            hopped, k = True, k - 1
            continue
        break
    if k < 0 or tokens[k].kind == "p" or (tokens[k].kind == "n" and not allow_number):
        return None
    return k, hopped


_PLURAL_PRONOUNS = frozenset("they we you i these those".split())
_RELATIVE_PRONOUNS = frozenset("who whom which whose".split())


def _subject_head_ok(token, third_person, clause_initial=True):
    lower = token.lower
    if token.kind == "n":
        return True
    if lower in _PRONOUNS:
        if third_person and lower in _PLURAL_PRONOUNS:
            return False        # "these signs": a plural determiner + noun, not pronoun + verb
        if lower in _RELATIVE_PRONOUNS or (lower == "that" and not clause_initial):
            return False        # a relative-clause verb does not make a main clause
        return True
    if (lower in _DETERMINERS or lower in _PREPOSITIONS or lower in _CONJUNCTIONS or lower in _MODALS
            or lower in _AUXILIARIES or lower == "to" or lower.endswith(("'s", "s'"))):
        return False
    if third_person and lower.endswith("s") and not lower.endswith(("ss", "is", "us")) and not token.starts_upper:
        return False    # plural-looking noun cannot agree with a third-person singular verb
    return True


def _clause_start(tokens, index):
    start = 0
    for k in range(index):
        if tokens[k].kind == "p":
            start = k + 1
    return start


def _subject_marked(tokens, start, subject_index):
    """Clause-start evidence that the preceding noun is a real subject."""
    head, first = tokens[subject_index], tokens[start]
    if head.lower in _PRONOUNS:
        return True
    # A proper-noun head ("SEC states", "Meta Platforms reports", "..., Adobe reports"):
    # an acronym, a name continuing a capitalized word, or a capitalized word
    # inside the clause. A capitalized first word alone could be any sentence-
    # initial common noun ("Sales fall ..."), so it is not evidence.
    if head.starts_upper:
        previous = tokens[subject_index - 1] if subject_index > 0 else None
        if (len(head.surface) >= 2 and head.surface.isalpha() and head.surface.isupper()) or subject_index > start \
                or (previous is not None and previous.starts_upper):
            return True
    # A determiner/possessive opening the clause introduces a real noun phrase
    # ("The third area covers ..."), unlike a bare compound ("NC ballot requests ...").
    return first.kind == "w" and first.lower in _DETERMINERS


def _has_complement(tokens, index):
    return any(t.kind in ("w", "n") for t in tokens[index + 1:])


def _sentence_predicate(sentence):
    """Return the finite verb (as written) that makes ``sentence`` a clause, or None."""
    text = sentence.strip()
    if (not text or _LABEL.match(text) or _BOILERPLATE.search(text) or _FILE_CAPTION.match(text)
            or _QUESTION_START.match(text) or _IMPERATIVE_START.match(text)):
        return None
    # Speech inside quotation marks reports what someone said ("If you pay, we
    # will sue," the CEO told Reuters); only the publisher's own voice is excluded.
    if _SECOND_PERSON.search(_QUOTED.sub(" ", text)):
        return None
    tokens = _tokenize(text)
    words = [t for t in tokens if t.kind in ("w", "n")]
    if len(words) < 4 or _all_caps(words):
        return None
    # A finished declarative sentence ends with a period. Questions, exclamations,
    # lead-ins ("...:"), truncated snippets ("..."/"…") and unpunctuated
    # headlines/captions/list rows are not propositions.
    if not re.search(r"(?<![.…])\.[\"”’)\]]*$", text):
        return None
    for index, token in enumerate(tokens):
        if not token.starts_lower:
            continue
        lower = token.lower
        structural = lower in _UNCONDITIONAL or lower in _MODALS or lower in _AUXILIARIES or bool(_NEGATED.match(lower))
        found = _subject_before(tokens, index, allow_number=structural)
        if found is None:
            continue
        subject, hopped = found
        head = tokens[subject]
        clause_start = 0 if hopped else _clause_start(tokens, index)
        if lower in _UNCONDITIONAL:
            return token.surface
        if structural:
            if not _subject_head_ok(head, lower == "does", subject == clause_start):
                continue
            following = next((t for t in tokens[index + 1:] if not _is_adverb(t)), None)
            if (following is not None and following.starts_lower
                    and following.lower not in _PREPOSITIONS | _DETERMINERS | _CONJUNCTIONS | {"that", "this"}):
                return token.surface
            continue
        if lower in _THIRD:
            if not _subject_head_ok(head, True, subject == clause_start) or not _has_complement(tokens, index):
                continue
            # Most "-s" verb forms are also plural nouns ("experiences", "yields",
            # "results"), so adjective + plural noun must not read as subject + verb.
            if not _subject_marked(tokens, clause_start, subject):
                continue
            return token.surface
        if lower in _PAST:
            if not _subject_head_ok(head, False, subject == clause_start) or not _has_complement(tokens, index):
                continue
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            strong = head.lower in _PRONOUNS or (head.starts_upper and subject > clause_start)
            if not strong and following is not None:
                nxt = following.lower
                if nxt == "by":
                    continue    # "a pilot funded by ...": reduced passive, not a finite clause
                if nxt == "to" and lower in _PARTICIPLE_BEFORE_TO:
                    continue    # "funds designed to outperform ...": the real verb comes later
                if following.starts_lower and (nxt in _STEMS or nxt in _THIRD or nxt in _AUXILIARIES
                                               or nxt in _MODALS):
                    continue    # "customers highlighted include ...": participle + the real verb
            if (subject == clause_start and head.lower.endswith("ing") and head.starts_upper
                    and lower.endswith("ed")):
                continue        # "Rising recycled content ...": clause-initial -ing modifier
            if lower in _PARTICIPLE_PRONE_PAST and not _subject_marked(tokens, clause_start, subject):
                continue        # "batteries stored in a warehouse": a noun phrase, not a clause
            return token.surface
    return None


def find_finite_predicate(text):
    """Return the first finite verb (as written) that heads a clause, else None."""
    if not isinstance(text, str) or not text.strip():
        return None
    if _BOILERPLATE.search(text) or _FOOTNOTE_START.match(text) or _MARKUP.search(text):
        return None         # one boilerplate/caption/markup cue disqualifies the whole paragraph
    text = _URL.sub(" ", _MD_LINK.sub(r"\1", _PARENTHETICAL.sub(" ", text)))
    for sentence in _SENTENCE_BREAK.split(text):
        verb = _sentence_predicate(sentence)
        if verb:
            return verb
    return None


def has_finite_predicate(text):
    """True when some sentence has a subject, a finite verb and a complement."""
    return find_finite_predicate(text) is not None
