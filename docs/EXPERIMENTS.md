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
| `experiments/gap_ablation.py` | Gap 1 ablation: eight strategies (nearest, score without BPR, free-capacity split, user equilibrium = SupplyPulse, system optimal, BPR without split). Over-capacity share, travel time, port time, system total time, M/G/1 wait, CO2 / EU ETS, gate split | development | built, tested; not yet run at full size |
| `experiments/labelling_kit.py` | Cohen's kappa between the two reviewers; gate precision / recall / F1 against agreed labels; severity baseline | 100 held-out events (final evaluation) | built, tested; waiting for labels |
| `experiments/published_comparison.py` | C1-C4 comparison from `published_values.json` | PDFs | values filled from the PDFs with page and table (28 Nov 2026); status COMPLETE; values not given by a paper are marked `not_in_paper` |
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

### A2: capacity-constrained equilibrium (since 28 Nov 2026, SupplyPulse's plan)

BPR has no hard capacity limit, but the M/G/1 queue is unstable at utilisation ≥ 1, so the two models disagreed
above capacity. SupplyPulse now uses a **utilisation ceiling RHO_MAX = 0.95 (ASSUMPTION: keeps M/G/1 stable; no source)**:
each congested link takes at most `L_i + x_i <= RHO_MAX · C_i`, so `x_i(T) = min(uncapped x_i(T), RHO_MAX·C_i − L_i)`
(0 if the link is already at or above the ceiling). Open-ocean bypass routes have no cap. Ports below the ceiling share
one travel time T; a port at the ceiling may be faster (t_i < T); unused ports have t_i(0) ≥ T. If demand is larger
than the total capped room and no bypass route exists, the ships that fit are assigned and the rest is reported as
**excess demand (ships waiting)**: never hidden, never forced over the cap, and not priced (no sourced waiting-cost model).
The uncapped user equilibrium and system optimum are kept as ablation strategies, plus a capped system optimum.

Shanghai (manual scenario, 350 ships over 144 h = 58.33 ships/day, p_i = 1.0 d, static utilisation, no LLM).
Per-port columns are Busan / Shenzhen / Singapore; M/G/1 wait in hours:

| Strategy | Ships per port | % of capacity | BPR port time (d) | M/G/1 wait | Avg travel time | Avg port time | Max utilisation | Excess demand | CO2 (t) |
|---|---|---|---|---|---|---|---|---|---|
| capped UE (main) | 96 / 103 / 96 | 95% / 95% / 95% | 1.122 / 1.122 / 1.122 | 8.0 h / 6.3 h / 4.9 h | 3.731 d | 1.122 d | 95% | 55 ships (9.11/day) | 18,326 |
| uncapped UE | 259 / 91 / 0 | 143% / 92% / 78% | 1.623 / 1.108 / 1.056 | unstable / 3.9 h / 0.9 h | 2.746 d | 1.489 d | 143% | 0 | 10,467 |
| capped SO | 96 / 103 / 96 | 95% / 95% / 95% | 1.122 / 1.122 / 1.122 | 8.0 h / 6.3 h / 4.9 h | 3.731 d | 1.122 d | 95% | 55 ships (9.11/day) | 18,326 |
| uncapped SO | 184 / 166 / 0 | 121% / 109% / 78% | 1.319 / 1.216 / 1.056 | unstable / unstable / 0.9 h | 2.637 d | 1.270 d | 121% | 0 | 11,385 |
| free-capacity split | 109 / 121 / 120 | 99% / 99% / 99% | 1.143 / 1.144 / 1.146 | 37.4 h / 33.7 h / 34.1 h | 3.823 d | 1.144 d | 99% | 0 | 22,312 |
| all-to-Busan | 350 / 0 / 0 | 169% / 71% / 78% | 2.233 / 1.038 / 1.056 | unstable / 0.8 h / 0.9 h | 3.356 d | 2.233 d | 169% | 0 | 9,353 |

