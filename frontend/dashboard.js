// ─────────────────────────────────────────────
// STATIC FALLBACK CLAIMS (shown instantly)
// These live in the frontend (Netlify) and are
// replaced once the Render backend wakes up.
// ─────────────────────────────────────────────
const STATIC_CLAIMS = [
  {
    claim: "COVID-19 vaccines contain microchips that track your location.",
    verdict: "False",
    explanation: "Extensive independent analysis of vaccine vials found no electronic components. This claim originated from a misunderstanding of lipid nanoparticles used as delivery mechanisms, which are microscopic fat particles — not microchips."
  },
  {
    claim: "Climate change is causing more frequent and intense hurricanes globally.",
    verdict: "True",
    explanation: "Multiple peer-reviewed studies confirm that rising ocean temperatures fuel stronger hurricanes. The IPCC's 2021 report directly links anthropogenic warming to increased hurricane intensity, with Category 4–5 storms becoming more common."
  },
  {
    claim: "Drinking bleach can cure coronavirus infections.",
    verdict: "False",
    explanation: "Ingesting bleach is extremely dangerous and can cause severe chemical burns, organ failure, and death. No scientific or medical body has ever endorsed this. The WHO and CDC have repeatedly issued warnings against this claim."
  },
  {
    claim: "5G towers were deliberately set on fire across Europe due to COVID conspiracy theories.",
    verdict: "True",
    explanation: "BBC and Reuters documented over 100 incidents of 5G tower arson attacks across the UK, Netherlands, and Ireland in early 2020, fuelled by unfounded conspiracy theories linking 5G to COVID-19."
  },
  {
    claim: "The Amazon rainforest produces 20% of the world's oxygen.",
    verdict: "Misleading",
    explanation: "While the Amazon produces ~20% of global oxygen through photosynthesis, it also consumes approximately the same amount through respiration and decomposition. Net oxygen contribution is close to zero — the ocean is the primary oxygen source."
  },
  {
    claim: "Former US President Donald Trump was impeached twice.",
    verdict: "True",
    explanation: "Trump was impeached by the House of Representatives in December 2019 (Ukraine affair) and again in January 2021 (incitement of insurrection). He was acquitted by the Senate both times, making him the only US president impeached twice."
  },
  {
    claim: "Eating carrots significantly improves night vision in healthy adults.",
    verdict: "False",
    explanation: "Carrots contain beta-carotene, which the body converts to Vitamin A — essential for preventing night blindness in deficient individuals. However, in healthy adults with sufficient Vitamin A, eating more carrots provides no additional vision benefit."
  },
  {
    claim: "Social media algorithms are designed to maximise engagement by promoting emotionally charged content.",
    verdict: "True",
    explanation: "Internal documents from Facebook (the 'Facebook Papers') and testimony from former employees confirm that recommendation algorithms prioritise content that drives reactions, shares, and comments — which correlates strongly with outrage and emotional provocation."
  },
  {
    claim: "The Great Wall of China is visible from space with the naked eye.",
    verdict: "False",
    explanation: "Astronauts including China's first, Yang Liwei, have confirmed the Great Wall is not visible from low Earth orbit without aid. NASA has confirmed its width (~9m) is far too narrow to resolve at that altitude — narrower than a human hair at that scale."
  },
  {
    claim: "Antibiotic resistance is partly caused by overuse of antibiotics in livestock farming.",
    verdict: "True",
    explanation: "The WHO and CDC both cite livestock antibiotic use — particularly sub-therapeutic dosing for growth promotion — as a major driver of antibiotic-resistant 'superbugs'. Many countries have since banned or restricted this practice."
  },
  {
    claim: "Human activity is the primary driver of the current rate of species extinction.",
    verdict: "True",
    explanation: "The IPBES 2019 Global Assessment found current extinction rates 100–1,000x higher than natural background rates, primarily driven by habitat destruction, pollution, overexploitation, invasive species, and climate change — all human-caused."
  },
  {
    claim: "Ivermectin is scientifically proven to be an effective treatment for COVID-19.",
    verdict: "False",
    explanation: "Multiple large-scale randomised controlled trials (TOGETHER, ACTIV-6, Oxford PRINCIPLE) found ivermectin provided no significant clinical benefit for COVID-19 patients. WHO, FDA, and EMA all recommend against its use for this purpose."
  },
  {
    claim: "The moon landing in 1969 was staged and filmed in a Hollywood studio.",
    verdict: "False",
    explanation: "Independently verified by the Soviet Union (who tracked the mission via radar), 382 kg of lunar rock brought back for global scientific study, retroreflectors still used by observatories today, and corroborated by thousands of NASA employees and international scientists."
  },
  {
    claim: "Screen time before bed significantly disrupts sleep quality in teenagers.",
    verdict: "True",
    explanation: "Multiple studies, including research published in JAMA Pediatrics, show that blue light from screens suppresses melatonin production, delaying sleep onset. Teens using devices 1+ hours before bed show later sleep timing and reduced total sleep duration."
  },
  {
    claim: "Electric vehicles produce zero emissions over their entire lifecycle.",
    verdict: "Misleading",
    explanation: "EVs produce zero direct tailpipe emissions, but manufacturing (especially battery production) and electricity generation create emissions. Lifecycle emissions vary widely by grid source — coal-heavy grids reduce but don't eliminate the carbon advantage over petrol vehicles."
  }
];

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────
const BACKEND_BASE = "https://misinformation-1ouh.onrender.com";
const API_URL = `${BACKEND_BASE}/api/dashboard/claims`;
const HEALTH_URL = `${BACKEND_BASE}/healthz`;

