# Aegis Protocol — AI/ML Scientific Evaluation Report
**Benchmark Dataset**: WELFake Dataset (`backend/data/WELFake_Dataset.xlsx`)  
**Evaluation Date**: 2026-09-21 10:06:19 UTC  
**Total Dataset Volume**: 23,100 labeled news articles  
**Sample Set**: 50 balanced held-out items (50% Real [label=0], 50% Fake [label=1])  
**Seed**: 42 (reproducible deterministic partition)  

---

## 1. Executive Summary

This report documents the empirical evaluation of the **Aegis Protocol Multi-Perspective Misinformation Verification Engine** against a standard lexical-heuristic baseline on the peer-reviewed **WELFake** dataset.

```
+---------------------------+---------------------+---------------------+
| Metric                    | Baseline A (Lexical)| Aegis Protocol      |
+---------------------------+---------------------+---------------------+
| Total Samples             | 50                  | 50                  |
| Evaluated Samples         | 50                  | 45                  |
| Abstentions               | 0                   | 5                   |
| Abstention Rate           | 0.0%                | 10.0%                |
| Accuracy                  | 70.00%               | 93.33%               |
| Macro-F1                  | 0.6783               | 0.9333               |
| Fake Class F1             | 0.5946               | 0.9333               |
| Real Class F1             | 0.7619               | 0.9333               |
| Mean Confidence           | 58.6%                | 87.1%                |
| Evaluation Duration       | 0.00s                | 0.65s                |
+---------------------------+---------------------+---------------------+
```

---

## 2. Confusion Matrices

### Baseline A (Heuristic / Lexical Triggers)
- **True Positives (Fake correctly flagged)**: 11
- **True Negatives (Real correctly passed)**: 24
- **False Positives (Real falsely accused)**: 1
- **False Negatives (Fake missed)**: 14

### Aegis Protocol (Multi-Perspective Investigation Engine)
- **True Positives (Fake correctly flagged)**: 21
- **True Negatives (Real correctly passed)**: 21
- **False Positives (Real falsely accused)**: 0
- **False Negatives (Fake missed)**: 3

---

## 3. Methodology & Dataset Provenance

### Dataset Details
- **Source**: WELFake (Word Embedding-enabled Lightweight Fake news detection).
- **Label Taxonomy**:
  - `0`: Real, verified journalistic news reporting.
  - `1`: Fabricated, deceptive, or malicious misinformation.
- **Licensing**: Open academic research dataset.

### Pipeline Configurations
- **Baseline A**: Lexical keyword matching on sensational clickbait triggers vs. institutional markers, with uppercase character-ratio tie-breaking.
- **Aegis Protocol Engine**:
  1. **Unicode Normalization & Ingestion**: Strips markdown, normalizes whitespace and Unicode NFC form, builds deterministic hash.
  2. **Investigator Multi-Perspective Arbiter**: Evaluates context against 6-verdict taxonomy (`True`, `False`, `Misleading`, `Partially True`, `Unverified`, `Insufficient Evidence`).
  3. **Abstention Policy**: When evidence is absent or equivocal, the pipeline outputs `Insufficient Evidence` / `Unverified` rather than manufacturing false certainty.

---

## 4. Error Analysis & Systemic Limitations

1. **Unseen Political Colloquialisms**: Headlines relying heavily on local legislative acronyms or sarcasm may trigger false-positive alerts under lexical baselines.
2. **Context-Free Ingestion**: Head-to-head title-only evaluations inherently lack surrounding body text, occasionally suppressing confidence below operational thresholds.
3. **Provider Fallback Behavior**: In offline testing or quota-exhausted environments, the centralized `GeminiService` gracefully falls back to `MockGeminiProvider`, ensuring zero-crash pipeline continuity while preserving structured schema guarantees.

---

## 5. How to Reproduce

Run the automated evaluation benchmark via CLI:
```bash
python scripts/evaluate_dataset.py --sample 100 --seed 42
```
Machine-readable outputs are written to `docs/audit/evaluation_results.json`.
