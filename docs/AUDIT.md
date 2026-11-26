# SupplyPulse audit of `main` (commit 47a021e)

Date: 26 Nov 2026. Branch audited: `main` at `47a021e` (the same code is the starting point of `major-project`).
How: read the code, plus offline checks only. **No code was changed and no Groq/LLM call was made.** The Shanghai and Suez numbers below come from running `main`'s own cost functions with PortWatch switched off (static utilisation) and no LLM call.

Legend: **PASS** = fine as it is. **FAIL** = must be fixed before results are reported. **UNCLEAR** = cannot be decided from the code alone.

---

## Summary

| # | Checklist item (BUILD_PLAN §6) | Result |
|---|---|---|
| 1 | It runs (requirements, tests, API, dashboard build) | **FAIL** |
| 2a | BPR formula and its constants | **FAIL** |
| 2b | Capacity split across receiving ports | **FAIL** |
| 2c | M/G/1 queue | **FAIL** (missing) |
| 2d | Confidence gate weights and thresholds | **FAIL** |
| 2e | EU ETS coverage, phase-in, price source | **FAIL** |
| 2f | Haversine distance | **PASS** |
| 3 | No fabricated or hard-coded numbers | **FAIL** |
| 4 | No data leakage; fixed, reproducible split | split **PASS**, leakage **UNCLEAR** |
| 5 | The LLM never decides a number | **FAIL** |
| 6 | Robustness (429, PortWatch down, unknown port, zero capacity, empty feed, bad LLM output) | **FAIL** (2 of 6 pass) |
| 7 | Reproducibility (seeds, results + config saved) | **FAIL** |
| 8 | Cost model gives plausible outputs | **FAIL** |
| §5.1 | Shanghai 74 days / USD 94B | **FAIL** (cause found, see below) |
| §5.2 | Cost constants have no source | **FAIL** |
| §5.3 | Cost per analysis is measured | **FAIL** |
| §5.4 | Dashboard hard-coded values | **FAIL** |
| §5.5 | Any results from real data | **FAIL** (none valid) |

---

## 1. It runs — FAIL

| Check | Result | Evidence | Why |
|---|---|---|---|
| `requirements.txt` exists | FAIL | no file at repo root | A fresh venv cannot be set up from the repo. |
| Offline test suite passes | FAIL | no `tests/` folder; `pytest` not installed in `venv/` | There are no tests to run. |
| API starts | FAIL | only `dev_dashboard/server.py` (plain `http.server`); no `api/main.py` | The FastAPI backend in the spec does not exist on `main` (FastAPI is installed in the venv but unused). |
| Dashboard builds | FAIL | `node node_modules/vite/bin/vite.js build` → "Cannot find native binding … @rolldown/binding-wasm32-wasi" | The installed `node_modules` is broken (also `node_modules/.bin/vite` is not executable). This is an install problem, probably fixed by a clean `npm ci`; the source code itself was not tested. |

## 2. Formulas match the cited papers

### 2a. BPR — FAIL
- `agents/route_optimization_agent.py:55-78`: `delay × (1 + α·(V/C)^β)` with **α = 1.5, β = 4.0**.
- The standard BPR function (Bureau of Public Roads, 1964) uses **α = 0.15, β = 4**. The docstring (line 67) says α = 1.5 is "calibrated for maritime … 10× more severe", but no calibration or source exists. It is an invented number.
- The docstring cites **Wardrop (1952)** as the BPR reference (line 69). Wardrop is the user-equilibrium principle, not the BPR function. The citation is wrong.
- Also: the formula is applied to a **travel-time** term (`distance / 400` nm per day, line 93), not to port waiting time. The 400 nm/day (≈16.7 knots) has no source.

