/**
 * Contract tests for Claim Intelligence Core frontend components:
 * - Module A: Allegation vs. Evidence Matrix
 * - Module B: Corroboration Illusion Detector & Source Independence Graph
 */
const assert = require('assert');
const {
  renderUnifiedReport,
  renderAllegationMatrix,
  renderCorroborationIllusion,
} = require('../../frontend/unified-report-renderer.js');

function createMockContainer() {
  return {
    innerHTML: '',
    querySelector: () => null,
    querySelectorAll: () => [],
    parentElement: null,
  };
}

console.log('--- TEST 1: Allegation vs. Evidence Matrix 6-State Rendering ---');
const sampleMatrixReport = {
  summary: 'Investigation of circulating product recall claims.',
  allegation_matrix: [
    {
      claim: {
        claim_id: 'clm_1',
        raw_allegation: 'Company X recalled all products today due to contamination.',
        target_entity: 'Company X',
        predicate: 'recalled',
        subject_scope: 'global_or_universal',
        temporal_scope: 'today',
        extracted_qualifiers: ['alleged'],
      },
      verdict: 'MISLEADING_CONTEXT',
      confidence: 0.82,
      allegation_summary: 'Allegation asserts that Company X recalled all products today.',
      verified_record_summary: 'An older 2021 recall was located. Checked FDA registries show zero recall today.',
      supporting_links: [],
      contradicting_links: [],
      corporate_denials: [
        {
          link_id: 'elk_denial_1',
          claim_id: 'clm_1',
          source_id: 'src_pr',
          source_url: 'https://companyx.com/pr',
          publisher: 'Company X PR',
          passage_text: 'Company X strongly denies reports of a nationwide recall.',
          passage_offsets: [0, 56],
          content_hash: 'd3b07384d113edec49eaa6238ad5ff00',
          stance: 'CONTRADICTS',
          confidence: 0.85,
          is_corporate_denial: true,
          rationale: 'Passage records an explicit corporate denial.',
        },
      ],
      deceptive_framing_flags: ['OUT_OF_CONTEXT_MEDIA'],
      registries_checked: ['FDA Enforcement Database', 'SEC EDGAR'],
      action_advisory: 'CONTEXT WARNING: Do not share without clarifying that past events are being presented out of context.',
    },
  ],
};

const matrixHtml = renderAllegationMatrix(sampleMatrixReport);
assert(matrixHtml.includes('ALLEGATION VS. EVIDENCE MATRIX'), 'Section header must render');
assert(matrixHtml.includes('Circulating Allegation'), 'Allegation column must render');
assert(matrixHtml.includes('Verified Record'), 'Record column must render');
assert(matrixHtml.includes('OUT OF CONTEXT MEDIA'), 'Deceptive framing flag must render');
assert(matrixHtml.includes('FDA Enforcement Database'), 'Checked registry must render');
assert(matrixHtml.includes('CORPORATE DENIAL'), 'Corporate denial badge must render');
assert(matrixHtml.includes('evidence of denial, not proof of falsity'), 'Corporate denial disclaimer must render');
console.log('✓ Allegation vs. Evidence Matrix verified with corporate denial and deceptive framing flags');

console.log('--- TEST 2: Corroboration Illusion Detector & Source Independence Graph ---');
const sampleCorrobReport = {
  summary: 'Investigation of viral report.',
  corroboration_summary: {
    total_sources_scanned: 12,
    unique_publishers: 8,
    independent_evidence_chains: 1,
    syndicated_reprints_count: 11,
    corroboration_illusion_detected: true,
    corroboration_ratio: 0.12,
    warning_message: 'CORROBORATION ILLUSION DETECTED: 8 publishers share 1 origin.',
    groups: [
      {
        group_id: 'grp_1',
        primary_origin_publisher: 'Original Investigative Blog',
        primary_origin_url: 'https://originblog.local/post',
        reprint_publishers: ['Mirror Wire', 'Viral Aggregator', 'Tech Repost', 'Social Clip'],
        all_source_ids: ['src_1', 'src_2', 'src_3', 'src_4', 'src_5'],
        is_independent: false,
        syndication_ratio: 0.8,
      },
    ],
  },
};

const corrobHtml = renderCorroborationIllusion(sampleCorrobReport);
assert(corrobHtml.includes('SOURCE INDEPENDENCE &amp; CORROBORATION ILLUSION AUDIT'), 'Header must render');
assert(corrobHtml.includes('Corroboration Illusion Detected'), 'Illusion alert must render');
assert(corrobHtml.includes('12'), 'Scanned count must render');
assert(corrobHtml.includes('8'), 'Unique publishers must render');
assert(corrobHtml.includes('Original Investigative Blog'), 'Origin publisher must render');
assert(corrobHtml.includes('Mirror Wire'), 'Reprint publisher must render');
console.log('✓ Corroboration Illusion Detector verified with echo-chamber alert and syndication graph');

console.log('--- TEST 3: Full Unified Report Integration ---');
const fullReport = {
  summary: 'Full investigation overview.',
  findings: ['Primary assertion unverified.'],
  evidence: { primary: [], independent: [], community: [] },
  allegation_matrix: sampleMatrixReport.allegation_matrix,
  corroboration_summary: sampleCorrobReport.corroboration_summary,
};

const container = createMockContainer();
renderUnifiedReport(container, fullReport);
assert(container.innerHTML.includes('ALLEGATION VS. EVIDENCE MATRIX'), 'Unified report must include matrix');
assert(container.innerHTML.includes('SOURCE INDEPENDENCE &amp; CORROBORATION ILLUSION AUDIT'), 'Unified report must include corroboration audit');
console.log('✓ Full Unified Report renders Claim Intelligence Core sections');

console.log('\nALL CLAIM INTELLIGENCE FRONTEND CONTRACT TESTS PASSED (3/3)!');
