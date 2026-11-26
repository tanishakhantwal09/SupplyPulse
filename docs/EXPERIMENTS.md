# SupplyPulse experiments (Stages 2-3)

Rules for every experiment (BUILD_PLAN sections 2 and 6):

- **Development set only** (435,889 events) for building and comparing. The held-out set (186,810 events) is
  loaded only through `experiments.common.load_held_out(..., purpose="final_evaluation")`, and only for the final
  detection-accuracy score. Nothing is tuned on it.
- **Gate setting is explicit.** Every experiment states `enforce_gate=True/False` (a required `--gate` flag
  for the ablation) and the setting is saved in its result file. This is separate from the pipeline policy,
  where the gate is enforced for live GDELT events only.
- **Every result file** in `experiments/results/` records the git commit, seed (42), dataset split, gate setting,
  model and key constants (`experiments/common.py: run_metadata`).
- **No numbers from memory.** Published values come only from the PDFs (`experiments/published_values.json`).
- Static port utilisation (`ports.json`) is used so results are reproducible; live PortWatch values change daily.

## Stage 2a (no LLM)

| Script | What it does | Data | Status |
|---|---|---|---|
| `experiments/common.py` | Loaders, held-out guard, seeded sampling, gate filter, result writer | — | built, tested |
| `experiments/gap_ablation.py` | Gap 1 ablation: nearest port vs score without BPR vs SupplyPulse (split + BPR), plus BPR without split. Over-capacity share, BPR delay, M/G/1 wait, CO2 / EU ETS, gate split | development | built, tested, smoke-run only (2,000 events) |
| `experiments/labelling_kit.py` | Cohen's kappa between the two reviewers; gate precision / recall / F1 against agreed labels; severity baseline | 100 held-out events (final evaluation) | built, tested; waiting for labels |
| `experiments/published_comparison.py` | C1-C4 comparison from `published_values.json` | PDFs | built; all values empty until copied from PDFs |
| `experiments/llm_number_check.py` | Every number in an LLM text must come from that agent's prompt and be described as the right thing (split plan vs single-port option) | run output | built, tested |

### Gap ablation: method

For each event, the alternates of its port are taken from `ports.json`. Ships are spread over the event,
`ships per day = vessels / max(duration_days, 1)`.

| Strategy | Ships go to |
|---|---|
| A `nearest` | all to the nearest usable alternate (Haversine) |
| B `score_no_bpr` | all to the best port by 0.40 risk + 0.35 raw delay + 0.25 cost |
| C `supplypulse` | split by free capacity; BPR-adjusted delays (the pipeline) |
| D `bpr_no_split` | all to the best port by the same score with BPR delay for all ships (extra ablation) |

Metrics, weighted by ships and then by events:
- **Over-capacity share**: ships sent to a port with V/C > 1.
- **BPR delay**: ship-weighted BPR-adjusted sailing time, U.S. Bureau of Public Roads (1964), alpha 0.15, beta 4.
- **M/G/1 wait**: Pollaczek–Khinchine, `Wq = λ·E[S²] / (2(1 − ρ))`, `E[S²] = (1 + cs²)·E[S]²`. Each port is one
  server with service rate = `vessel_capacity` per day (ASSUMPTION); arrivals = current load + diverted ships per day.
  `cs² = 1.0` is an **ASSUMPTION** (exponential service, the M/M/1 case) until the Rauca et al. (2025) PDF gives a value.
  Unstable queues (ρ ≥ 1) are reported as a share of ships, and the mean wait is over stable ports only.
- **CO2 and EU ETS cost**: `agents/carbon.py` (Directive (EU) 2023/959), with the event year for the phase-in.

Because utilisation is static and vessels / duration follow the dataset rules, the result depends only on
(port, severity, vessels, duration, year). Each distinct case is computed once and weighted by its number of events.

**Known design issue found while building (to discuss):** the split shares ships by free capacity and ignores distance.
For Shanghai it sends 120 ships to Singapore (5.84 d), so the split plan's ship-weighted delay (3.03 d) is worse than
sending all ships to Busan (2.46 d), although the split avoids overloading Busan (V/C 0.99 vs 1.69). A true
Wardrop (1952) user equilibrium would equalise delay across the ports used. Strategy D shows this trade-off.

### Proposed full runs (waiting for approval)

| Run | Command | Events | Distinct cases | Seed |
|---|---|---|---|---|
| 1, primary | `python3 -m experiments.gap_ablation --gate enforce` | 13,332 (gate PROCEED) | 852 | 42 (no sampling) |
| 2, sensitivity | `python3 -m experiments.gap_ablation --gate off --name gap_ablation_gate_off` | 435,889 (all) | 3,221 | 42 (no sampling) |

## Stage 2b (LLM, not started)

`agents/architectures.py`, `experiments/architecture_benchmark.py`, `experiments/llm_vs_code_decision.py`.
Groq budget: a confirmation run used 3,047 tokens (2,068 in, 979 out); the free tier is 200K tokens per day.
