"""Aggregate word/depth claims must never become confirmed research metrics."""
from scripts.audits.reconcile_saved_benchmark import dossier_metrics, subject_matches
import hashlib


def test_depth_claim_and_sealed_snippet_do_not_establish_six_reads_or_articles():
    text='Aster Quinn was mentioned in a publisher headline.'
    data={'target':'Aster Quinn','summary':'with 6 deep-read primary documents',
          'candidate_snapshots':{'saved':{'content':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}},
          'source_lineage':{'nodes':[{'id':'saved','url':'https://publisher.example/story'}]},
          'findings_provenance':[{'supporting_evidence_ids':['saved','missing']}]}
    result=dossier_metrics(data)
    assert result['summary_reported_document_count_NOT_attempts']==6
    assert result['actual_read_attempts'] is None and result['article_bodies_actually_acquired'] is None
    assert result['deduplicated_relevant_passage_words'] is None
    assert result['all_snapshot_hashes_match']
    assert result['references_with_snapshot_and_url']==1 and result['citation_references']==2


def test_subject_matching_preserves_name_boundaries_and_explicit_ticker_alias():
    assert subject_matches('Example Corporation (EXM)','EXM')
    assert not subject_matches('Another Example Company','EXM')
    assert not subject_matches('Aster Quinn Jr','Aster Quinn')