Times are averaged over the ships that are assigned, so capped and uncapped rows are not directly comparable on time
(the capped rows leave 55 ships waiting). Shanghai's demand exceeds the total capped room (49.2 ships/day), so all three
ports fill to the ceiling and the capped UE equals the capped SO.

RHO_MAX sensitivity of the main plan:

| RHO_MAX | Ships (B / Sh / Si) | % of capacity | Excess demand | Avg travel time | Max M/G/1 wait |
|---|---|---|---|---|---|
| 0.90 | 78 / 82 / 68 | 90% / 90% / 90% | 122 ships (20.26/day) | 3.598 d | 3.8 h |
| 0.95 | 96 / 103 / 96 | 95% / 95% / 95% | 55 ships (9.11/day) | 3.731 d | 8.0 h |
| 0.98 | 106 / 116 / 113 | 98% / 98% / 98% | 15 ships (2.42/day) | 3.793 d | 20.6 h |

### Gap ablation: method

For each event, the alternates of its port are taken from `ports.json`. Ships are spread over the event,
`ships per day = vessels / max(duration_days, 1)`.

| Strategy | Ships go to |
|---|---|
| `nearest` | all to the nearest usable alternate (Haversine) |
| `score_no_bpr` | all to the best port by 0.40 risk + 0.35 sailing time + 0.25 cost |
| `free_capacity_split` | in proportion to free daily capacity (the old split; ignores distance) |
| `user_equilibrium` | uncapped Wardrop user equilibrium (ablation) |
| `capped_user_equilibrium` | **SupplyPulse**: capacity-constrained user equilibrium, ceiling RHO_MAX = 0.95 |
| `system_optimal` | uncapped Wardrop system optimum (ablation) |
| `capped_system_optimal` | capacity-constrained system optimum, ceiling RHO_MAX = 0.95 |
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
- **Excess-demand share**: ships per day that do not fit under the ceiling and wait (capped strategies only).
- **Max utilisation**: highest V/C of any congested link receiving ships.
- **Limitation:** M/G/1 assumes a steady state; a 6-day surge is not a steady state, so the waits are indicative only.

Because utilisation is static and vessels / duration follow the dataset rules, the result depends only on
(port, severity, vessels, duration, year). Each distinct case is computed once and weighted by its number of events.

### A3: candidate ports and waiting ships (since 28 Nov 2026)

**Candidate ports.** The hand-made 3-port `alternate_ports` lists left out obvious ports (Shanghai never got
Ningbo-Zhoushan, 82 nm away). For a disrupted **cargo port**, the candidates are now every cargo port within
**1,500 nm (ASSUMPTION: about 3.75 days at 400 nm/day; no source)**, excluding the disrupted port; if fewer than
**3 (ASSUMPTION)** are inside the radius, the nearest cargo ports are added (Santos and Lagos have none within 1,500 nm;
Callao, Durban and Cape Town have one). For a disrupted **canal, strait or bypass route** the alternative is a
different route, so its hand-made list (with the bypass routes) is kept (ASSUMPTION, no source).

**Waiting ships** (Newell, G.F. (1982), *Applications of Queueing Theory*, 2nd ed., deterministic queueing).
With diverted arrivals λ ships/day, room under the ceiling μ ships/day and event length D days (λ > μ, no bypass):

- **E = (λ − μ) · D** is the number of ships that **cannot be placed immediately** and wait at anchorage;
- **W = λ · D / (2μ)** is the average wait of a waiting ship;
- **total waiting = E × W ship-days**, which is the area between the cumulative arrival and departure curves
  (checked numerically in `tests/test_queueing.py`);
- the average wait over all diverted ships is E × W / (λ · D) = (λ − μ) · D / (2μ).

ASSUMPTIONS: arrivals spread evenly; after the event the ports keep the same room μ; first-in first-out; waiting
ships then sail to the same ports in proportion to the placed flow. **Every time average is over ALL ships**
(waiting ships included), so all strategies are compared over the same ships; "ships waiting" and "average wait of
waiting ships" are reported separately.

