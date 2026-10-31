/**
 * intelligence-transformer.js — Aegis Protocol (v2.0 Truthful)
 * ============================================================
 * Evidence Formatting & Quantitative Extraction Engine
 * 
 * Extracts structured quantitative metrics and channel dispersion from verified evidence.
 * 
 * Strict Evidence Qualification Invariants:
 * - NEVER synthesize "verified findings" from raw snippets or ungrounded sentences.
 *   Verified findings MUST originate from backend qualification gates.
 * - If backend findings are empty, data.findings remains empty ([]).
 * - NEVER generate synthetic executive summaries that claim unverified facts.
 */

(function(root) {
  'use strict';

  const POSITIVE_MARKERS = [
    /\b(?:profit|growth|gain|record|beat|surge|expansion|partnership|approved|cleared|dismissed|upgrade|buyback|dividend|award|patent|launch|breakthrough)\b/i,
    /\b(?:increased by|rose|climbed|outperformed|positive outlook|revenue jumped)\b/i
  ];

  const NEGATIVE_MARKERS = [
    /\b(?:loss|drop|fall|plunge|decline|miss|short[- ]seller|attack|lawsuit|litigation|probe|investigation|counterfeit|scam|fraud|fake|charges|subpoena|penalty|sanction|downgrade)\b/i,
    /\b(?:volatility|warning|headwind|under investigation|indicted|allegation|defamation|smear)\b/i
  ];

  const UNRESOLVED_MARKERS = [
    /\b(?:pending|ongoing|preliminary|unconfirmed|alleged|reviewing|awaiting|scheduled for|hearing|inquiry|unclear|disputed|forecast|speculation)\b/i,
    /\b(?:trial date|court hearing|jury selection|regulatory scrutiny|examination)\b/i
  ];

  const QUANTITATIVE_REGEX = /(?:\$|₹|£|€)\s*\d+(?:[.,]\d+)?(?:\s*(?:billion|million|trillion|B|M|K|Cr|Lakh))?|\b\d+(?:[.,]\d+)?%|\b(?:Q[1-4]|FY\s*\d{2,4})\b|\b(?:CIK\s*0*\d{6,10}|Accession\s*[\d-]+)\b/gi;

  function cleanSentence(s) {
    if (!s) return '';
    return s.replace(/\s+/g, ' ').trim();
  }

  function splitIntoSentences(text) {
    if (!text || typeof text !== 'string') return [];
    return text
      .split(/(?<=[.!?])\s+(?=[A-Z0-9"'])/)
      .map(cleanSentence)
      .filter(s => s.length > 25 && s.length < 350);
  }

  const IntelligenceTransformer = {
    /**
     * Main entry point: extracts quantitative metrics and channel dispersion
     * from genuine evidence without fabricating findings or summaries.
     */
    enrich(data) {
      if (!data || typeof data !== 'object') return data;

      const passages = this.collectPassages(data);
      let evidence = [];
      if (Array.isArray(data.evidence)) {
        evidence = data.evidence;
      } else if (data.evidence && typeof data.evidence === 'object') {
        const ev = data.evidence;
        evidence = [
          ...(Array.isArray(ev.primary) ? ev.primary : []),
          ...(Array.isArray(ev.independent) ? ev.independent : []),
          ...(Array.isArray(ev.community) ? ev.community : [])
        ];
      } else if (Array.isArray(data.sources)) {
        evidence = data.sources;
      }
      const allSentences = this.extractAllSentences(passages, evidence);

      // INVARIANT: Do NOT synthesize findings from unverified snippets.
      // Findings must strictly originate from the qualified backend pipeline.
      if (!Array.isArray(data.findings)) {
        data.findings = [];
      }

      // Do NOT overwrite or synthesize data.catalysts with keyword-extracted items;
      // Preserve existing backend-supplied catalysts, or store heuristic items under client_derived
      if (!data.catalysts || typeof data.catalysts !== 'object') {
        data.catalysts = { positive: [], negative: [], unresolved: [] };
      }
      data.client_derived = {
        heuristic_catalysts: this.extractCatalysts(allSentences)
      };

      // Extract Quantitative Indicators directly from acquired evidence
      data.quantitative_metrics = this.extractQuantitativeIndicators(allSentences);

      // Compute Channel Dispersion from actual evidence records
      data.channel_dispersion = this.computeChannelDispersion(evidence);

      return data;
    },

    collectPassages(data) {
      const list = [];
      if (Array.isArray(data.evidence_workbench?.passages)) {
        list.push(...data.evidence_workbench.passages);
      }
      if (Array.isArray(data.sources)) {
        for (const s of data.sources) {
          if (s.passage) list.push({ text: s.passage, source_title: s.title, publisher_host: s.publisher || s.domain, url: s.url });
          if (s.relevant_excerpt) list.push({ text: s.relevant_excerpt, source_title: s.title, publisher_host: s.domain, url: s.url });
        }
      }
      if (Array.isArray(data.evidence)) {
        for (const e of data.evidence) {
          if (e.text) list.push({ text: e.text, source_title: e.source_name || e.title, publisher_host: e.publisher || e.domain, url: e.url });
          if (e.snippet) list.push({ text: e.snippet, source_title: e.title, publisher_host: e.domain, url: e.url });
        }
      } else if (data.evidence && typeof data.evidence === 'object') {
        const allEv = [
          ...(Array.isArray(data.evidence.primary) ? data.evidence.primary : []),
          ...(Array.isArray(data.evidence.independent) ? data.evidence.independent : []),
          ...(Array.isArray(data.evidence.community) ? data.evidence.community : [])
        ];
        for (const e of allEv) {
          if (e.text) list.push({ text: e.text, source_title: e.source_name || e.title, publisher_host: e.publisher || e.domain, url: e.url });
          if (e.snippet) list.push({ text: e.snippet, source_title: e.title, publisher_host: e.domain, url: e.url });
        }
      }
      return list;
    },

    extractAllSentences(passages, evidence) {
      const sentences = [];
      const seen = new Set();

      for (const p of passages) {
        const text = typeof p === 'string' ? p : (p.text || p.content || '');
        for (const s of splitIntoSentences(text)) {
          const norm = s.toLowerCase().replace(/[^a-z0-9]/g, '');
          if (!seen.has(norm)) {
            seen.add(norm);
            sentences.push({
              text: s,
              source: p.source_title || p.publisher_host || 'Unspecified Source',
              url: p.url || p.source_url || null,
              publisher: p.publisher_host || 'Unspecified Publisher'
            });
          }
        }
      }

      for (const e of evidence) {
        const text = e.text || e.snippet || e.relevant_excerpt || '';
        for (const s of splitIntoSentences(text)) {
          const norm = s.toLowerCase().replace(/[^a-z0-9]/g, '');
          if (!seen.has(norm)) {
            seen.add(norm);
            sentences.push({
              text: s,
              source: e.source_name || e.title || 'Unspecified Source',
              url: e.url || null,
              publisher: e.publisher || e.domain || 'Unspecified Publisher'
            });
          }
        }
      }

      return sentences;
    },

    extractCatalysts(sentences) {
      const positive = [];
      const negative = [];
      const unresolved = [];

      for (const s of sentences) {
        const text = s.text;
        let matched = false;

        if (NEGATIVE_MARKERS.some(m => m.test(text))) {
          if (negative.length < 5) {
            negative.push({
              catalyst: text,
              source: s.source,
              url: s.url,
              epistemic_state: 'CONTESTED_HEADWIND'
            });
            matched = true;
          }
        }

        if (!matched && POSITIVE_MARKERS.some(m => m.test(text))) {
          if (positive.length < 5) {
            positive.push({
              catalyst: text,
              source: s.source,
              url: s.url,
              epistemic_state: 'SUPPORTED_GROWTH'
            });
            matched = true;
          }
        }

        if (!matched && UNRESOLVED_MARKERS.some(m => m.test(text))) {
          if (unresolved.length < 5) {
            unresolved.push({
              factor: text,
              catalyst: text,
              source: s.source,
              url: s.url,
              epistemic_state: 'UNVERIFIED_PENDING'
            });
          }
        }
      }

      return { positive, negative, unresolved };
    },

    extractQuantitativeIndicators(sentences) {
      const metrics = [];
      const seenVal = new Set();

      for (const s of sentences) {
        const matches = s.text.match(QUANTITATIVE_REGEX);
        if (matches) {
          for (const m of matches) {
            const clean = m.trim();
            if (!seenVal.has(clean) && clean.length > 1 && metrics.length < 8) {
              seenVal.add(clean);
              metrics.push({
                value: clean,
                context: s.text,
                source: s.source,
                publisher: s.publisher
              });
            }
          }
        }
      }

      return metrics;
    },

    computeChannelDispersion(evidence) {
      const counts = { regulatory: 0, news: 0, web: 0, social: 0, research: 0 };
      const items = Array.isArray(evidence) ? evidence : [];
      const total = items.length;

      if (total === 0) {
        return {
          regulatory_pct: 0,
          news_pct: 0,
          social_pct: 0,
          web_pct: 0,
          total_items: 0
        };
      }

      function getHostname(urlStr) {
        if (!urlStr || typeof urlStr !== 'string') return '';
        try {
          const parsed = new URL(urlStr.includes('://') ? urlStr : 'https://' + urlStr);
          return parsed.hostname.toLowerCase();
        } catch (_) {
          return '';
        }
      }

      for (const e of items) {
        const rawUrl = (e.url || '').toLowerCase();
        const host = getHostname(e.url) || (e.domain || e.publisher_host || '').toLowerCase();
        const pub = (e.publisher || e.domain || '').toLowerCase();

        const isRegulatory = host === 'sec.gov' || host.endsWith('.sec.gov') || pub.includes('edgar') || pub.includes('regulatory') || rawUrl.includes('sec.gov');
        const isSocial = host === 'twitter.com' || host.endsWith('.twitter.com') ||
                         host === 'x.com' || host.endsWith('.x.com') ||
                         host === 'reddit.com' || host.endsWith('.reddit.com') ||
                         host === 'youtube.com' || host.endsWith('.youtube.com');
        const isNews = !isRegulatory && !isSocial && (
          pub.includes('bbc') || pub.includes('reuters') || pub.includes('apnews') ||
          pub.includes('bloomberg') || host.includes('reuters.com') || host.includes('bloomberg.com') ||
          pub.includes('news')
        );

        if (isRegulatory) counts.regulatory++;
        else if (isSocial) counts.social++;
        else if (isNews) counts.news++;
        else counts.web++;
      }

      return {
        regulatory_pct: Math.round((counts.regulatory / total) * 100),
        news_pct: Math.round((counts.news / total) * 100),
        social_pct: Math.round((counts.social / total) * 100),
        web_pct: Math.round((counts.web / total) * 100),
        total_items: total
      };
    }
  };

  root.IntelligenceTransformer = IntelligenceTransformer;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = IntelligenceTransformer;
  }
})(typeof window !== 'undefined' ? window : this);

