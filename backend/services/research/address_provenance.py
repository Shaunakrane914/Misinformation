"""Bounded publisher-observed speech scope; never identity authentication."""
import hashlib
import re
from urllib.parse import urlsplit


EDITORIAL_BASIS = 'OBSERVED_AUTHOR_AND_EDITORIAL_ADDRESS_INTRODUCTION'
GOVUK_BASIS = 'CAPTURED_GOVUK_CONTENT_API_SPEECH_SPEAKER'


def speaker_matches(speaker, target):
    def name(value):
        value = ' '.join(value.casefold().split())
        value = re.sub(r'^(?:the\s+)?(?:rt\.?\s+hon\.?\s+)', '', value)
        value = re.sub(r'^(?:sir|dame|dr\.?)\s+', '', value)
        return re.sub(r'(?:\s+(?:mp|kc|kcb|cbe|obe|mbe))+$', '', value)
    return bool(target and name(speaker) == name(target))


def project_statement_metadata(value):
    """Keep issuing/publication context even when speaker attribution is absent."""
    if not isinstance(value, dict) or value.get('publisher') != 'GOV.UK':
        return None
    result = {'publisher':'GOV.UK', 'identity_authenticated':False}
    for key in ('speaker','delivered_on','first_published_at'):
        if isinstance(value.get(key),str):
            result[key] = value[key][:200]
    if isinstance(value.get('issuing_organisations'),list):
        result['issuing_organisations'] = [name[:200] for name in value['issuing_organisations'][:8] if isinstance(name,str)]
    return result


def project_address(address, body):
    if (not isinstance(address, dict) or not isinstance(body, str)
            or address.get('source_text_sha256') != hashlib.sha256(body.encode('utf-8')).hexdigest()
            or not isinstance(address.get('speaker'), str) or not 1 <= len(address['speaker']) <= 150
            or not all(type(address.get(k)) is int for k in ('start', 'end'))
            or not 0 <= address['start'] < address['end'] <= len(body)):
        return None
    basis = address.get('basis')
    if basis == EDITORIAL_BASIS:
        if (not all(type(address.get(k)) is int for k in ('intro_start', 'intro_end'))
                or not 0 <= address['intro_start'] < address['intro_end'] <= address['start']):
            return None
    elif basis == GOVUK_BASIS:
        try:
            parsed = urlsplit(str(address.get('source_api_url') or ''))
        except ValueError:
            return None
        if (address.get('document_type') != 'speech'
                or address.get('speaker_basis') not in {'links.speaker', 'details.speaker_without_profile'}
                or parsed.scheme != 'https' or parsed.netloc != 'www.gov.uk'
                or not parsed.path.startswith('/api/content/government/speeches/') or parsed.query or parsed.fragment):
            return None
    else:
        return None
    result = {key:address[key] for key in ('speaker', 'start', 'end', 'source_text_sha256', 'basis')}
    for key in ('intro_start', 'intro_end'):
        if type(address.get(key)) is int:
            result[key] = address[key]
    for key in ('publisher', 'speaker_basis', 'speaker_profile_url', 'delivered_on', 'first_published_at',
                'source_api_url', 'api_response_sha256', 'document_type'):
        if isinstance(address.get(key), str):
            result[key] = address[key][:1000]
    organisations = address.get('issuing_organisations')
    if isinstance(organisations, list):
        result['issuing_organisations'] = [name[:200] for name in organisations[:8] if isinstance(name, str)]
    result['identity_authenticated'] = False
    return result
