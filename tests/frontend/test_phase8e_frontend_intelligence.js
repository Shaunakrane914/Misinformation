'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { renderUnifiedReport } = require(
  path.resolve(__dirname, '../../frontend/unified-report-renderer.js')
);

function createTestMount() {
  const listeners = {};
  return {
    innerHTML: '',
    querySelectorAll: () => [],
    querySelector: (selector) => {
      return {
        addEventListener: (event, cb) => { listeners[event] = cb; },
        click: () => { if (listeners['click']) listeners['click'](); }
      };
    }
  };
}

console.log('--- TEST 1: All 7 Non-Binary Epistemic Verdicts ---');
const verdicts = [
  'SUPPORTED', 'REFUTED', 'MISLEADING', 'OUTDATED', 'MIXED', 'UNVERIFIED', 'INSUFFICIENT_EVIDENCE'
];

for (const v of verdicts) {
  const mount = createTestMount();
  renderUnifiedReport(mount, {
    summary: `Claim is **${v}**.`,
    verdict: { verdict: v, confidence: 0.92, reasoning: `Reasoning for ${v}` }
  });
  const expectedClass = v === 'INSUFFICIENT_EVIDENCE' ? 'ur-verdict--insufficient' : `ur-verdict--${v.toLowerCase().replace('_', '-')}`;
  assert(mount.innerHTML.includes(expectedClass), `Missing CSS class for ${v}`);
  assert(mount.innerHTML.includes('Model Confidence: <strong>92%</strong>'));
  assert(mount.innerHTML.includes(`Reasoning for ${v}`));
}
console.log('✓ All 7 non-binary verdict states verified');

console.log('--- TEST 2: Claim Decomposition Multi-Premise Sub-claims ---');
for (const unknown of ['UNSUPPORTED', 'NOT_SUPPORTED', 'NOT_REFUTED']) {
  const mount = createTestMount();
  renderUnifiedReport(mount, { verdict: { verdict: unknown } });
  assert(!mount.innerHTML.includes('ur-verdict--supported'), unknown);
  assert(!mount.innerHTML.includes('ur-verdict--refuted'), unknown);
}
{
  const mount = createTestMount();
  renderUnifiedReport(mount, {
    summary: 'Multi-premise claim under review',
    claim_decomposition: [
      {
        claim_text: 'Acme Corp acquired Beta Ltd for $2B',
        verdict: 'SUPPORTED',
        confidence: 0.95,
        reasoning: 'Confirmed via 8-K regulatory disclosure.',
        evidence_citations: ['https://sec.gov/edgar/data/12345/0001']
      },
      {
        claim_text: 'CEO resigned immediately following announcement',
        verdict: 'REFUTED',
        confidence: 0.89,
        reasoning: 'Corporate governance disclosure confirms CEO remains in position.',
        evidence_citations: ['https://acme.com/press-release']
      }
    ]
  });
  assert(mount.innerHTML.includes('CLAIM DECOMPOSITION'));
  assert(mount.innerHTML.includes('Acme Corp acquired Beta Ltd for $2B'));
  assert(mount.innerHTML.includes('CEO resigned immediately following announcement'));
  assert(mount.innerHTML.includes('href="https://sec.gov/edgar/data/12345/0001"'));
  assert(mount.innerHTML.includes('ur-verdict--supported'));
  assert(mount.innerHTML.includes('ur-verdict--refuted'));
}
console.log('✓ Claim decomposition multi-premise verified');

console.log('--- TEST 3: Multi-Dimensional 5D Contradiction Cards ---');
{
  const mount = createTestMount();
  renderUnifiedReport(mount, {
    summary: 'Conflicting corporate rumor',
    contradictions: [
      {
        type: 'NUMERICAL_DISCREPANCY',
        severity: 'CRITICAL',
        statement_a: 'Company reported Q3 revenue of $450M in social report',
        source_a: 'Viral X Cashtag Analysis',
        statement_b: 'Official 10-Q filing documents Q3 revenue as $310M',
        source_b: 'SEC EDGAR 10-Q Item 2',
        explanation: 'Factual discrepancy of $140M between viral post and audited filing.'
      },
      {
        type: 'TEMPORAL_DIVERGENCE',
        severity: 'MODERATE',
        statement_a: 'Product launch is indefinitely postponed',
        source_a: 'Forum Thread',
        statement_b: 'Product launched 6 months ago on schedule',
        source_b: 'Official Changelog',
        explanation: '2024 discussion recirculated in 2026 as current news.'
      }
    ]
  });
  assert(mount.innerHTML.includes('WHAT DISAGREES?'));
  // Type/severity strings without paired captured passages are review leads.
  assert(mount.innerHTML.includes('POSSIBLE DISAGREEMENT'));
  assert(mount.innerHTML.includes('UNASSESSED'));
  assert(!mount.innerHTML.includes('ur-contra-sev ur-sev--critical'));
  assert(mount.innerHTML.includes('Proposition A [Viral X Cashtag Analysis]:'));
  assert(mount.innerHTML.includes('Proposition B [SEC EDGAR 10-Q Item 2]:'));
  assert(mount.innerHTML.includes('Factual discrepancy of $140M'));
}
console.log('✓ 5-dimensional contradiction cards verified');