### Shanghai check (manual scenario, 350 ships over 144 h, 1,500 nm candidates, p_i 1.0 d, RHO_MAX 0.95, static utilisation, no LLM)

Candidates: Ningbo-Zhoushan (82 nm), Busan, Guangzhou, Shenzhen, Osaka-Kobe, Tokyo-Yokohama, Ho Chi Minh City.

| Strategy | Ships per port | Max utilisation | Ships waiting | Avg travel time, all ships | Avg port time | Over-capacity share | Unstable-queue share | CO2 (t) |
|---|---|---|---|---|---|---|---|---|
| capped UE (main) | Ningbo 101, Busan 96, Guangzhou 78, Shenzhen 75 | 95% | 0 | 2.193 d | 1.109 d | 0.00 | 0.00 | 9,016 |
| uncapped UE | Ningbo 350 | 144% | 0 | 1.858 d | 1.653 d | 1.00 | 1.00 | 1,705 |
| capped SO | Ningbo 101, Busan 96, Guangzhou 66, Shenzhen 63, Osaka 24 | 95% | 0 | 2.199 d | 1.101 d | 0.00 | 0.00 | 9,131 |
| uncapped SO | Ningbo 233, Busan 107, Guangzhou 10 | 121% | 0 | 1.786 d | 1.259 d | 0.67 | 0.67 | 4,384 |
| free-capacity split | all 7 ports | 87% | 0 | 2.653 d | 1.072 d | 0.00 | 0.00 | 13,175 |
| all-to-Ningbo (nearest) | Ningbo 350 | 144% | 0 | 1.858 d | 1.653 d | 1.00 | 1.00 | 1,705 |
| all-to-Busan | Busan 350 | 169% | 0 | 3.356 d | 2.233 d | 1.00 | 1.00 | 9,353 |

With a 500 nm radius (fallback gives Ningbo, Busan, Guangzhou; room 49.5 ships/day for 58.3/day) the capped UE leaves
**53 ships waiting, 3.54 d each**, average travel time of all ships 2.642 d. Radius 1,000 / 1,500 / 2,000 nm all give
the same Shanghai plan (no waiting, 2.193 d).

### Full gap ablation (development set, seed 42, no sampling, static utilisation)

Result files in `experiments/results/`: `gap_ablation.json` (gate enforced, main), `gap_ablation_gate_off.json.gz`
(gate off; gzip-compressed to keep the repository small), `gap_ablation_radius_1000.json`,
`gap_ablation_radius_2000.json`, `gap_ablation_scv_0.04.json`. Every file records its configuration (git commit,
gate setting, radius, RHO_MAX, p_i, service-time SCV, capacities marked ASSUMPTION).

**Run 1, gate enforced: 13,272 events, 852 distinct cases** (the expected count after comparing the unrounded gate
score; 13,332 and 13,338 were rounding artefacts). Means are event-weighted; "waiting share" is ship-weighted.

| Strategy | Over-capacity share | Unstable-queue share | Avg travel time, all ships | Avg port time | Waiting-ship share | Avg wait of waiting ships | M/G/1 wait (stable ports) | Max utilisation | CO2 (t) |
|---|---|---|---|---|---|---|---|---|---|
| nearest | 0.991 | 0.991 | 11.654 d | 10.052 d | 0 | – | 0.744 d | 2.28 | 5,103 |
| score without BPR | 0.931 | 0.931 | 9.096 d | 7.372 d | 0 | – | 0.348 d | 2.16 | 5,450 |
| free-capacity split | 0.392 | 0.392 | 3.947 d | 1.200 d | 0 | – | 0.364 d | 1.01 | 8,588 |
| uncapped UE | 0.825 | 0.825 | 3.929 d | 1.998 d | 0 | – | 0.405 d | 1.63 | 6,382 |
| **capped UE (SupplyPulse)** | **0** | **0** | 4.137 d | 1.070 d | 0.231 | 3.407 d | 0.735 d | 0.95 | 8,265 |
| uncapped SO | 0.577 | 0.577 | 3.583 d | 1.299 d | 0 | – | 7.493 d | 1.27 | 7,516 |
| capped SO | 0 | 0 | 4.137 d | 1.064 d | 0.231 | 3.407 d | 0.647 d | 0.94 | 8,278 |
| BPR without split | 0.931 | 0.931 | 8.966 d | 6.860 d | 0 | – | 0.348 d | 2.02 | 6,355 |