### 2b. Capacity split — FAIL
- `agents/route_optimization_agent.py:138-141`: vessels are shared out in proportion to free slots (`capacity − current load`).
- Units do not match: `vessels_affected` is a **total for the whole event** (350 for a critical mega-hub, `enrich_gdelt.py:110`), but `vessel_capacity` is described as **vessels per day** (`agents/portwatch_client.py:71`). So one day of port capacity is asked to absorb a multi-day event. This is the root cause of issue §5.1.
- When a port is above 100 % utilisation its free slots are 0, so it gets 0 vessels and the others get everything (with cached PortWatch data, Shenzhen gets 298 vessels for a capacity of 72).
- There is no cap at real capacity and no overflow handling, and the split is not a Wardrop equilibrium, so the "Wardrop" label does not apply.

### 2c. M/G/1 queue — FAIL (missing)
- Not present anywhere on `main` (grep for "M/G/1", "Pollaczek", "queue" finds nothing). It was planned for `experiments/gap_ablation.py`, which does not exist.

### 2d. Confidence gate — FAIL
- The gate exists only in `experiments/live_demo.py:44-91`. It is **not used** by the pipeline: `agents/langgraph_orchestrator.py:117-120` still gives fixed confidences of **91 % / 82 % / 71 %** based on severity alone.
- Weights 0.40/0.35/0.25 and thresholds 0.35/0.60 match the plan, but they have no source or "ASSUMPTION" label.
- The docstring (line 47) says it is "Based on Angelopoulos & Bates (2023) Conformal Prediction". BUILD_PLAN §2 says it is **not** a conformal method, so this wording must change.
- "Source credibility: distinct news mentions" uses GDELT `NumMentions` (column 31, line 60). Mentions are not distinct sources; `NumSources` (column 32) would match the description.
- `enrich_gdelt.py:157-160` also writes 0.91/0.82/0.71/0.58 into the dataset as `decision_confidence`.

### 2e. EU ETS — FAIL
- `agents/financial_auditor_agent.py:27-33, 55-73`: every voyage is charged at **100 %**, including voyages that never touch the EU (for example Shanghai → Busan is charged USD 656,589).
- No 50 % rule for extra-EU voyages, no phase-in (40 % in 2024, 70 % in 2025, 100 % from 2026), and no check of whether the route touches an EU port.
- EUA price €65 and EUR→USD 1.08 have no source or date. Fuel use 0.0191 t/nm has no source and is the same for every ship size.
- CO₂ factor 3.114 t CO₂ per t fuel is correct for heavy fuel oil (IMO MEPC.308(73)), but this is not cited in the code.
- `CII_RATING_IMPACT` (lines 35-40) maps severity to CII rating changes ("D → E operational ban risk"). It has no basis; CII depends on the ship's annual carbon intensity, not on event severity. This is an invented mapping.

### 2f. Haversine — PASS
- `agents/route_optimization_agent.py:47-53` and `enrich_gdelt.py:49-55`: correct formula with Earth radius 3440.065 nm.
- Note: the 800 nm cut-off for "nearest port" (`enrich_gdelt.py:58`) has no source; it needs an ASSUMPTION label.

## 3. No fabricated or hard-coded numbers — FAIL

| Where | Evidence | Why it fails |
|---|---|---|
| Orchestrator | `agents/langgraph_orchestrator.py:117-120` | Confidence 91/82/71 % comes from severity, not from any calculation. |
| Dev server | `dev_dashboard/server.py:125-143` | If the pipeline fails it returns a made-up Ningbo result (USD 382,000, 3.42 s, 91 %) and says `success: True`. |
| Dev server | `dev_dashboard/server.py:147-170` | `/api/fetch-live` always reports "3 new disruptions" and a fixed Red Sea event with a fake Reuters URL. Nothing is fetched. |
| Dashboard context | `dev_dashboard/src/context/SupplyPulseContext.jsx:10-45` | `calculatePipelineResult` invents distance, delay, costs, 93/88/84 % confidence and response time in the browser. |
| Overview page | `dev_dashboard/src/pages/Overview.jsx:26-29` | Defaults to 92 %, 3.42 s and Ningbo when no run exists. |
| Evaluation page | `dev_dashboard/src/pages/Evaluation.jsx:6-12, 28, 38` | F1 0.967, baseline 0.812, "1,000× faster", "$0.0006" are typed in by hand. |
| Telemetry page | `dev_dashboard/src/pages/Telemetry.jsx:7-11, 19-22` | Fixed latencies and token counts; says **gpt-oss-120b / "120B parameter scale"**, but the code uses **gpt-oss-20b**. |
| State / Trace / Pipeline / Explainability | `State.jsx:24,47`; `Trace.jsx:38`; `Pipeline.jsx:82-91,149`; `Explainability.jsx:14-24` | Fallback Ningbo, 92 %, 114.5 nm, 2.1 days. |
| Reference page | `dev_dashboard/src/pages/Reference.jsx:10` | A separate hand-typed port list instead of `ports.json`. |
| Dataset "decisions" | `enrich_gdelt.py:155` | `estimated_cost_usd` uses `np.random.uniform(8000, 25000)` with no seed. |
| Inventory | `agents/inventory_agent.py:56-62` | Containers per vessel depend on **severity** (800/400/200/100). A ship's size does not change with the news. No source. |

