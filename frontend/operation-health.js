/* Operation-level acquisition status helpers shared by all four agents.
 * Phase 7.1 Hardened: bounded TTL cache, concurrent request deduplication,
 * visibility revalidation, explicit cache invalidation, and stale-truth tracking.
 */
(function attachOperationHealth(root) {
  'use strict';

  const DEFAULT_CONFIG = {
    ttlMs: 45000,           // 45s cache validity (bounded 30-60s)
    staleThresholdMs: 90000, // 90s: beyond this, last-known-good is flagged stale
    timeoutMs: 3500          // 3.5s fetch timeout
  };

  let config = Object.assign({}, DEFAULT_CONFIG);
  let cachedData = null;
  let lastFetchedAt = 0;
  let inFlightPromise = null;
  let lastFetchError = null;
  let activeListeners = [];

  function configure(newConfig) {
    if (newConfig && typeof newConfig === 'object') {
      config = Object.assign({}, config, newConfig);
    }
    return Object.assign({}, config);
  }

  function getCacheState() {
    const now = Date.now();
    const age = lastFetchedAt > 0 ? now - lastFetchedAt : null;
    const isExpired = age !== null && age > config.ttlMs;
    const isStale = age !== null && age > config.staleThresholdMs;
    return {
      hasData: Boolean(cachedData),
      lastFetchedAt,
      ageMs: age,
      isExpired,
      isStale,
      inFlight: Boolean(inFlightPromise),
      lastFetchError: lastFetchError ? String(lastFetchError.message || lastFetchError) : null
    };
  }

  function invalidateCapabilities() {
    cachedData = null;
    lastFetchedAt = 0;
    lastFetchError = null;
    inFlightPromise = null;
  }

  function classifyOperation(operation, options) {
    const op = operation || {};
    const opts = options || {};
    const decision = String(op.decision || '').toUpperCase();
    const health = String(op.runtime_health || '').toUpperCase();
    const outcome = String(op.last_outcome || '').toUpperCase();
    const reason = String(op.reason || '').toUpperCase();

    // Explicit policy blocks and auth requirements take precedence
    if (reason.includes('POLICY_BLOCKED') || health === 'BLOCKED') return 'blocked';
    if (reason.includes('AUTH_REQUIRED') || health === 'AUTH_REQUIRED') return 'auth_required';
    if (reason.includes('NO_PRODUCTION_HANDLER') || health === 'UNAVAILABLE_NOT_IMPLEMENTED') return 'unavailable';

    // If cache is stale beyond threshold or caller flagged stale observation,
    // a previously healthy operation must NEVER remain indefinitely green.
    if (opts.isStale || health === 'STALE') {
      if (['HEALTHY', 'LIMITED'].includes(health)) return 'stale';
    }

    if (decision === 'DEFER_TEMPORARY' || ['RATE_LIMITED', 'DEGRADED'].includes(health)) return 'degraded';
    if (['DIRECT_METADATA', 'SYNDICATED_SUMMARY', 'SEARCH_INDEX_DISCOVERY', 'PARTIAL_OR_UNCLASSIFIED'].includes(outcome)) return 'limited';
    if (health === 'LIMITED') return 'limited';
    if (health === 'HEALTHY' && outcome === 'DIRECT_CONTENT') return 'healthy';
    return 'unverified';
  }

  function summarizeChannel(channel, requiredOperations, options) {
    const operations = (channel && channel.operation_capabilities) || {};
    const names = requiredOperations && requiredOperations.length ? requiredOperations : Object.keys(operations);
    const details = names.map(name => ({ name, state: classifyOperation(operations[name], options) }));
    if (!details.length) return { state: 'unverified', label: 'Not verified', details: [] };
    const states = new Set(details.map(item => item.state));
    let state;
    if (states.size === 1) state = details[0].state;
    // Mixed operation health must never become a generic green channel.
    else if (states.has('healthy') || states.has('limited')) state = 'limited';
    else if (states.has('blocked')) state = 'blocked';
    else if (states.has('auth_required')) state = 'auth_required';
    else if (states.has('degraded')) state = 'degraded';
    else if (states.has('stale')) state = 'stale';
    else if (states.has('unavailable')) state = 'unavailable';
    else state = 'unverified';
    const labels = {
      healthy: 'Direct content', limited: 'Limited / partial', degraded: 'Temporarily degraded',
      auth_required: 'Authentication required', blocked: 'Policy blocked',
      unavailable: 'Not implemented', stale: 'Stale observation', unverified: 'Not yet verified'
    };
    return { state, label: labels[state] || 'Not yet verified', details };
  }

  async function fetchCapabilities(options) {
    const opts = options || {};
    const now = Date.now();
    const maxAge = typeof opts.maxAgeMs === 'number' ? opts.maxAgeMs : config.ttlMs;

    // Cache hit: return existing fresh data unless caller requested force revalidation
    if (!opts.force && cachedData && (now - lastFetchedAt) < maxAge) {
      return cachedData;
    }

    // Deduplication: if a request is already in-flight, return the same promise
    if (inFlightPromise) {
      return inFlightPromise;
    }

    const abortController = typeof AbortController !== 'undefined' ? new AbortController() : null;
    let timeoutId = null;

    if (abortController) {
      timeoutId = setTimeout(() => {
        try { abortController.abort(); } catch (_) {}
      }, config.timeoutMs);
    }

    const fetchPromise = (async () => {
      try {
        const fetchFn = (typeof root !== 'undefined' && root.fetch) || (typeof fetch !== 'undefined' ? fetch : null);
        if (!fetchFn) throw new Error('fetch is not available in environment');

        const fetchOpts = { headers: { 'Accept': 'application/json' } };
        if (abortController) {
          fetchOpts.signal = abortController.signal;
        }

        const response = await fetchFn('/api/agent-reach/capabilities', fetchOpts);
        if (timeoutId) clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`Capability API returned HTTP ${response.status}`);
        }

        const data = await response.json();
        cachedData = data;
        lastFetchedAt = Date.now();
        lastFetchError = null;
        return cachedData;
      } catch (err) {
        if (timeoutId) clearTimeout(timeoutId);
        lastFetchError = err;

        // If we have previous data, keep it but mark it so callers can identify degraded/stale state
        if (cachedData) {
          return cachedData;
        }
        throw err;
      } finally {
        inFlightPromise = null;
      }
    })();

    inFlightPromise = fetchPromise;
    return inFlightPromise;
  }

  async function renderPills(element, channelRequirements, options) {
    if (!element) return;
    const settings = options || {};
    const elementRef = element;

    async function update() {
      try {
        const data = await fetchCapabilities(settings.fetchOptions);
        const channels = (data && data.channels) || {};
        const stateInfo = getCacheState();
        const evalOpts = { isStale: stateInfo.isStale || (settings.fetchOptions && settings.fetchOptions.isStale) };

        elementRef.replaceChildren();
        const lead = (typeof document !== 'undefined') ? document.createElement('span') : null;
        if (lead) {
          lead.style.cssText = 'color:var(--text-dim);font-weight:700;';
          lead.textContent = settings.lead || 'OPERATION STATUS:';
          elementRef.appendChild(lead);
        }

        Object.entries(channelRequirements || {}).forEach(([channelName, requirement]) => {
          const summary = summarizeChannel(channels[channelName] || {}, requirement.operations || [], evalOpts);
          if (typeof document !== 'undefined') {
            const pill = document.createElement('span');
            const visual = summary.state === 'healthy' ? 'healthy'
              : ['limited', 'degraded', 'auth_required', 'stale'].includes(summary.state) ? 'degraded'
                : 'unavailable';
            pill.className = `${settings.pillClass || 'health-pill'} ${visual}`;
            pill.textContent = `${requirement.label || channelName.toUpperCase()} · ${summary.label}`;
            pill.title = summary.details.map(item => `${item.name}: ${item.state}`).join(', ');
            elementRef.appendChild(pill);
          }
        });

        if (settings.tail && typeof document !== 'undefined') {
          const tail = document.createElement('span');
          tail.style.cssText = 'margin-left:auto;color:var(--text-dim);';
          tail.textContent = settings.tail;
          elementRef.appendChild(tail);
        }
      } catch (_error) {
        if (typeof document !== 'undefined') {
          elementRef.replaceChildren();
          const unavailable = document.createElement('span');
          unavailable.className = `${settings.pillClass || 'health-pill'} unavailable`;
          unavailable.textContent = 'Operation status unavailable';
          elementRef.appendChild(unavailable);
        }
      }
    }

    // Register re-render listener for automatic visibility or refresh triggers
    if (!activeListeners.includes(update)) {
      activeListeners.push(update);
    }

    return update();
  }

  // Controlled visibility listener: when tab becomes visible after inactivity,
  // revalidate if cache has expired beyond TTL without runaway background polling
  if (typeof document !== 'undefined' && document.addEventListener) {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        const state = getCacheState();
        if (state.isExpired) {
          fetchCapabilities({ force: true }).then(() => {
            activeListeners.forEach(fn => {
              try { fn(); } catch (_) {}
            });
          }).catch(() => {});
        }
      }
    });
  }

  root.AegisOperationHealth = {
    DEFAULT_CONFIG,
    configure,
    getCacheState,
    invalidateCapabilities,
    classifyOperation,
    summarizeChannel,
    fetchCapabilities,
    renderPills
  };
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
