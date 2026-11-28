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
- **Response times: cold and warm runs are reported separately.** Every run result has `timing_condition`:
  `portwatch` = `cold` (a utilisation was fetched live from PortWatch in that run), `warm` (all from the local cache)
  or `static`, and `llm_client` = `new` (Groq client created in that run), `reused` or `disabled`.
  Use `experiments.common.split_by_timing(results)`; never average cold and warm runs together.

## Stage 2a (no LLM)

| Script | What it does | Data | Status |
|---|---|---|---|
| `experiments/common.py` | Loaders, held-out guard, seeded sampling, gate filter, result writer | — | built, tested |
| `experiments/gap_ablation.py` | Gap 1 ablation: six strategies (nearest, score without BPR, free-capacity split, user equilibrium = SupplyPulse, system optimal, BPR without split). Over-capacity share, travel time, port time, system total time, M/G/1 wait, CO2 / EU ETS, gate split | development | built, tested; not yet run at full size |
| `experiments/labelling_kit.py` | Cohen's kappa between the two reviewers; gate precision / recall / F1 against agreed labels; severity baseline | 100 held-out events (final evaluation) | built, tested; waiting for labels |
| `experiments/published_comparison.py` | C1-C4 comparison from `published_values.json` | PDFs | built; all values empty until copied from PDFs |
| `experiments/llm_number_check.py` | Every number in an LLM text must come from that agent's prompt and be described as the right thing (split plan vs single-port option) | run output | built, tested |

### Ship allocation model (since 28 Nov 2026)

SupplyPulse allocates diverted ships by a **Wardrop (1952) user equilibrium** (`agents/wardrop.py`).
Travel time of a diverted ship at receiving link i, with x_i diverted ships per day:

`t_i(x_i) = s_i + p_i · (1 + 0.15 · ((L_i + x_i) / C_i)^4)`

| Symbol | Meaning | Source |
|---|---|---|
| s_i | sailing time = Haversine great-circle distance / 400 nm per day | distance from ports.json coordinates (great-circle, so shorter than real sea routes: ASSUMPTION); speed ASSUMPTION |
| p_i | free-flow port time: 1.0 day for ports, 1.0 day transit + normal queue for canals/straits | **ASSUMPTION**, no source yet; results are sensitive to it (table below) |
| L_i | ships already at the port per day = current utilisation × capacity | ASSUMPTION (BUILD_PLAN 5, calibrate port capacities) |
| C_i | full daily capacity (vessel_capacity) | ASSUMPTION (same) |
| 0.15, 4 | BPR alpha, beta | U.S. Bureau of Public Roads (1964), Traffic Assignment Manual |

Every port used has the same travel time T; every unused port has t_i(0) ≥ T. T is found by bisection
(tolerance max(1e-9 days, 1e-12·T), at most 200 iterations). Every ship is assigned, even above total capacity.
**Open-ocean bypass routes** (port_type `alternate_route`: Cape of Good Hope Route, Lombok Strait, Cape Horn Route)
are uncongested: t_i = s_i, no capacity limit; if one is used, T = its s_i. **Canals and straits** (port_type
`chokepoint`: Suez Canal, Panama Canal, Strait of Malacca) are treated like ports.

The **system optimum** minimises the total time of all ships at the links (diverted + existing):
every port used has the same marginal time `s_i + p_i · (1 + 0.75 · v_i^4)`, v_i = (L_i + x_i)/C_i.

The recommended port is the port with the most ships. The 0.40 risk + 0.35 time + 0.25 cost score is shown for
comparison only and is not used for allocation.

### Gap ablation: method

For each event, the alternates of its port are taken from `ports.json`. Ships are spread over the event,
`ships per day = vessels / max(duration_days, 1)`.

| Strategy | Ships go to |
|---|---|
| `nearest` | all to the nearest usable alternate (Haversine) |
| `score_no_bpr` | all to the best port by 0.40 risk + 0.35 sailing time + 0.25 cost |
| `free_capacity_split` | in proportion to free daily capacity (the old split; ignores distance) |
| `user_equilibrium` | **SupplyPulse**: Wardrop user equilibrium |
| `system_optimal` | Wardrop system optimum |
| `bpr_no_split` | all to the best port by the same score, using travel time with all ships there |