let backendAlive = false;
let allClaims = [...STATIC_CLAIMS];

// ─────────────────────────────────────────────
// STAT CARDS
// ─────────────────────────────────────────────
function updateStatCards(items) {
  const trueCount = items.filter(i => String(i.verdict).toLowerCase() === "true").length;
  const falseCount = items.filter(i => String(i.verdict).toLowerCase() === "false").length;
  const misleadingCount = items.filter(i => String(i.verdict).toLowerCase() === "misleading").length;
  const unverifiedCount = items.length - (trueCount + falseCount + misleadingCount);

  const elTrue = document.getElementById('trueCount');
  const elFalse = document.getElementById('falseCount');
  const elMis = document.getElementById('misleadingCount');
  const elUnv = document.getElementById('unverifiedCount');
  if (elTrue) elTrue.textContent = trueCount;
  if (elFalse) elFalse.textContent = falseCount;
  if (elMis) elMis.textContent = misleadingCount;
  if (elUnv) elUnv.textContent = unverifiedCount;

  return { trueCount, falseCount, misleadingCount, unverifiedCount };
}

// ─────────────────────────────────────────────
// CHARTS
// ─────────────────────────────────────────────
let pieChartInst = null;
let barChartInst = null;

function buildPieChart(stats) {
  const ctx = document.getElementById('pieChart') || document.getElementById('claimsPieChart');
  if (!ctx) return;
  if (pieChartInst) { pieChartInst.destroy(); pieChartInst = null; }
  pieChartInst = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['True', 'False', 'Misleading', 'Unverified'],
      datasets: [{
        data: [stats.trueCount, stats.falseCount, stats.misleadingCount, stats.unverifiedCount],
        backgroundColor: ['rgba(16,185,129,0.8)','rgba(239,68,68,0.8)','rgba(251,191,36,0.8)','rgba(139,92,246,0.8)'],
        borderColor: ['#10b981','#ef4444','#fbbf24','#8b5cf6'],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { color: '#cbd5e1', font: { size: 12, family: 'Inter' }, padding: 12 } } }
    }
  });
}

function buildBarChart(stats) {
  const ctx = document.getElementById('barChart') || document.getElementById('claimsBarChart');
  if (!ctx) return;
  if (barChartInst) { barChartInst.destroy(); barChartInst = null; }
  barChartInst = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['True', 'False', 'Misleading', 'Unverified'],
      datasets: [{
        label: 'Claims',
        data: [stats.trueCount, stats.falseCount, stats.misleadingCount, stats.unverifiedCount],
        backgroundColor: ['rgba(16,185,129,0.7)','rgba(239,68,68,0.7)','rgba(251,191,36,0.7)','rgba(139,92,246,0.7)'],
        borderColor: ['#10b981','#ef4444','#fbbf24','#8b5cf6'],
        borderWidth: 2, borderRadius: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { color: '#cbd5e1', font: { family: 'Inter' } }, grid: { color: 'rgba(203,213,225,0.1)' } },
        x: { ticks: { color: '#cbd5e1', font: { family: 'Inter' } }, grid: { display: false } }
      }
    }
  });
}