**Run 2, gate off: 435,889 events, 3,221 distinct cases.**

| Strategy | Over-capacity share | Unstable-queue share | Avg travel time, all ships | Avg port time | Waiting-ship share | Avg wait of waiting ships | M/G/1 wait (stable ports) | Max utilisation | CO2 (t) |
|---|---|---|---|---|---|---|---|---|---|
| nearest | 0.845 | 0.845 | 6.151 d | 4.545 d | 0 | – | 0.275 d | 1.65 | 1,886 |
| score without BPR | 0.759 | 0.759 | 5.216 d | 3.466 d | 0 | – | 0.515 d | 1.57 | 2,031 |
| free-capacity split | 0.133 | 0.133 | 3.812 d | 1.069 d | 0 | – | 0.289 d | 0.86 | 3,124 |
| uncapped UE | 0.730 | 0.730 | 3.376 d | 1.618 d | 0 | – | 0.258 d | 1.37 | 2,232 |
| **capped UE (SupplyPulse)** | **0** | **0** | 3.487 d | 1.048 d | 0.164 | 2.518 d | 0.606 d | 0.93 | 2,903 |
| uncapped SO | 0.495 | 0.495 | 3.179 d | 1.183 d | 0 | – | 60.413 d | 1.13 | 2,587 |
| capped SO | 0 | 0 | 3.488 d | 1.042 d | 0.164 | 2.518 d | 0.541 d | 0.92 | 2,907 |
| BPR without split | 0.752 | 0.752 | 5.284 d | 3.318 d | 0 | – | 0.513 d | 1.51 | 2,271 |

Reading: the uncapped strategies send 13–99 % of ships into ports above capacity (unstable M/G/1 queues); the capped
plans never do, at the price of 16–23 % of ships waiting about 2.5–3.4 days. The uncapped system optimum's M/G/1 wait at
its stable ports is very large because many of them sit just below ρ = 1.

**Radius sensitivity (SupplyPulse, gate enforced):**

| Radius | Avg travel time, all ships | Waiting-ship share | Avg wait of waiting ships | CO2 (t) |
|---|---|---|---|---|
| 1,000 nm | 4.209 d | 0.271 | 3.524 d | 8,080 |
| 1,500 nm (main) | 4.137 d | 0.231 | 3.407 d | 8,265 |
| 2,000 nm | 4.148 d | 0.199 | 3.488 d | 8,547 |

**Service-time spread (Cs) sensitivity (gate enforced).** Main setting SCV = 1.0 (ASSUMPTION). Rauca et al. use
Cs = 0.2 for a bulk pier (Logistics 9, 122, 2025, p. 16), i.e. SCV = 0.04; it does not transfer directly to container
ports, so it is a sensitivity only. Changing Cs changes **only the M/G/1 waiting time** (for SupplyPulse
0.735 d → 0.382 d; uncapped SO 7.493 d → 3.896 d). Over-capacity share, unstable-queue share, travel and port time,
waiting ships and CO2 are identical, as expected: the allocation does not use the M/G/1 model.

## Stage 2b (LLM, not started)

`agents/architectures.py`, `experiments/architecture_benchmark.py`, `experiments/llm_vs_code_decision.py`.
Groq budget: a confirmation run used 3,047 tokens (2,068 in, 979 out); the free tier is 200K tokens per day.
