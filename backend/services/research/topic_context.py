"""Bounded deterministic routing context; labels are hypotheses, never evidence.

No person-name table, network lookup, model call or permission input. Explicit
request hints may guide relevance but cannot grant acquisition access.
"""
from dataclasses import dataclass, field, asdict
import re


TOPICS = {
    'bollywood': ('bollywood', 'बॉलीवुड', 'हिंदी सिनेमा'),
    'regional_cinema': ('tamil cinema', 'telugu cinema', 'malayalam cinema', 'kannada cinema', 'मराठी सिनेमा'),
    'film': ('film', 'films', 'movie', 'movies', 'cinema', 'actor', 'actress', 'फिल्म', 'अभिनेता', 'अभिनेत्री'),
    'hollywood': ('hollywood', 'हॉलीवुड'),
    'cricket': ('cricket', 'cricketer', 'क्रिकेट', 'ipl', 'test match', 't20'),
    'sports': ('athlete', 'football', 'tennis', 'basketball', 'olympics', 'sports', 'खेल'),
    'politics': ('politician', 'parliament', 'minister', 'legislation', 'politics', 'मंत्री', 'संसद'),
    'elections': ('election', 'elections', 'electoral', 'चुनाव'),
    'semiconductors': ('semiconductor', 'semiconductors', 'chip manufacturing', 'chipmaker', 'foundry'),
    'technology': ('technology', 'software', 'hardware', 'artificial intelligence', 'ai', 'gpu'),
    'energy': ('battery', 'batteries', 'recycling', 'energy storage', 'solar', 'renewable'),
    'health': ('health', 'vaccine', 'medicine', 'clinical', 'disease', 'स्वास्थ्य'),
    'research': ('research', 'scientific', 'study', 'preprint'),
    'finance': ('financial', 'revenue', 'earnings', 'profit', 'quarterly', 'filing', 'listed company', 'वित्तीय'),
    'cybersecurity': ('phishing', 'ransomware', 'malware', 'credential theft', 'vulnerability', 'data breach'),
    'product_safety': ('recall', 'product safety', 'fire hazard', 'defective product'),
    'scams': ('scam', 'fraud', 'impersonation', 'counterfeit', 'fake advertisement', 'fake endorsement'),
    'false_quotes': ('false quote', 'fabricated quote', 'misattributed', 'did not say', 'झूठा बयान'),
}


def _has(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text, re.I))


def normal_agent(agent, domain=''):
    value = str(agent).lower().removesuffix('_agent')
    if value in {'personal', 'personal_watch'}:
        return 'personal_watch'
    if value in {'scout', 'trending', 'brandshield'}:
        return value
    return {'financial': 'scout', 'brand': 'brandshield', 'personal': 'personal_watch',
            'personal_watch': 'personal_watch', 'trending': 'trending'}.get(domain, 'research')