// ─────────────────────────────────────────────
// CARD BUILDER
// ─────────────────────────────────────────────
function buildCard(item) {
  const card = document.createElement("div");
  card.className = "claim-card";

  const indicator = document.createElement("div");
  indicator.className = "claim-indicator";

  const title = document.createElement("h3");
  title.className = "claim-text";
  title.textContent = item.claim || "";

  const badgeContainer = document.createElement("div");
  badgeContainer.style.cssText = "margin-left:2rem;margin-bottom:0.75rem;";

  const verdict = String(item.verdict);
  const isTrue = verdict.toLowerCase() === "true";
  const isMisleading = verdict.toLowerCase() === "misleading";
  const badge = document.createElement("span");
  badge.className = `badge ${isTrue ? "badge-true" : isMisleading ? "badge-misleading" : "badge-false"}`;
  badge.textContent = verdict;
  badgeContainer.appendChild(badge);

  const summary = document.createElement("p");
  summary.className = "claim-summary";
  summary.textContent = item.explanation || "";

  const btn = document.createElement("button");
  btn.className = "toggle-btn";
  btn.textContent = "Show Evidence";

  const evidence = document.createElement("div");
  evidence.className = "evidence-section";

  const evidenceContent = document.createElement("div");
  evidenceContent.className = "evidence-content";

  // Pre-fill with static explanation immediately (no waiting)
  const staticExplanation = item.explanation || "This claim has been assessed by our AI verification system.";
  evidenceContent.innerHTML = `
    <div class="evidence-block">
      <span class="badge ${isTrue ? 'badge-true' : isMisleading ? 'badge-misleading' : 'badge-false'}">${verdict}</span>
    </div>
    <div class="evidence-block">
      <h4>Analysis:</h4>
      <p>${staticExplanation}</p>
    </div>
    <div class="evidence-block" id="aiEnhance_${Math.random().toString(36).slice(2)}">
      <p style="color:#64748b;font-size:0.85rem;">
        ${backendAlive ? '🤖 Loading AI-enhanced explanation...' : '📡 AI enhancement available once backend wakes up.'}
      </p>
    </div>
  `;

  evidence.appendChild(evidenceContent);

  btn.addEventListener("click", async () => {
    const isExpanded = card.classList.contains("expanded");
    if (!isExpanded) {
      card.classList.add("expanded");
      btn.textContent = "Hide Evidence";

      // Only call AI endpoint if backend is alive and not already loaded
      if (backendAlive && !card.dataset.aiLoaded) {
        const aiBlock = evidenceContent.querySelector('[id^="aiEnhance_"]');
        if (aiBlock) aiBlock.innerHTML = `<p style="color:#64748b;font-size:0.85rem;">🤖 Generating AI explanation...</p>`;

        try {
          const response = await fetch(`${BACKEND_BASE}/api/explain-claim`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ claim: item.claim, verdict: item.verdict })
          });
          const data = await response.json();

          if (data.explanation) {
            const aiExplanation = evidenceContent.querySelector('.evidence-block:nth-child(2) p');
            if (aiExplanation) aiExplanation.textContent = data.explanation;

            const src = data.evidence_url
              ? `<a href="${data.evidence_url}" target="_blank" rel="noopener noreferrer">View Source →</a>`
              : `<span style="color:#94a3b8">No source link available</span>`;
            const aiBlock2 = evidenceContent.querySelector('[id^="aiEnhance_"]');
            if (aiBlock2) aiBlock2.innerHTML = `<h4>Evidence Link:</h4><p>${src}</p>`;
            card.dataset.aiLoaded = "1";
          }
        } catch (e) {
          const aiBlock2 = evidenceContent.querySelector('[id^="aiEnhance_"]');
          if (aiBlock2) aiBlock2.innerHTML = `<p style="color:#94a3b8;font-size:0.85rem;">AI explanation unavailable.</p>`;
        }
      }
    } else {
      card.classList.remove("expanded");
      btn.textContent = "Show Evidence";
    }
  });

  card.appendChild(indicator);
  card.appendChild(title);
  card.appendChild(badgeContainer);
  card.appendChild(summary);
  card.appendChild(btn);
  card.appendChild(evidence);
  return card;
}

// ─────────────────────────────────────────────
// RENDER CLAIMS
// ─────────────────────────────────────────────
function renderClaims(data) {
  allClaims = data;
  const container = document.getElementById("claimsContainer");
  if (!container) return;
  container.innerHTML = "";
  data.forEach(item => container.appendChild(buildCard(item)));
  const stats = updateStatCards(data);
  buildPieChart(stats);
  buildBarChart(stats);
}

