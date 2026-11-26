# Retired figures

These numbers were produced by the old code. They are kept in the repo so nothing is hidden,
but **they must not be reported** in the paper, the dashboard or a presentation.

| Figure | Where it appears | Why it is retired |
|---|---|---|
| Rerouting F1 **0.974** (precision 0.95, recall 1.0, accuracy 0.967) | `experiments/results/formal_evaluation.json`, `experiments/formal_evaluation.py`, `generate_graphs.py` (fallback) | **Circular.** The "ground truth" `decision_reroute` was written by `enrich_gdelt.py` as `severity in ['critical','high']`, and the pipeline decides with the same rule. It measures the rule against itself. |
| F1 0.967 / baseline 0.812 / "port accuracy 90%" | old `dev_dashboard/src/pages/Evaluation.jsx` (removed in Stage 1) | Typed in by hand. They do not even match the result files (which say F1 0.974 and plan correctness 0.467). |
| Rule-baseline F1 0.857 | `experiments/results/brintrup_baseline.json` | Same circular labels. |
| Cost per analysis **$0.0009** | `formal_evaluation.json`, `brintrup_baseline.json`, both scripts, `generate_graphs.py` | **ASSUMPTION, not measured:** 1,500 tokens × 4 calls × $0.15 per million tokens. |
| Cost per analysis $0.0006, "99.9% savings", "1,000× faster" | old `Evaluation.jsx` (removed) | Typed in by hand, no basis. |
| Comparison with Brintrup/AlMahri 2026 (F1 0.962–0.991, $0.0836, 229.8 s) | `brintrup_baseline.json`, `formal_evaluation.json` | Preprint (arXiv:2601.09680): disclosed reference only, never evidence (BUILD_PLAN section 2). |
| Confidence 91% / 82% / 71% (and 93/88/84/92% on the dashboard) | old orchestrator and dashboard; still in the dataset column `decision_confidence` | Fixed by severity, not calculated. Replaced by the signal gate (`agents/confidence.py`). |

## What replaces them

- **Detection accuracy:** 100 held-out events labelled by two reviewers (Tanisha and Mirza); Cohen's kappa for label
  reliability, then precision, recall and F1 of the gate against those labels (Stage 2-3, `experiments/labelling_kit.py`).
- **Cost per analysis:** measured token counts from `llm_usage` in every run result
  (`agents/llm_utils.py`, `USAGE`), multiplied by a dated, cited Groq price.
- **Comparison with published systems:** peer-reviewed C1-C4 in `experiments/published_comparison.py` (Stage 2-3).

Each retired result file carries a `_status` block saying the same thing.
