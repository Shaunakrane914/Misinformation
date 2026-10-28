"""Regressions for a genuine live controlled-source routing crash; no HTTP."""
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.research_models import EvidenceItem


def controlled(metadata=None):
    return EvidenceItem(id='observed-source', canonical_url='https://globalvoices.org/observed',
        title='Observed report', content='The council announced new eligibility rules and published its statement.',
        content_depth='PARTIAL_CONTENT', metadata={'topic_source_controlled': True,
            'source_family': 'global_voices', 'read_success': True,
            'specialist_tasks': ['PUBLIC_STATEMENT'], **(metadata or {})})


def test_candidate_preserves_scalar_routing_without_crashing():
    pool = RawAcquisitionPool('scalar-routing')
    identity = pool.add_candidate(controlled())
    row = pool.get(identity)
    assert row['topic_source_controlled'] is True
    assert row['source_family'] == 'global_voices'
    assert row['specialist_tasks'] == ['PUBLIC_STATEMENT']


def test_duplicate_candidates_merge_tasks_but_keep_family_as_string():
    pool = RawAcquisitionPool('duplicate-routing')
    identity = pool.add_candidate(controlled())
    pool.add_candidate(controlled({'specialist_tasks': ['IDENTITY_THREAT']}))
    row = pool.get(identity)
    assert row['source_family'] == 'global_voices'
    assert row['topic_source_controlled'] is True
    assert row['specialist_tasks'] == ['PUBLIC_STATEMENT', 'IDENTITY_THREAT']


def test_controlled_capture_keeps_permissions_after_export_and_restore():
    pool = RawAcquisitionPool('capture-routing')
    pool.add_capture(controlled())
    restored = RawAcquisitionPool.from_export(pool.export())
    item, = restored.to_evidence_items()
    assert item.metadata['topic_source_controlled'] is True
    assert item.metadata['source_family'] == 'global_voices'
    assert item.content == controlled().content
