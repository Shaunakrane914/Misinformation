// Recent completed investigations: no fixtures, model calls or automatic reruns.
(() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  let reports = [];
  function render() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const filter = document.querySelector('.db-filter-btn.active')?.dataset.filter || 'all';
    const rows = reports.filter(row => (filter === 'all' || row.agent === filter) && String(row.query || '').toLowerCase().includes(query));
    document.getElementById('claimsContainer').innerHTML = rows.length ? rows.map(row => `<article class="claim-card" style="padding:20px;margin:16px 0;overflow-wrap:anywhere"><div>${escape(row.agent)} · ${escape(row.created_at || 'Date unavailable')}</div><h2 style="font-size:1.2rem"><a href="status.html?${row.kind === 'claim' ? 'id' : 'report'}=${encodeURIComponent(row.id)}">${escape(row.query || 'Saved investigation')}</a></h2><p>${escape(row.summary || 'Saved report')}</p><p>${escape(row.passage_words ?? 'Unknown')} published passage words · ${escape(typeof row.status === 'string' ? row.status : row.status?.status || 'See report for scope')}</p><details><summary>Full report ID</summary><code>${escape(row.id)}</code></details></article>`).join('') : '<p>No saved investigations match. Run an investigation and open its report in this browser to add it here.</p>';
  }
  async function load() {
    const banner = document.getElementById('statusBanner');
    const entries = window.AegisHistory?.entries() || [];
    const claims = entries.filter(row => row.kind === 'claim').map(row => ({...row, summary: 'Stored claim status; open to inspect the retained result.', passage_words: 'Not measured'}));
    const ids = entries.filter(row => row.kind !== 'claim').map(row => row.id);
    reports = claims;
    if (!ids.length) { banner.textContent = claims.length ? 'Saved claim status links; open a link for its current result.' : 'No report links saved in this browser yet.'; render(); return; }
    banner.textContent = 'Loading saved reports…';
    try {
      const response = await fetch(window.getAegisApiUrl('/api/investigations?ids=' + encodeURIComponent(ids.join(','))), {signal: AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error('History unavailable');
      reports = [...((await response.json()).investigations || []), ...claims];
      banner.textContent = `${reports.length} saved reports available. ${ids.length + claims.length - reports.length} links no longer available in server storage.`;
    } catch (_) { banner.textContent = 'History could not be loaded. Your saved links are retained; refresh to try again.'; }
    render();
  }
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('searchInput').addEventListener('input', render);
    document.getElementById('refreshBtn').addEventListener('click', load);
    document.querySelectorAll('.db-filter-btn').forEach(button => button.addEventListener('click', () => {
      document.querySelectorAll('.db-filter-btn').forEach(item => { item.classList.remove('active'); item.setAttribute('aria-pressed', 'false'); });
      button.classList.add('active'); button.setAttribute('aria-pressed', 'true'); render();
    }));
    load();
  });
})();