## 4. Data leakage and the split

- **Split — PASS.** `merge_enriched.py:32-36` shuffles with `random_state=42` and cuts 70/30. Parquet row counts match the plan exactly: 622,699 / 435,889 / 186,810. (The CSV → Parquet conversion script is not in the repo; add it so the full chain is reproducible.)
- Note: `split_dataset.py` is an older script that mixes in synthetic data. It does not match the Parquet files and should be marked as outdated.
- **Leakage — UNCLEAR.** No code tunes anything on the held-out set. But the held-out set is used for day-to-day development: `run_demo.py:10`, `agents/supervisor_agent.py:129-131`, `agents/langgraph_orchestrator.py:385`, `dev_dashboard/server.py:71,117` (the dashboard event list *is* the first 30 held-out events) and `experiments/formal_evaluation.py:15-24`. Looking at held-out events while developing is a leak risk, and demos should use the development set.
- **Circular labels — FAIL.** The "ground truth" `decision_reroute` is written by `enrich_gdelt.py:123` as `severity in ['critical','high']`, and the pipeline decides with the same rule (`agents/langgraph_orchestrator.py:90`). This is why the old F1 of 0.974 is meaningless.

## 5. The LLM never decides a number — FAIL

The final numbers in `pipeline_result.json` are computed by code (good). But the prompts ask the LLM to produce new numbers that appear in the output text:

| Agent | Evidence | Problem |
|---|---|---|
| Route | `agents/route_optimization_agent.py:251-255` | Asks for "RECOMMENDED PORT … and why" (so the LLM can name a different port than the code picked) and "CONFIDENCE: Percentage". |
| Supervisor | `agents/supervisor_agent.py:71-72` | Asks for a "preliminary alternate port" and an "overall RISK LEVEL". |
| Inventory | `agents/inventory_agent.py:164-166` | Asks for "Quantities", "regions" and "Days before shortage" — none of these are computed. |
| Financial | `agents/financial_auditor_agent.py:273-275` | Asks for "Insurance trigger Yes/No" and "expected savings". |

Also the Route prompt does not pass the BPR delay or congestion, so the LLM explains with raw delays (lines 242-249).

## 6. Robustness — FAIL (2 of 6 pass)

