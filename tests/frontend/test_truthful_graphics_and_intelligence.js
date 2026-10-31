'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

const IntelligenceTransformer = require(path.resolve(__dirname, '../../frontend/intelligence-transformer.js'));
const AegisGraphs = require(path.resolve(__dirname, '../../frontend/aegis-graphs.js'));

function mount() {
  return { innerHTML: '', querySelectorAll: () => [] };
}

console.log('--- TEST 1: Channel Dispersion Object Evidence & Hostname Matching ---');
// 1. Channel dispersion handles object-shaped evidence { primary: [...], independent: [...] }
const sampleData = {
  evidence: {
    primary: [
      { url: 'https://www.sec.gov/edgar/data/1318605/filing.htm', publisher: 'SEC EDGAR' }
    ],
    independent: [
      { url: 'https://netflix.com/press-release', domain: 'netflix.com' }, // Must NOT be counted as social!
      { url: 'https://fedex.com/news', domain: 'fedex.com' }, // Must NOT be counted as social!
      { url: 'https://twitter.com/elonmusk/status/12345', domain: 'twitter.com' }
    ],
    community: [
      { url: 'https://reddit.com/r/teslamotors/comments/abc', domain: 'reddit.com' }
    ]
  }
};

const enriched = IntelligenceTransformer.enrich(sampleData);
assert.equal(enriched.channel_dispersion.total_items, 5);
// Counts: regulatory: 1 (20%), social: 2 (40%: twitter + reddit; netflix and fedex are web!), web: 2 (40%)
assert.equal(enriched.channel_dispersion.regulatory_pct, 20);
assert.equal(enriched.channel_dispersion.social_pct, 40);
assert.equal(enriched.channel_dispersion.web_pct, 40);
console.log('✓ Channel dispersion correctly normalizes object-shaped evidence without false social hits');

console.log('--- TEST 2: Catalysts Governance Invariant ---');
// Heuristic keyword catalysts must NEVER overwrite or synthesize data.catalysts
const noCatalystsData = {
  evidence: [
    { text: 'Revenue rose strongly this quarter but fraud investigations continue.', url: 'https://example.com' }
  ]
};
const result = IntelligenceTransformer.enrich(noCatalystsData);
assert.deepEqual(result.catalysts, { positive: [], negative: [], unresolved: [] });
assert.ok(result.client_derived);
assert.ok(Array.isArray(result.client_derived.heuristic_catalysts.positive));
assert.ok(Array.isArray(result.client_derived.heuristic_catalysts.negative));
// Check no fake evidence_ids in heuristic catalysts
for (const cat of result.client_derived.heuristic_catalysts.negative) {
  assert.equal(cat.evidence_ids, undefined, 'Must not invent fake evidence_ids');
}
console.log('✓ Catalysts invariant preserved: backend data.catalysts remains untainted');

console.log('--- TEST 3: Volatility Chart Truthful Filtering & Empirical Dispersion ---');
const volMount = mount();
// Filter out null, non-numeric, or missing values
AegisGraphs.renderVolatilityChart(volMount, {
  history: [
    { val: 'invalid' },
    { val: null },
    { val: 100, time: 'T1' },
    { val: 120, time: 'T2' },
    { val: 110, time: 'T3' }
  ]
});
assert(volMount.innerHTML.includes('Base: <strong style="color:#fff;">$100.00</strong>'));
assert(volMount.innerHTML.includes('Current: <strong style="color:var(--emerald);">$110.00</strong>'));
assert(volMount.innerHTML.includes('// EMPIRICAL DISPERSION BAND (MEAN ± 1.5σ)'));

// Empty state on fewer than 2 valid points
const volEmptyMount = mount();
AegisGraphs.renderVolatilityChart(volEmptyMount, {
  history: [{ val: null }, { val: 'bad' }, { val: 50 }]
});
assert(volEmptyMount.innerHTML.includes('INSUFFICIENT HISTORICAL OBSERVATIONS'));
console.log('✓ Volatility chart strictly filters non-finite points and computes empirical dispersion');

console.log('--- TEST 4: 6-Axis Epistemic Tensor Missing Axis Handling ---');
const radarMount = mount();
AegisGraphs.renderEpistemicRadar(radarMount, {
  relevance: 0.8,
  source_quality: 0.9,
  independence: null, // Absent measurement
  primary_weight: undefined, // Absent measurement
  freshness: 0.7,
  contradiction: 0.2 // Resilience = 1.0 - 0.2 = 0.8
});
// 4 assessed axes: (0.8 + 0.9 + 0.7 + 0.8) / 4 = 3.2 / 4 = 80%
assert(radarMount.innerHTML.includes('Mean Epistemic Score: <strong style="color:#c4b5fd;">80%</strong>'));
assert(radarMount.innerHTML.includes('Independence (n/a)'));
assert(radarMount.innerHTML.includes('Primary Weight (n/a)'));
assert(radarMount.innerHTML.includes('4/6 ASSESSED'));
console.log('✓ Epistemic radar correctly treats missing axes as n/a and excludes them from mean score');

console.log('--- TEST 5: Hawkes Velocity Empty States & Trajectory Guard ---');
const hawkesNonFiniteMount = mount();
AegisGraphs.renderHawkesVelocity(hawkesNonFiniteMount, { r0: 'invalid_nan' });
assert(hawkesNonFiniteMount.innerHTML.includes('INSUFFICIENT TEMPORAL VELOCITY OBSERVATIONS'));

const hawkesScalarMount = mount();
AegisGraphs.renderHawkesVelocity(hawkesScalarMount, { r0: 1.45 });
// Without arrivals, must render honest scalar metric panel and omit synthetic sin() curve
assert(hawkesScalarMount.innerHTML.includes('OBSERVED BRANCHING RATIO R₀'));
assert(hawkesScalarMount.innerHTML.includes('1.45'));
assert(hawkesScalarMount.innerHTML.includes('SUPER-CRITICAL CASCADE'));
assert(!hawkesScalarMount.innerHTML.includes('T-48h'), 'Must not render hardcoded time labels when unobserved');
assert(!hawkesScalarMount.innerHTML.includes('<svg'), 'Must not render synthetic SVG curve without arrival data');
console.log('✓ Hawkes velocity renders honest scalar metrics without fabricated trajectories');

console.log('--- TEST 6: Identity Threat Gauge Assessed Clamping & Safe Empty State ---');
const threatEmptyMount = mount();
AegisGraphs.renderIdentityThreatGauge(threatEmptyMount, {});
assert(threatEmptyMount.innerHTML.includes('No assessments recorded; this is not evidence of safety.'));

const threatPartialMount = mount();
AegisGraphs.renderIdentityThreatGauge(threatPartialMount, {
  deepfake: 75,
  impersonation: null, // Unassessed
  doxxing: 120, // Clamped to 100
  smear: null // Unassessed
});
assert(threatPartialMount.innerHTML.includes('ELEVATED THREAT DETECTED'));
assert(threatPartialMount.innerHTML.includes('75%'));
assert(threatPartialMount.innerHTML.includes('100%'));
assert(threatPartialMount.innerHTML.includes('Not assessed'));
console.log('✓ Identity threat gauge clamps assessed values and honestly renders unassessed vectors');

console.log('\nALL TRUTHFUL GRAPHICS AND INTELLIGENCE TESTS PASSED!');