// ─────────────────────────────────────────────
// STATUS BANNER
// ─────────────────────────────────────────────
function setStatusBanner(state) {
  let banner = document.getElementById("backendStatusBanner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "backendStatusBanner";
    banner.style.cssText = "text-align:center;padding:0.5rem 1rem;font-size:0.85rem;font-family:Inter,sans-serif;transition:all 0.4s ease;";
    const header = document.querySelector(".page-header");
    if (header) header.insertAdjacentElement("afterend", banner);
  }
  if (state === "loading") {
    banner.style.cssText += "background:rgba(251,191,36,0.1);color:#fbbf24;border-radius:8px;margin:0.5rem 0;";
    banner.innerHTML = `⏳ Backend is waking up on Render... Showing cached data. Live AI results will load shortly.`;
  } else if (state === "live") {
    banner.style.cssText += "background:rgba(16,185,129,0.1);color:#10b981;border-radius:8px;margin:0.5rem 0;";
    banner.innerHTML = `✅ Live backend connected — showing real-time AI verified claims.`;
    setTimeout(() => { banner.style.opacity = "0"; setTimeout(() => banner.remove(), 600); }, 4000);
  } else if (state === "error") {
    banner.style.cssText += "background:rgba(239,68,68,0.1);color:#ef4444;border-radius:8px;margin:0.5rem 0;";
    banner.innerHTML = `⚠️ Backend unavailable. Showing pre-verified sample claims.`;
  }
}

// ─────────────────────────────────────────────
// BACKEND POLL — tries until alive, then loads
// ─────────────────────────────────────────────
async function pollBackend() {
  const MAX_ATTEMPTS = 20; // ~2 min total
  const INTERVAL_MS = 6000;

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    try {
      const r = await fetch(HEALTH_URL, { cache: "no-store", signal: AbortSignal.timeout(5000) });
      if (r.ok) {
        backendAlive = true;
        // Fetch real claims from backend
        const claimsRes = await fetch(API_URL, { cache: "no-store" });
        if (claimsRes.ok) {
          const data = await claimsRes.json();
          if (data && data.length > 0) {
            renderClaims(data);
            setStatusBanner("live");
            applyFilters(); // Re-apply any active filters
            return;
          }
        }
      }
    } catch (e) {
      // Backend still asleep, keep waiting
    }
    await new Promise(res => setTimeout(res, INTERVAL_MS));
  }
  // After max attempts, give up gracefully
  setStatusBanner("error");
}

// ─────────────────────────────────────────────
// SEARCH & FILTER
// ─────────────────────────────────────────────
function applyFilters() {
  const container = document.getElementById("claimsContainer");
  if (!container) return;
  const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
  const activeFilter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';

  const filtered = allClaims.filter(claim => {
    const matchesSearch = !searchTerm ||
      (claim.claim || '').toLowerCase().includes(searchTerm) ||
      (claim.explanation || '').toLowerCase().includes(searchTerm);
    const matchesFilter = activeFilter === 'all' ||
      String(claim.verdict).toLowerCase() === activeFilter.toLowerCase();
    return matchesSearch && matchesFilter;
  });

  container.innerHTML = "";
  if (filtered.length === 0) {
    container.innerHTML = `<p style="text-align:center;color:var(--text-muted);padding:3rem;">No claims match your filters.</p>`;
  } else {
    filtered.forEach(item => container.appendChild(buildCard(item)));
  }
  updateStatCards(filtered);
}

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  // 1. Instantly show static claims
  renderClaims(STATIC_CLAIMS);
  setStatusBanner("loading");

  // 2. Start polling backend in background
  pollBackend();

  // 3. Search
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    let t;
    searchInput.addEventListener('input', () => { clearTimeout(t); t = setTimeout(applyFilters, 300); });
  }

  // 4. Filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
    });
  });

  // 5. Refresh button
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.classList.add('spinning');
      if (backendAlive) {
        try {
          const res = await fetch(API_URL, { cache: "no-store" });
          if (res.ok) { const data = await res.json(); if (data.length) renderClaims(data); }
        } catch (e) {}
      } else {
        renderClaims(STATIC_CLAIMS);
      }
      applyFilters();
      setTimeout(() => refreshBtn.classList.remove('spinning'), 1000);
    });
  }
});