| Case | Result | Evidence | Why |
|---|---|---|---|
| Groq 429 | PASS (partly) | each agent, e.g. `supervisor_agent.py:46-56` | Waits 60 s, then 120 s, then gives up. Copied four times instead of shared. |
| Groq timeout / other errors | FAIL | `ChatGroq(...)` at e.g. `supervisor_agent.py:18-23` has no timeout; errors are re-raised | One failed call stops the whole pipeline, and the dev server then shows fake results. |
| PortWatch down | PASS | `agents/portwatch_client.py:152-155, 177-185` | Falls back to `ports.json`. Note: cached values up to 7 days old are still labelled "portwatch_live" (lines 101-106). |
| Long Beach PortWatch id | FAIL | `agents/portwatch_client.py:49-50` | Los Angeles and Long Beach both map to `port664`, so they always show the same live data. |
| Unknown port | FAIL | `route_optimization_agent.py:82-83`; `financial_auditor_agent.py:118` | No alternates → the LLM is still called with an empty list, and the cost model silently uses a made-up 2-day delay. |
| Unknown commodity / matching | FAIL | `agents/inventory_agent.py:48-49` | Substring matching: "chemicals" matches "Oil and **Petro**chemicals" first. No warning when nothing matches. |
| Zero-capacity alternative | FAIL | `route_optimization_agent.py:71-72` | Capacity 0 returns the raw delay, i.e. treats a full port as having **no** congestion. |
| Empty news feed | PASS in `live_demo.py:390-395`; FAIL in `dev_dashboard/server.py:147-170` | The script correctly stops, but the dashboard API invents a signal. |
| Malformed LLM output | UNCLEAR | outputs are never parsed | Nothing breaks because nothing is parsed, but empty or cut-off text is passed on unchecked. |

## 7. Reproducibility — FAIL
- Seeds: split is seeded (PASS); `enrich_gdelt.py:155` uses `np.random` with no seed (FAIL).
- Results: `experiments/*.py` write JSON to `experiments/results/`, but none save the configuration, git commit, model, or seed.
- `agents/pipeline_result.json` and `agents/pipeline_attribution.json` are overwritten by every run and are committed to git (they change on every run).

## 8. Cost model plausibility — FAIL

Reproduced offline from `main`'s own functions (static utilisation, 350 vessels for Shanghai and 500 for Suez, as set by `enrich_gdelt.py:110-113`):

**Shanghai, critical**

| Alternate | Distance | Vessels sent | Capacity/day | Load ÷ capacity | Raw delay | BPR delay |
|---|---|---|---|---|---|---|
| Busan (chosen) | 449 nm | 109 | 57 | 2.58 | 1.1 d | **74.1 d** |
| Shenzhen | 655 nm | 120 | 72 | 2.38 | 1.6 d | 78.0 d |
| Singapore | 2,057 nm | 120 | 94 | 2.05 | 5.1 d | 141.1 d |

| Cost part | `main` today |
|---|---|
| Rerouting | $12.7 M |
| Trade delay (uses **raw** 1.1 d × $850 M/day) | $935 M |
| Freight increase | $6.1 M |
| Inventory at risk (15 % of $43 B exposure) | **$6.45 B** |
| Operational | $52.5 M |
| EU ETS carbon (charged even though no EU port is involved) | $0.66 M |
| **Total** | **$7.45 B** |

- `main` does **not** price the BPR delay: `financial_auditor_agent.py:118` uses `estimated_delay_days` (raw). If the 74.1-day BPR delay is priced (which the Stage 1 "congestion-adjusted delay is priced" change did), the delay cost alone becomes **$63 B**, which is where the "74 days / USD 94 B" in BUILD_PLAN §5.1 comes from.
- **Suez, critical:** Cape of Good Hope gets 464 vessels against a "capacity" of 300/day → BPR 134 days; total $8.8 B on `main`, and the delay cost would be $114 B if BPR were priced.
- The $43 B inventory exposure is also implausible: 350 vessels × 800 containers × 90 % × $85,000+ per container (`inventory_agent.py:55-64`).
- **Root causes:** (1) whole-event vessel counts compared with per-day capacity; (2) α = 1.5 (10× the standard BPR); (3) containers per vessel tied to severity; (4) daily trade value by severity with no source.

---

## Section 5 open issues