@dataclass(frozen=True)
class ResearchContext:
    subject: str
    agent: str
    tasks: tuple
    topics: tuple = ()
    subject_type: str = 'unknown'
    aliases: tuple = ()
    jurisdiction: str = 'UNKNOWN'
    language: str = 'und'
    time_window: str = 'unspecified'
    confidence: float = 0.0
    ambiguity: tuple = ()
    basis: str = 'DETERMINISTIC_REQUEST_CUES'
    topic_scores: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def infer_context(claim, subject='', *, agent='', domain='', hints=None, observed_titles=()):
    hints = hints if isinstance(hints, dict) else {}
    subject, claim = str(subject)[:300], str(claim)[:2000]
    text = claim
    # Do not interpret the product/company's own name as an incident allegation.
    task_text = re.sub(r'(?<!\w)' + re.escape(subject) + r'(?!\w)', ' ', claim, flags=re.I) if subject else claim
    agent = normal_agent(agent, domain)
    tasks = {'scout': ['FINANCIAL_VERIFICATION'], 'trending': ['TOPIC_DISCOVERY'],
             'brandshield': ['BRAND_RISK'], 'personal_watch': ['IDENTITY_THREAT']}.get(agent, ['GENERAL_RESEARCH'])
    if agent == 'personal_watch' and re.search(r'\b(statement|interview|speech|remarks|transcript|said)\b', task_text, re.I):
        tasks = ['PUBLIC_STATEMENT']
    if _has(task_text, 'false quote') or _has(task_text, 'fabricated quote') or _has(task_text, 'did not say'):
        tasks = ['QUOTE_VERIFICATION'] if agent == 'personal_watch' else tasks
    if agent == 'brandshield':
        for task, cues in [('PHISHING', ('phishing',)), ('COUNTERFEIT', ('counterfeit', 'fake product')),
                           ('PRODUCT_SAFETY', ('recall', 'product safety')),
                           ('ENDORSEMENT_CLAIM', ('fake advertisement', 'fake endorsement', 'celebrity advertisement')),
                           ('IMPERSONATION', ('impersonation',))]:
            if any(_has(task_text, cue) for cue in cues):
                tasks.append(task)
    scores = {topic: .8 for topic, cues in TOPICS.items() if any(_has(
        task_text if topic in {'product_safety', 'scams', 'false_quotes'} else text, cue) for cue in cues)}
    if re.search(r'\bfake\s+(?:celebrity\s+)?(?:ad(?:vertisement)?s?|endorsements?)\b', task_text, re.I):
        scores['scams'] = .8
    requested_topics = hints.get('topics', [])
    if isinstance(requested_topics, (list, tuple)):
        scores.update({t: .85 for t in requested_topics[:4] if isinstance(t, str) and t in TOPICS})
    # Unknown bare names stay ambiguous. Observed titles must contain all name
    # tokens before they can offer weak routing cues; this cannot qualify a body.
    tokens = re.findall(r'\w+', subject.casefold())
    observations_used = 0
    country_cues = {'IN': ('india', 'indian'), 'US': ('united states', 'american'),
                    'UK': ('united kingdom', 'british'), 'AU': ('australia', 'australian')}
    request_countries = {country for country, cues in country_cues.items() if any(_has(text, cue) for cue in cues)}
    observed_countries = set()
    for title in list(observed_titles)[:8]:
        title = str(title)[:400]
        words = set(re.findall(r'\w+', title.casefold()))
        if not tokens or not set(tokens) <= words:
            continue
        observed_countries.update(country for country, cues in country_cues.items()
                                  if any(_has(title, cue) for cue in cues))
        for topic, cues in TOPICS.items():
            if any(_has(title, cue) for cue in cues):
                scores.setdefault(topic, .55)
                observations_used += 1
    subject_type = hints.get('subject_type', 'unknown')
    if subject_type not in {'person', 'company', 'organisation', 'topic', 'unknown'}:
        subject_type = 'unknown'
    if subject_type == 'unknown':
        if any(_has(text, cue) for cue in ('actor', 'actress', 'cricketer', 'athlete', 'politician', 'अभिनेता', 'अभिनेत्री')):
            subject_type = 'person'
        elif any(_has(text, cue) for cue in ('manufacturer', 'listed company', 'corporation', 'company')):
            subject_type = 'company'
        elif agent == 'trending' and scores and not any(_has(text, cue) for cue in ('celebrity', 'interview', 'statement')):
            subject_type = 'topic'
    aliases = hints.get('aliases', [])
    aliases = tuple(a.strip() for a in aliases[:4] if isinstance(a, str) and 0 < len(a.strip()) <= 100) if isinstance(aliases, (list, tuple)) else ()
    language = str(hints.get('language', 'und'))
    if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z]{2,8})?', language):
        language = 'und'
    if language == 'und' and re.search(r'[\u0900-\u097f]', claim):
        language = 'und-Deva'  # Devanagari alone cannot distinguish Hindi/Marathi/etc.
    country = str(hints.get('jurisdiction', 'UNKNOWN')).upper()
    if country not in {'IN', 'US', 'UK', 'HK', 'EU', 'AU', 'GLOBAL', 'UNKNOWN'}:
        country = 'UNKNOWN'
    if country == 'UNKNOWN' and len(request_countries) == 1:
        country = next(iter(request_countries))
    elif country == 'UNKNOWN' and not request_countries and len(observed_countries) == 1:
        country = next(iter(observed_countries))
        observations_used += 1  # Routing hint only, not nationality/identity proof.
    if country == 'UNKNOWN' and any(t in scores for t in ('bollywood', 'regional_cinema')):
        country = 'IN'
    window = str(hints.get('time_window', hints.get('time_scope', 'unspecified')))[:60]
    ambiguity = []
    if not scores:
        ambiguity.append('TOPIC_UNRESOLVED_NEUTRAL_DISCOVERY_REQUIRED')
    if subject_type == 'unknown':
        ambiguity.append('SUBJECT_TYPE_UNRESOLVED')
    if country == 'UNKNOWN':
        ambiguity.append('JURISDICTION_UNRESOLVED')
    return ResearchContext(subject, agent, tuple(dict.fromkeys(tasks)), tuple(scores), subject_type, aliases,
                           country, language, window, max(scores.values(), default=.0), tuple(ambiguity),
                           'REQUEST_AND_OBSERVED_TITLE_CUES' if observations_used else 'DETERMINISTIC_REQUEST_CUES', scores)
