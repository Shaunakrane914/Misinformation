/* Operation-level acquisition status helpers shared by all four agents. */
(function attachOperationHealth(root) {
  'use strict';

  let capabilityPromise = null;

  function classifyOperation(operation) {
    const op = operation || {};
    const decision = String(op.decision || '').toUpperCase();
    const health = String(op.runtime_health || '').toUpperCase();
    const outcome = String(op.last_outcome || '').toUpperCase();
    const reason = String(op.reason || '').toUpperCase();
    if (reason.includes('POLICY_BLOCKED') || health === 'BLOCKED') return 'blocked';
    if (reason.includes('AUTH_REQUIRED') || health === 'AUTH_REQUIRED') return 'auth_required';
    if (reason.includes('NO_PRODUCTION_HANDLER') || health === 'UNAVAILABLE_NOT_IMPLEMENTED') return 'unavailable';
    if (decision === 'DEFER_TEMPORARY' || ['RATE_LIMITED', 'DEGRADED'].includes(health)) return 'degraded';
    if (['DIRECT_METADATA', 'SYNDICATED_SUMMARY', 'SEARCH_INDEX_DISCOVERY', 'PARTIAL_OR_UNCLASSIFIED'].includes(outcome)) return 'limited';
    if (health === 'LIMITED') return 'limited';
    if (health === 'HEALTHY' && outcome === 'DIRECT_CONTENT') return 'healthy';
    return 'unverified';
  }

  function summarizeChannel(channel, requiredOperations) {
    const operations = (channel && channel.operation_capabilities) || {};
    const names = requiredOperations && requiredOperations.length ? requiredOperations : Object.keys(operations);
    const details = names.map(name => ({ name, state: classifyOperation(operations[name]) }));
    if (!details.length) return { state: 'unverified', label: 'Not verified', details: [] };
    const states = new Set(details.map(item => item.state));
    let state;
    if (states.size === 1) state = details[0].state;
    // Mixed operation health must never become a generic green channel.
    else if (states.has('healthy') || states.has('limited')) state = 'limited';
    else if (states.has('blocked')) state = 'blocked';
    else if (states.has('auth_required')) state = 'auth_required';
    else if (states.has('degraded')) state = 'degraded';
    else if (states.has('unavailable')) state = 'unavailable';
    else state = 'unverified';
    const labels = {
      healthy: 'Direct content', limited: 'Limited / partial', degraded: 'Temporarily degraded',
      auth_required: 'Authentication required', blocked: 'Policy blocked',
      unavailable: 'Not implemented', unverified: 'Not yet verified'
    };
    return { state, label: labels[state], details };
  }

  async function fetchCapabilities() {
    if (!capabilityPromise) {
      capabilityPromise = fetch('/api/agent-reach/capabilities', {
        signal: AbortSignal.timeout(3000)
      }).then(response => {
        if (!response.ok) throw new Error(`Capability API returned ${response.status}`);
        return response.json();
      }).catch(error => {
        capabilityPromise = null;
        throw error;
      });
    }
    return capabilityPromise;
  }

  async function renderPills(element, channelRequirements, options) {
    if (!element) return;
    const settings = options || {};
    try {
      const data = await fetchCapabilities();
      const channels = data.channels || {};
      element.replaceChildren();
      const lead = document.createElement('span');
      lead.style.cssText = 'color:var(--text-dim);font-weight:700;';
      lead.textContent = settings.lead || 'OPERATION STATUS:';
      element.appendChild(lead);
      Object.entries(channelRequirements).forEach(([channelName, requirement]) => {
        const summary = summarizeChannel(channels[channelName] || {}, requirement.operations || []);
        const pill = document.createElement('span');
        const visual = summary.state === 'healthy' ? 'healthy'
          : ['limited', 'degraded', 'auth_required'].includes(summary.state) ? 'degraded'
            : 'unavailable';
        pill.className = `${settings.pillClass || 'health-pill'} ${visual}`;
        pill.textContent = `${requirement.label || channelName.toUpperCase()} · ${summary.label}`;
        pill.title = summary.details.map(item => `${item.name}: ${item.state}`).join(', ');
        element.appendChild(pill);
      });
      if (settings.tail) {
        const tail = document.createElement('span');
        tail.style.cssText = 'margin-left:auto;color:var(--text-dim);';
        tail.textContent = settings.tail;
        element.appendChild(tail);
      }
    } catch (_error) {
      element.replaceChildren();
      const unavailable = document.createElement('span');
      unavailable.className = `${settings.pillClass || 'health-pill'} unavailable`;
      unavailable.textContent = 'Operation status unavailable';
      element.appendChild(unavailable);
    }
  }

  root.AegisOperationHealth = {
    classifyOperation, summarizeChannel, fetchCapabilities, renderPills
  };
})(window);
