const API_BASE = (typeof window !== "undefined" && window.BACKEND_BASE)
  ? window.BACKEND_BASE
  : "https://misinfo-5f13.onrender.com"; // fallback to Render backend
const API_URL = `${API_BASE}/dashboard/claims`;

async function fetchWithRetry(url, options = {}, retries = 3, delayMs = 800) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res;
    } catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(r => setTimeout(r, delayMs * Math.pow(2, i)));
    }
  }
}

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

function buildPieChart(stats) {
  const ctx = document.getElementById('pieChart') || document.getElementById('claimsPieChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['True', 'False', 'Misleading', 'Unverified'],
      datasets: [{
        data: [stats.trueCount, stats.falseCount, stats.misleadingCount, stats.unverifiedCount],
        backgroundColor: [
          'rgba(16, 185, 129, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(251, 191, 36, 0.8)',
          'rgba(139, 92, 246, 0.8)'
        ],
        borderColor: [
          '#10b981',
          '#ef4444',
          '#fbbf24',
          '#8b5cf6'
        ],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#cbd5e1',
            font: {
              size: 12,
              family: 'Inter'
            },
            padding: 12
          }
        }
      }
    }
  });
}

function buildBarChart(stats) {
  const ctx = document.getElementById('barChart') || document.getElementById('claimsBarChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['True', 'False', 'Misleading', 'Unverified'],
      datasets: [{
        label: 'Claims',
        data: [stats.trueCount, stats.falseCount, stats.misleadingCount, stats.unverifiedCount],
        backgroundColor: [
          'rgba(16, 185, 129, 0.7)',
          'rgba(239, 68, 68, 0.7)',
          'rgba(251, 191, 36, 0.7)',
          'rgba(139, 92, 246, 0.7)'
        ],
        borderColor: [
          '#10b981',
          '#ef4444',
          '#fbbf24',
          '#8b5cf6'
        ],
        borderWidth: 2,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            color: '#cbd5e1',
            font: {
              family: 'Inter'
            }
          },
          grid: {
            color: 'rgba(203, 213, 225, 0.1)'
          }
        },
        x: {
          ticks: {
            color: '#cbd5e1',
            font: {
              family: 'Inter'
            }
          },
          grid: {
            display: false
          }
        }
      }
    }
  });
}

function buildCard(item) {
  const card = document.createElement("div");
  card.className = "claim-card";

  // Green indicator dot
  const indicator = document.createElement("div");
  indicator.className = "claim-indicator";

  const title = document.createElement("h3");
  title.className = "claim-text";
  title.textContent = item.claim || "";

  // Verdict badge - shown in collapsed state
  const badgeContainer = document.createElement("div");
  badgeContainer.style.marginLeft = "2rem";
  badgeContainer.style.marginBottom = "0.75rem";

  const badge = document.createElement("span");
  const v = String(item.verdict).toLowerCase();
  const badgeClassCollapsed = v === "true" ? "badge-true" : v === "misleading" ? "badge-misleading" : "badge-false";
  const badgeTextCollapsed = v === "true" ? "True" : v === "misleading" ? "Misleading" : "False";
  badge.className = `badge ${badgeClassCollapsed}`;
  badge.textContent = badgeTextCollapsed;
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
  evidenceContent.innerHTML = `<p style="color: #64748b;">Loading AI explanation...</p>`;

  evidence.appendChild(evidenceContent);

  btn.addEventListener("click", async () => {
    const isExpanded = card.classList.contains("expanded");

    if (!isExpanded) {
      // Expand and fetch explanation
      card.classList.add("expanded");
      btn.textContent = "Hide Evidence";

      // Fetch AI explanation
      try {
        evidenceContent.innerHTML = `<p style="color: #64748b;">🤖 Generating AI explanation...</p>`;

        const response = await fetchWithRetry(`${API_BASE}/explain-claim`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            claim: item.claim,
            verdict: item.verdict
          })
        }, 3, 800);

        const data = await response.json();

        const v2 = String(item.verdict).toLowerCase();
        const badgeClass = v2 === "true" ? "badge-true" : v2 === "misleading" ? "badge-misleading" : "badge-false";
        const badgeText = v2 === "true" ? "True" : v2 === "misleading" ? "Misleading" : "False";

        const source = data.evidence_url
          ? '<a href="' + (data.evidence_url || '#') + '" target="_blank" rel="noopener noreferrer">Source</a>'
          : '<span style="color:#94a3b8">No link available</span>';
        evidenceContent.innerHTML = `
          <div class="evidence-block">
            <span class="badge ${badgeClass}">${badgeText}</span>
          </div>
          <div class="evidence-block">
            <h4>AI Analysis:</h4>
            <p>${data.explanation || "Unable to generate explanation."}</p>
          </div>
          <div class="evidence-block">
            <h4>Evidence Link:</h4>
            <p>${source}</p>
          </div>
        `;
        card.dataset.loaded = "1";
      } catch (error) {
        evidenceContent.innerHTML = `
          <div class="evidence-block">
            <p style="color: #ef4444;">⚠️ Failed to load AI explanation. Please try again.</p>
          </div>
        `;
      }
    } else {
      // Collapse
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

async function init() {
  try {
    console.time("fetch-dashboard-claims");
    const res = await fetchWithRetry(API_URL, { cache: "no-store" });
    if (!res.ok) {
      const container = document.getElementById("claimsContainer");
      if (container) container.innerHTML = "";
      const dbg = document.getElementById("debugArea");
      if (dbg) { dbg.style.display = "block"; const b=document.createElement("div"); b.className="debug-banner error"; b.textContent=`Failed to load dashboard claims (${res.status})`; dbg.appendChild(b);} 
      return;
    }
    const data = await res.json();
    console.timeEnd("fetch-dashboard-claims");

    const container = document.getElementById("claimsContainer");
    if (container) {
      container.innerHTML = "";
      data.forEach(item => container.appendChild(buildCard(item)));
    }

    // Update stat cards and build charts
    const stats = updateStatCards(data);
    buildPieChart(stats);
    buildBarChart(stats);
  } catch (e) {
    const container = document.getElementById("claimsContainer");
    if (container) container.innerHTML = "";
    const dbg = document.getElementById("debugArea");
    if (dbg) { dbg.style.display = "block"; const b=document.createElement("div"); b.className="debug-banner error"; b.textContent=`Error fetching dashboard data: ${e}`; dbg.appendChild(b);} 
  }
}

window.addEventListener("DOMContentLoaded", init);