console.log('--- TEST 4: Authoritative Source Badges (SEC EDGAR, NIST, arXiv, ClaimReview) ---');
{
  const mount = createTestMount();
  renderUnifiedReport(mount, {
    summary: 'Authoritative multi-source investigation',
    evidence: {
      primary: [
        {
          title: 'Form 10-K Annual Report',
          url: 'https://sec.gov/edgar/data/123/001.htm',
          source: { name: 'SEC EDGAR', authority: 'STATUTORY_REGULATOR', reliability: 0.99, is_primary: true }
        },
        {
          title: 'CVE-2026-10492 Security Advisory',
          url: 'https://nvd.nist.gov/vuln/detail/CVE-2026-10492',
          source: { name: 'NIST NVD', authority: 'NATIONAL_VULNERABILITY_DATABASE', reliability: 0.98, is_primary: true }
        }
      ],
      independent: [
        {
          title: 'Neural Fact Verification Architecture',
          url: 'https://arxiv.org/abs/2603.18942',
          source: { name: 'arXiv Preprints', authority: 'PEER_PREPRINT_ARCHIVE', reliability: 0.88 }
        },
        {
          title: 'Fact Check: Disinformation Claim Review',
          url: 'https://politifact.com/factchecks/2026/01',
          source: { name: 'PolitiFact', authority: 'FACT_CHECK_ORGANIZATION', reliability: 0.94 }
        }
      ],
      community: []
    }
  });
  assert(mount.innerHTML.includes('SEC EDGAR · Regulator'));
  assert(mount.innerHTML.includes('NIST NVD · Security'));
  assert(mount.innerHTML.includes('arXiv · Preprint'));
  assert(mount.innerHTML.includes('ClaimReview · Fact Check'));
  assert(mount.innerHTML.includes('Heuristic source score: 99%'));
  assert(mount.innerHTML.includes('Heuristic source score: 88%'));
}
console.log('✓ Authoritative source badges verified');

console.log('--- TEST 5: Agent Specialized Intelligence Modules ---');
{
  const mount = createTestMount();
  renderUnifiedReport(mount, {
    summary: 'Agent intelligence report',
    // Synthetic render contract, not observed research or a source-authenticity test.
    evidence: { primary: [{ title: 'Synthetic captured report', extraction: {
      evidentiary_use: 'REQUIRES_PASSAGE_REVIEW', content_depth: 'PARTIAL_CONTENT'
    } }] },
    agent_intelligence: {
      filing_comparison: {
        status: 'ANOMALIES_DETECTED', comparisons: [{ metric: 'Revenue' }],
        discrepancy_detected: true,
        discrepancies: [
          { metric: 'Revenue', filing_value: '$100M', reported_value: '$500M', variance: '+400%' }
        ]
      },
      bot_amplification: {
        measurement_basis: 'OBSERVED_POST_SAMPLE', observed_post_count: 3,
        bot_risk_score: 0.87,
        coordination_patterns: ['Synchronized burst posting', 'Near-identical semantic embeddings']
      },
      narrative_velocity: {
        measurement_basis: 'OBSERVED_TIME_SERIES', observation_count: 3,
        velocity_score: 0.78,
        doubling_time_hours: 3.5
      },
      executive_impersonation: {
        is_impersonation_suspected: true
      },
      smear_analysis: {
        classification: 'SMEAR_CAMPAIGN'
      },
      identity_verification: {
        is_identity_matched: true
      },
      doxxing_exposure: {
        doxxing_risk_level: 'CRITICAL'
      },
      quote_attribution: {
        attribution_status: 'FABRICATED'
      }
    }
  });
  assert(mount.innerHTML.includes('SPECIALIZED AGENT INTELLIGENCE'));
  assert(mount.innerHTML.includes('Reported numerical discrepancy'));
  assert(mount.innerHTML.includes('Variance: +400%'));
  assert(mount.innerHTML.includes('Bot Risk Score'));
  assert(mount.innerHTML.includes('87%'));
  assert(mount.innerHTML.includes('Doubling Time'));
  assert(mount.innerHTML.includes('3.5h'));
  assert(mount.innerHTML.includes('Impersonation Risk'));
  assert(mount.innerHTML.includes('SMEAR_CAMPAIGN'));
  assert(mount.innerHTML.includes('Catalog Identity Match'));
  assert(mount.innerHTML.includes('CATALOG MATCH — NOT IDENTITY VERIFICATION'));
  assert(mount.innerHTML.includes('FABRICATED'));
}
console.log('✓ Agent specialized intelligence modules verified');

console.log('--- TEST 6: XSS Safety Across All New Components ---');
{
  const xssAttack = '<img src=x onerror=alert(1)>';
  const mount = createTestMount();
  renderUnifiedReport(mount, {
    summary: `Summary ${xssAttack}`,
    claim_decomposition: [{
      claim_text: `Claim ${xssAttack}`,
      verdict: 'SUPPORTED',
      reasoning: `Reason ${xssAttack}`,
      evidence_citations: ['javascript:alert(1)']
    }],
    contradictions: [{
      type: xssAttack,
      statement_a: xssAttack,
      source_a: xssAttack,
      statement_b: xssAttack,
      source_b: xssAttack,
      explanation: xssAttack
    }],
    agent_intelligence: {
      bot_amplification: {
        coordination_patterns: [xssAttack]
      }
    }
  });
  assert(!mount.innerHTML.includes(xssAttack));
  assert(!mount.innerHTML.includes('<img'));
  assert(!mount.innerHTML.includes('href="javascript:'));
  assert(mount.innerHTML.includes('&lt;img src=x onerror=alert(1)&gt;'));
}
console.log('✓ XSS sanitization verified across all Phase 8E modules');

console.log('\nALL PHASE 8E FRONTEND INTELLIGENCE TESTS PASSED!');
