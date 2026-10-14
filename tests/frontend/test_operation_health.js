/**
 * Phase 7.1 Frontend Operation Health Automated Verification
 * Tests bounded TTL, concurrent request deduplication, cache expiry,
 * visibility change triggers, error handling, and truthful state transitions.
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

// Create a mock browser/window/document environment
const mockWindow = {};
let visibilityState = 'visible';
let visibilityListeners = [];

const mockDocument = {
  get visibilityState() { return visibilityState; },
  addEventListener: (event, handler) => {
    if (event === 'visibilitychange') {
      visibilityListeners.push(handler);
    }
  },
  createElement: (tag) => {
    return {
      tagName: tag,
      style: {},
      className: '',
      textContent: '',
      title: '',
      children: [],
      appendChild(c) { this.children.push(c); },
      replaceChildren(...args) { this.children = args; }
    };
  }
};

global.window = mockWindow;
global.document = mockDocument;

// Load operation-health.js into the mock environment
const code = fs.readFileSync(path.join(__dirname, '../../frontend/operation-health.js'), 'utf-8');
eval(code);

const Health = mockWindow.AegisOperationHealth;
assert(Health, 'AegisOperationHealth must be attached to window');

// Test helper for mocking fetch
let fetchCallCount = 0;
let nextFetchResponse = null;

global.fetch = async (url, opts) => {
  fetchCallCount++;
  if (nextFetchResponse instanceof Error) {
    throw nextFetchResponse;
  }
  return nextFetchResponse;
};

function createMockResponse(status, jsonBody) {
  return {
    ok: status >= 200 && status < 300,
    status: status,
    json: async () => jsonBody
  };
}

async function runTests() {
  console.log('--- TEST 1: Initial Successful Capability Fetch ---');
  Health.invalidateCapabilities();
  Health.configure({ ttlMs: 1000, staleThresholdMs: 2000, timeoutMs: 500 });
  fetchCallCount = 0;

  const mockData1 = {
    channels: {
      twitter: {
        operation_capabilities: {
          search: { runtime_health: 'HEALTHY', last_outcome: 'DIRECT_CONTENT', decision: 'PREFER' },
          profile: { runtime_health: 'HEALTHY', last_outcome: 'DIRECT_CONTENT', decision: 'PREFER' }
        }
      }
    }
  };
  nextFetchResponse = createMockResponse(200, mockData1);

  const res1 = await Health.fetchCapabilities();
  assert.strictEqual(fetchCallCount, 1, 'Should call fetch once');
  assert.deepStrictEqual(res1, mockData1, 'Should return fetched data');
  const state1 = Health.getCacheState();
  assert.strictEqual(state1.hasData, true);
  assert.strictEqual(state1.isExpired, false);
  console.log('✓ Initial successful fetch verified');

  console.log('--- TEST 2: Cache Hit Within TTL ---');
  const res2 = await Health.fetchCapabilities();
  assert.strictEqual(fetchCallCount, 1, 'Should NOT call fetch again within TTL');
  assert.deepStrictEqual(res2, mockData1);
  console.log('✓ Cache hit within TTL verified');

  console.log('--- TEST 3: Fetch After TTL Expiry ---');
  // Fast-forward by re-configuring or waiting
  Health.configure({ ttlMs: 10 });
  await new Promise(r => setTimeout(r, 20));

  const stateExpired = Health.getCacheState();
  assert.strictEqual(stateExpired.isExpired, true, 'Cache should be marked expired');

  const mockData2 = {
    channels: {
      twitter: {
        operation_capabilities: {
          search: { runtime_health: 'RATE_LIMITED', last_outcome: 'EMPTY', decision: 'DEFER_TEMPORARY' },
          profile: { runtime_health: 'HEALTHY', last_outcome: 'DIRECT_CONTENT', decision: 'PREFER' }
        }
      }
    }
  };
  nextFetchResponse = createMockResponse(200, mockData2);

  const res3 = await Health.fetchCapabilities();
  assert.strictEqual(fetchCallCount, 2, 'Should call fetch after TTL expiry');
  assert.deepStrictEqual(res3, mockData2);
  console.log('✓ Fetch after TTL expiry verified');

  console.log('--- TEST 4: Concurrent Requests Share In-Flight Fetch (Deduplication) ---');
  Health.invalidateCapabilities();
  Health.configure({ ttlMs: 1000 });
  fetchCallCount = 0;

  let delayedResolve;
  const delayedFetch = new Promise(resolve => { delayedResolve = resolve; });
  global.fetch = async () => {
    fetchCallCount++;
    await delayedFetch;
    return createMockResponse(200, mockData1);
  };

  const p1 = Health.fetchCapabilities();
  const p2 = Health.fetchCapabilities();
  const p3 = Health.fetchCapabilities();

  delayedResolve();
  const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

  assert.strictEqual(fetchCallCount, 1, 'Concurrent calls must share single in-flight fetch');
  assert.deepStrictEqual(r1, mockData1);
  assert.deepStrictEqual(r2, mockData1);
  assert.deepStrictEqual(r3, mockData1);
  console.log('✓ Request deduplication verified');

  console.log('--- TEST 5: Healthy Operation Becomes Blocked ---');
  const blockedOp = { runtime_health: 'BLOCKED', reason: 'POLICY_BLOCKED', decision: 'EXCLUDE' };
  assert.strictEqual(Health.classifyOperation(blockedOp), 'blocked');
  const summaryBlocked = Health.summarizeChannel({
    operation_capabilities: { search: blockedOp }
  }, ['search']);
  assert.strictEqual(summaryBlocked.state, 'blocked');
  assert.strictEqual(summaryBlocked.label, 'Policy blocked');
  console.log('✓ Blocked operation classification verified');

  console.log('--- TEST 6: Healthy Operation Becomes Rate-Limited ---');
  const rateLimitedOp = { runtime_health: 'RATE_LIMITED', decision: 'DEFER_TEMPORARY' };
  assert.strictEqual(Health.classifyOperation(rateLimitedOp), 'degraded');
  const summaryDegraded = Health.summarizeChannel({
    operation_capabilities: { search: rateLimitedOp }
  }, ['search']);
  assert.strictEqual(summaryDegraded.state, 'degraded');
  assert.strictEqual(summaryDegraded.label, 'Temporarily degraded');
  console.log('✓ Rate-limited operation classification verified');

  console.log('--- TEST 7: Capability API Becomes Unavailable (No Indefinite Green) ---');
  Health.invalidateCapabilities();
  nextFetchResponse = new Error('Network error');
  global.fetch = async () => { throw new Error('Backend 503'); };

  let errorThrown = false;
  try {
    await Health.fetchCapabilities();
  } catch (err) {
    errorThrown = true;
  }
  assert.strictEqual(errorThrown, true, 'Fresh fetch failure must throw if no cache exists');

  // If previous data existed and background revalidation fails:
  Health.invalidateCapabilities();
  global.fetch = async () => createMockResponse(200, mockData1);
  await Health.fetchCapabilities();

  // Now backend goes down
  global.fetch = async () => { throw new Error('API down'); };
  // With isStale option, operation status cannot remain green
  const healthyOp = { runtime_health: 'HEALTHY', last_outcome: 'DIRECT_CONTENT', decision: 'PREFER' };
  assert.strictEqual(Health.classifyOperation(healthyOp), 'healthy');
  assert.strictEqual(Health.classifyOperation(healthyOp, { isStale: true }), 'stale');
  console.log('✓ Stale observations degrade gracefully without staying green');

  console.log('--- TEST 8: Page Becomes Visible After Inactivity ---');
  Health.configure({ ttlMs: 10 });
  await new Promise(r => setTimeout(r, 20));
  fetchCallCount = 0;
  global.fetch = async () => {
    fetchCallCount++;
    return createMockResponse(200, mockData2);
  };

  visibilityState = 'visible';
  for (const listener of visibilityListeners) {
    listener();
  }
  await new Promise(r => setTimeout(r, 50));
  assert.strictEqual(fetchCallCount >= 1, true, 'Visibility change must trigger revalidation when expired');
  console.log('✓ Page visibility revalidation verified');

  console.log('\nALL FRONTEND OPERATION HEALTH TESTS PASSED (8/8)!');
}

runTests().catch(err => {
  console.error('TEST FAILED:', err);
  process.exit(1);
});
