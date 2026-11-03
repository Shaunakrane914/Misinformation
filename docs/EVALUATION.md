# Evaluation and limitations

Aegis has several different evaluation tasks. Their metrics are not interchangeable.

| Task | Retained record | Scope |
| --- | --- | --- |
| Headline/article classification | [WELFake baseline](evaluation/results/welfake_classical_ml_4ad02c2.json) | Historical TF-IDF + logistic regression, 2,948 held-out examples: accuracy 0.885, macro-F1 0.885. This is not live claim-verification accuracy. |
| Candidate reranking | [Reranker baseline](evaluation/results/reranker_benchmark_4ad02c2.json) | Seven held-out queries with controlled candidate pools. MRR 0.20 to 1.00 in that small experiment; not a universal retrieval result. |
| Frozen retrieval regression | [Benchmark records](../artifacts/retrieval_benchmark/) | Reproducible fixture checks and historical comparisons; not independent live-source adjudication. |
| Application correctness | `tests/`, GitHub Actions | Offline extraction, routing, attribution, API and security behavior. Passing tests do not establish source availability. |
| Live usefulness | Subject-specific source and passage review | Requires actual bodies, relevant exact citations, dates, task sufficiency and honest abstention. No general accuracy score is claimed. |

Historical records retain their original revision and timestamp; this cleanup did
not rerun or improve those experiments. The WELFake sample and frozen retrieval
fixtures remain versioned for reproducibility. See [testing commands](TESTING.md).

## Current limitations

- Some subjects still yield only snippets, indexes, denied requests or stale bodies.
- Source assertions can be wrong; publisher counts do not prove independent support.
- Reported quotations do not authenticate the person or verify synthetic media.
- One temporal snapshot cannot establish trend acceleration or platform-wide reach.
- Bare entity names can be misframed by the shared allegation UI; executive summaries
  and authority/independence labels need further consistency work.
- Investigation history and visible-ID recovery require further verification.
- Research-lab simulations and statistical text features are not calibrated proof of
  authorship, factual truth or observed audience behavior.

Do not advertise production readiness, guaranteed truth or a useful-evidence
multiplier from these records. Report article-body words, selected cited words and
frontend words separately. Retain failures rather than replacing unknowns with zero.
