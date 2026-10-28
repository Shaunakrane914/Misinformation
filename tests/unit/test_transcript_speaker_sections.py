"""Observed transcript labels identify source attribution, never authenticated identity."""
import hashlib
import json
from pathlib import Path

from backend.services.research.research_models import EvidenceItem
from backend.services.research.passage_records import public_statement_attribution, captured_passages
from backend.services.research.passage_extractor import PassageExtractor
from backend.services.research.content_roles import paragraph_role


def record(body, author=''):
    return EvidenceItem(id='speaker_fixture', canonical_url='https://publisher.example/transcript',
        title='Public event transcript',source_name=author,content=body,content_depth='PARTIAL_CONTENT',
        metadata={'read_success':True,'layer2_eligible':True,'acquisition_objective':'PUBLIC_STATEMENT',
                  'page_metadata':{'body_kind':'ARTICLE_BODY'}})


def test_speaker_roster_does_not_attribute_an_editorial_intro():
    intro='Here is the full transcript of the event where Dana Vale and other executives spoke.'
    body='Speakers at the event:\n\nDana Vale – CEO, Example\n\nOther Person – Director\n\n'+intro
    item=record(body)
    assert public_statement_attribution(item,intro,'Dana Vale') is None
    assert paragraph_role(intro)=='TRANSCRIPT_INTRODUCTION'
    assert not any(p['content_role']=='PUBLIC_STATEMENT' for p in captured_passages(item,'personal','Dana Vale'))


def test_explicit_transcript_section_stops_at_next_speaker_even_with_feed_author():
    dana='We will publish our research findings in the coming weeks. Our laboratory has completed the initial review.'
    other='Our organization will separately review these proposals before making a decision.'
    body='TRANSCRIPT:\n\nDana Vale – CEO, Example\n\n'+dana+'\n\nRobin Lane – Director\n\n'+other
    item=record(body,author='Dana Vale')
    assert public_statement_attribution(item,dana,'Dana Vale')=='OBSERVED_TRANSCRIPT_SPEAKER_SECTION'
    assert public_statement_attribution(item,other,'Dana Vale') is None
    assert public_statement_attribution(item,other,'Robin Lane')=='OBSERVED_TRANSCRIPT_SPEAKER_SECTION'


def test_inline_next_speaker_label_cannot_borrow_preceding_speaker():
    body='TRANSCRIPT:\n\nDana Vale – CEO, Example\n\nWe will report results.\n\nRobin Lane: We will review the proposals separately.'
    item=record(body)
    assert public_statement_attribution(item,'Robin Lane: We will review the proposals separately.','Dana Vale') is None


def test_titled_transcript_with_honorifics_times_and_editorial_intro():
    intro = 'The following is the full transcript of Dana Vale interviewing another researcher.'
    notes = 'EDITOR\u2019S NOTES: Dana Vale discusses the research in this interview.'
    answer = 'DR. DANA VALE: (00:04:25 - 00:12:12): We have not established the result. Further research is necessary before drawing conclusions.'
    host = 'ROBIN LANE: (00:12:13 - 00:12:40): Dana Vale, what are the research limitations?'
    body = '\n\n'.join(['Transcript of Dr. Dana Vale Interview', intro, notes,
        'ROBIN LANE: Welcome to the interview with Dana Vale.', answer, host])
    item = record(body, author='Dana Vale')
    assert public_statement_attribution(item, answer, 'Dana Vale') == 'OBSERVED_TRANSCRIPT_SPEAKER_SECTION'
    for text in (intro, notes, host):
        assert public_statement_attribution(item, text, 'Dana Vale') is None
    PassageExtractor().extract_passages([item], 'Dana Vale', domain='personal')
    assert item.relevant_excerpt == answer
    assert [p['text'] for p in item.metadata['evidence_passages']] == [answer]
    assert [p['text'] for p in captured_passages(item, 'personal', 'Dana Vale')] == [answer]
    assert item.content == body


def test_transcript_roster_without_repeated_colon_turns_is_not_speaker_evidence():
    body = 'Transcript interview participants\n\nDana Vale - CEO\n\nRobin Lane - Host\n\nThis interview features Dana Vale.'
    item = record(body)
    assert public_statement_attribution(item, 'This interview features Dana Vale.', 'Dana Vale') is None