Metrics (same definitions for every strategy), weighted by diverted ships and then by events:
- **Over-capacity share**: ships sent to a congested link with V/C > 1.
- **Travel time**: sailing + BPR port time. **Port time**: p_i · (1 + 0.15 · v^4); 0 on open-ocean bypasses.
- **System total time**: ship-days per day of all ships at the receiving links (diverted + existing). The system
  optimum is guaranteed to be lowest on this measure (tested).
- **M/G/1 wait**: Pollaczek–Khinchine, `Wq = λ·E[S²] / (2(1 − ρ))`, `E[S²] = (1 + cs²)·E[S]²`. Each congested link is one
  server with service rate = `vessel_capacity` per day (ASSUMPTION); arrivals = current load + diverted ships per day.
  `cs² = 1.0` is an **ASSUMPTION** (exponential service, the M/M/1 case) until the Rauca et al. (2025) PDF gives a value.
  Unstable queues (ρ ≥ 1) are reported as a share of ships; the mean wait is over stable links only. Open-ocean bypasses
  have no queue.
- **CO2 and EU ETS cost**: `agents/carbon.py` (Directive (EU) 2023/959), with the event year for the phase-in.

Because utilisation is static and vessels / duration follow the dataset rules, the result depends only on
(port, severity, vessels, duration, year). Each distinct case is computed once and weighted by its number of events.

### Shanghai check (manual scenario, 350 ships over 144 h, static utilisation, p_i = 1.0 day, no LLM)

| Strategy | Ships (Busan / Shenzhen / Singapore) | % of capacity | Ship-weighted travel time | Ship-weighted port time | System total time | CO2 (t) |
|---|---|---|---|---|---|---|
| user equilibrium | 259 / 91 / 0 | 143% / 92% / 78% | 2.746 d | 1.489 d | 356.16 | 10,467 |
| system optimal | 184 / 166 / 0 | 121% / 109% / 78% | 2.637 d | 1.270 d | 343.73 | 11,385 |
| free-capacity split | 109 / 121 / 120 | 99% / 99% / 99% | 3.823 d | 1.144 d | 409.16 | 22,312 |
| all-to-Busan | 350 / 0 / 0 | 169% / 71% / 78% | 3.356 d | 2.233 d | 411.55 | 9,353 |

Sensitivity of ship-weighted travel time to p_i (ships Busan / Shenzhen / Singapore):

| p_i | user equilibrium | system optimal | free-capacity split | all-to-Busan |
|---|---|---|---|---|
| 0.5 d | 2.162 (331 / 19 / 0) | 1.988 (204 / 146 / 0) | 3.251 (109 / 121 / 120) | 2.240 (350 / 0 / 0) |
| 1.0 d | 2.746 (259 / 91 / 0) | 2.637 (184 / 166 / 0) | 3.823 (109 / 121 / 120) | 3.356 (350 / 0 / 0) |
| 2.0 d | 3.969 (214 / 136 / 0) | 3.905 (173 / 177 / 0) | 4.967 (109 / 121 / 120) | 5.590 (350 / 0 / 0) |

**Open point:** the equilibrium accepts V/C above 1 (Busan 143%), because BPR has no hard capacity limit, while the
M/G/1 model calls any link with ρ ≥ 1 an unstable queue. The two congestion models disagree above capacity; to be
decided before the full ablation is reported.

### Proposed full runs (waiting for approval)

| Run | Command | Events | Distinct cases | Seed |
|---|---|---|---|---|
| 1, primary | `python3 -m experiments.gap_ablation --gate enforce` | 13,332 (gate PROCEED) | 852 | 42 (no sampling) |
| 2, sensitivity | `python3 -m experiments.gap_ablation --gate off --name gap_ablation_gate_off` | 435,889 (all) | 3,221 | 42 (no sampling) |

## Stage 2b (LLM, not started)

`agents/architectures.py`, `experiments/architecture_benchmark.py`, `experiments/llm_vs_code_decision.py`.
Groq budget: a confirmation run used 3,047 tokens (2,068 in, 979 out); the free tier is 200K tokens per day.