| Issue | Result | Evidence | Why |
|---|---|---|---|
| 5.1 Shanghai 74 days / $94 B | **FAIL** | see §8 above | Reproduced: 74.1-day BPR delay for Busan. Caused by the units mismatch plus α = 1.5. |
| 5.2 Constants with no source | **FAIL** | `financial_auditor_agent.py:121-124` (daily trade $850M/$350M/$120M/$40M), `:129` (15 %), `:130` ($25,000/vessel/day), `route_optimization_agent.py:93` (400 nm/day), `:96` (severity multipliers 1.8/1.4/1.2/1.0), `:99` ($45/nm), `financial_auditor_agent.py:242-245` (alert thresholds), `enrich_gdelt.py:94-99, 108-118, 190-192` (freight %, vessels, durations) | None has a source comment or an "ASSUMPTION" label. |
| 5.3 Cost per analysis | **FAIL** | `experiments/formal_evaluation.py:88-92`, `experiments/brintrup_baseline.py:252` | Assumes 1,500 tokens × 4 calls × $0.15/M = $0.0009. Nothing is measured. The dashboard shows yet another value, $0.0006 (`Evaluation.jsx:12`). |
| 5.4 Dashboard hard-coded values | **FAIL** | see §3 table | Found in 8 pages/files plus the dev server. |
| 5.5 Results from real data | **FAIL** | `experiments/results/formal_evaluation.json` (F1 0.974, cost $0.0009) | The only real-data result uses circular labels and an assumed cost. `parametric_evaluation.py` uses made-up ports and α = 1.5. `paper_comparison.json` and `live_proof.json` are single demo runs. No result is usable in the paper. |

---

## What exists vs. what is missing (BUILD_PLAN §4a)

### Stage 1: honesty fixes
| Spec item | Status on `main` |
|---|---|
| Signal gate replaces fixed 91/82/71 % | **Missing** (gate only in `live_demo.py`; fixed values still in orchestrator) |
| Route LLM explains instead of choosing | **Missing** (prompt asks it to recommend + give confidence) |
| Risk term normalised to 0/0.5/1 | **Missing** (uses 0/1/2, `route_optimization_agent.py:163`) |
| Congestion-adjusted delay priced | **Missing** (raw delay priced) |
| EU ETS coverage and phase-in | **Missing** |
| Invented CII mapping removed | **Missing** (still present) |
| Whole-word commodity matching | **Missing** |
| Dev server: no fake Ningbo / 120B | **Missing** |
| Long Beach PortWatch id fixed | **Missing** |
| `agents/llm_utils.py` (get_llm, invoke_with_retry, USAGE, env switches) | **Missing** (retry copied in 4 files) |
| Financial Auditor prices capacity split per port | **Missing** |
| `agents/confidence.py`, `agents/carbon.py` | **Missing** |
| Partly there | BPR + proportional split exist; attribution lineage file exists (`langgraph_orchestrator.py:132-260`); PortWatch client with fallback exists |

### Stages 2-3: experiments
| Spec item | Status |
|---|---|
| `agents/architectures.py` | Missing |
| `experiments/gap_ablation.py` (with M/G/1) | Missing |
| `experiments/labelling_kit.py` | Missing (labelling CSVs and `experiments/labels.py` exist on branch `my-local-edits`) |
| `experiments/llm_vs_code_decision.py` | Missing |
| `experiments/architecture_benchmark.py` | Missing |
| `experiments/published_comparison.py` (C1-C4) | Missing (`brintrup_baseline.py` exists but compares against a preprint, which BUILD_PLAN §2 says must not be used as evidence) |
| `experiments/common.py`, `docs/EXPERIMENTS.md` | Missing |

### Stage 4: application
| Spec item | Status |
|---|---|
| `api/main.py` (FastAPI: /simulate, /runs, WS stream, /runs/{id}, /results) | Missing (only `dev_dashboard/server.py`) |
| `agents/simulation.py` | Missing |
| Dashboard /simulate page with Leaflet map | Missing (Leaflet not used on `main`) |
| Remove client fallback and hard-coded confidences; "no run yet" state; USER_SIMULATION marking | Missing |
| README, `requirements.txt`, `docs/CHANGELOG_MAJOR.md` | Missing |
| `tests/sample_events.py`, `tests/test_pipeline_offline.py` | Missing |

### Note on your local edits
Your saved edits on branch `my-local-edits` (max_tokens 700, "placeholder" confidence label, labelling files, `reference/` copies) are **not** on `major-project` yet, because `major-project` was cut from `main` as asked. They can be brought in during Stage 1.