def test_genuine_saved_honorific_transcript_found_by_threat_query():
    source=json.loads((Path(__file__).parent/'fixtures/oct28_fei_transcript_turn_capture.json').read_text(encoding='utf-8'))
    body=source['readable_text']
    assert hashlib.sha256(body.encode()).hexdigest()==source['prefix_sha256']
    item=record(body)
    item.metadata['acquisition_objective']='IDENTITY_THREAT'
    PassageExtractor().extract_passages([item], 'Fei-Fei Li', domain='personal')
    assert item.extraction_status=='SUCCESS'
    assert item.metadata['evidence_passages']
    assert all(p['attribution']=='OBSERVED_TRANSCRIPT_SPEAKER_SECTION' for p in item.metadata['evidence_passages'])
    assert all(body[p['start']:p['end']]==p['text'] for p in item.metadata['evidence_passages'])
    assert not any('EDITOR' in p['text'] or p['text'].startswith('The following') for p in item.metadata['evidence_passages'])
    assert item.content==body
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    native = {'evidence_id': item.id, 'title': item.title, 'url': item.canonical_url,
              'content': body, 'content_depth': item.content_depth, 'metadata': item.metadata}
    result = synthesize_personal_threats({'canonical_name':'Fei-Fei Li'}, [native])
    assert result['public_statements'] and not result['threats']
    assert all(not p['identity_authenticated'] for p in result['public_statements'])
    item.metadata['page_metadata']['body_kind']='NEWS_INDEX'
    assert public_statement_attribution(item,item.relevant_excerpt,'Fei-Fei Li') is None


def test_merged_multi_speaker_paragraph_cannot_borrow_one_speakers_attribution():
    paragraph = 'DR. DANA VALE: We have not confirmed the result.\nROBIN LANE: I believe the result is confirmed.'
    body = 'Transcript of interview\n\nROBIN LANE: Welcome to this interview.\n\n' + paragraph
    assert public_statement_attribution(record(body), paragraph, 'Dana Vale') is None


def test_genuine_tim_cook_capture_selects_exact_spoken_paragraphs_not_intro():
    source=json.loads((Path(__file__).parent/'fixtures/oct25_tim_cook_transcript_capture.json').read_text(encoding='utf-8'))['source']
    body=source['readable_text'];assert hashlib.sha256(body.encode()).hexdigest()==source['raw_content_hash']
    item=record(body)
    PassageExtractor().extract_passages([item],'Tim Cook',domain='personal')
    assert item.relevant_excerpt and not item.relevant_excerpt.startswith('Following is the full transcript')
    assert public_statement_attribution(item,item.relevant_excerpt,'Tim Cook')=='OBSERVED_TRANSCRIPT_SPEAKER_SECTION'
    assert item.metadata['evidence_passages']
    assert all(p['content_role']=='PUBLIC_STATEMENT' and p['attribution']=='OBSERVED_TRANSCRIPT_SPEAKER_SECTION'
               for p in item.metadata['evidence_passages'])
    passages=[p for p in captured_passages(item,'personal','Tim Cook') if p['content_role']=='PUBLIC_STATEMENT']
    assert passages
    assert all(body[p['start']:p['end']]==p['text'] for p in passages)
    assert item.content==body and hashlib.sha256(item.content.encode()).hexdigest()==source['raw_content_hash']


def test_saved_workbench_rebuild_preserves_original_and_does_not_copy_old_findings():
    from copy import deepcopy
    from scripts.audits.rebuild_saved_workbench import rebuild_payload
    source=json.loads((Path(__file__).parent/'fixtures/oct25_tim_cook_transcript_capture.json').read_text(encoding='utf-8'))['source']
    pool={'schema_version':'raw-acquisition-pool-v1','investigation_id':'saved-transcript-control',
          'created_at':'2026-10-25T17:00:00+00:00','sources':[source]}
    payload={'research_corpus':{'raw_acquisition_pool':pool},'unified_report':{'findings':['old projection']}}
    original=deepcopy(payload)
    result=rebuild_payload(payload,'Tim Cook','personal','personal_watch')
    assert payload==original
    assert result['unified_report']['findings']==[]
    assert result['new_network_calls']==result['model_calls']==0
    assert result['unified_report']['evidence_workbench']['passages']
    assert all(p['attribution']=='OBSERVED_TRANSCRIPT_SPEAKER_SECTION'
               for p in result['unified_report']['evidence_workbench']['passages'])
