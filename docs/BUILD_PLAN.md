# SupplyPulse: build plan, decisions and handoff (single source of truth)

Last updated 26 Nov 2026. A new chat must read this whole file before doing anything. If anything here is wrong, Tanisha corrects it and this file is updated.

## 0. Where we are right now (read first)

- **Priority order (Tanisha, 26 Nov 2026):** the research paper is the real goal. It will be published, so the system must be correct and every result defensible. Interviews matter less; they are only about explaining and defending the project. Paper writing is ON HOLD until the project is complete.
- **Update 26 Nov 2026:** the major-project code (Stages 1 to 4) is **lost**. It is not on GitHub, not on Tanisha's Mac (Desktop, Documents, Downloads, zips searched) and not in the chat downloads. It will be rebuilt, using Section 4a as the specification.
- **Agreed next steps, in this order:**
  1. Save Tanisha's uncommitted local edits on a branch (Section 4b). Revoke the GitHub token that was stored in the git remote URL.
  2. **Audit the current `main`** (Section 6). Its failures become the checklist for the rebuild, so real problems are fixed once instead of rebuilding from memory and auditing afterwards. Report the audit as a list before changing anything.
  3. **Rebuild Stages 1 to 4** (Section 4a), fixing what the audit found, with a done-and-left list approved by Tanisha before each stage. Commit each stage separately on a `major-project` branch and push to GitHub after each stage, so nothing is lost again.
  4. Fix the cost model (Section 5, issue 1) as part of the rebuild.
  5. Finish building (Section 7), then run all experiments.
  6. Only then write the research paper (Section 8).
- Before building anything large, first list what is done and what is left, and wait for Tanisha's "yes".

## 1. What the project is

- **Title:** SupplyPulse: An Autonomous Multi-Agent LLM Framework for Real-Time Supply Chain Disruption Monitoring and Emergency Rerouting.
- **People:** B.Tech CSE, Amity University Noida. Team ARGO: Tanisha Khantwal (A2305223248, project manager, research, agent design) and Mirza Farman (A2305223245, backend, agents, frontend, testing). Guide: Dr. Dolly Sharma.
- **What it does:** a user sees a world shipping map and simulates a disruption (for example Shanghai closed by a typhoon), or one is detected from news. Within 30 seconds four agents return one rerouting plan:
  - **Supervisor:** assesses the event and coordinates.
  - **Route Optimization:** chooses alternative ports and routes, congestion-aware.
  - **Inventory:** works out exposed stock and how to reallocate it.
  - **Financial Auditor:** costs each option, including carbon.
- **Research claim:** existing work monitors OR reroutes; SupplyPulse does both in one coordinated multi-agent LLM pipeline, validated on real data. Always word it "in our search", never "none exist".
- **Target venue:** IEEE Access or Springer Nature Computer Science. IEEE two-column A4 format is applied last.
- **Repo:** github.com/tanishakhantwal09/SupplyPulse. Claude can now push to it directly (it was blocked on 3 Nov).

## 2. Decisions already made (do not reopen)

### LLM and agents
- **LLM:** openai/gpt-oss-20b on the Groq free tier (200K tokens a day, 8K tokens a minute). Retry wait of 60 s on HTTP 429. max_tokens: 700 for Supervisor and Inventory, 400 for Route and Financial.
- **Orchestration:** LangGraph. Deterministic code calculates every number; the LLM only writes the explanation (Gap 3). The Route LLM is given the code-selected port and explains it; it does not choose.

### Data
- **GDELT 2.0:** 3,251,756 raw events (2020 to 2026), stored as Parquet. master_enriched has 622,699 rows, split into 435,889 development and 186,810 held-out (validation_set_REAL_ONLY). The held-out set is never used for tuning.
- **Reference DBs:** 50 ports, 10 routes, 8 commodities.
- **Live congestion:** IMF PortWatch, with a static fallback.
- The Parquet files are on Tanisha's Mac, not in the repo.

### Research gaps
Each gap is tied to a cited paper and a measurable before/after.
- **Gap 1:** BPR congestion function (U.S. Bureau of Public Roads 1964) on port time, and ships allocated across receiving ports by a Wardrop (1952) user equilibrium (agents/wardrop.py; since 28 Nov 2026). The old free-capacity split is kept only as an ablation strategy.
- **Gap 2:** three-factor confidence gate with weights 0.40/0.35/0.25 and thresholds 0.35 and 0.60. Inspired by Angelopoulos and Bates 2023; it is NOT a conformal method.
  - **Gate policy (decided 26 Nov 2026):** thresholds stay 0.35/0.60. The gate is enforced for **live GDELT events only**. Manual scenarios (a user triggers a run from the dashboard, API or a script, including dataset events) always run; the gate score is still computed and shown, labelled "manual scenario – user-confirmed disruption".
  - All labelled events in experiments/labeling/ (random 100, targeted 50, maritime 40; no overlap) are from the **held-out** set: use them for evaluation only, never for designing rules.
- **Gap 3:** deterministic attribution lineage (Turpin et al., NeurIPS 2023).
- **Gap 7:** EU ETS carbon cost with Directive 2023/959 coverage and phase-in (Vaca-Cabrero et al. 2024 method), plus cost, carbon and time options.
- **Queued:** Arrhenius decay for perishables; geopolitical escalation tracking.

### Evaluation rules
- **Dr. Sharma's standards:**
  - Mathematically grounded novelty with measurable results matters more than the frontend.
  - The research paper must compare SupplyPulse with 2 to 3 published systems; this is the most important part.
  - The research paper's references may differ from the review paper's.
- **No preprints as evidence:** the Brintrup/AlMahri 2026 preprint stays only as a disclosed reference.
- **The old F1 of 0.974 is circular and retired.** Detection accuracy is reported only against 100 held-out events labelled by two reviewers (Tanisha and Mirza). Cohen's kappa shows the labels are reliable; precision, recall and F1 against those labels measure the system.
- **"Real-time":** say "evaluated on held-out historical events". Claim real-time only where the live GDELT/PortWatch feed is actually used.

### Storage and deployment (decided 26 Nov 2026)
- **PostgreSQL**, not MongoDB, using SQLAlchemy and Alembic.
  - Tables: ports, routes, commodities, runs, agent steps, options. LLM text and attribution records go in JSONB columns. Add indexes on the filter fields.
  - Add a Run History page in React.
- Parquet stays for the GDELT dataset.
- Add pytest tests for the maths (BPR, capacity split, ETS, confidence gate) and the API.
- Docker Compose, then deploy:
  - frontend on Vercel
  - backend on Render
  - free Neon or Supabase PostgreSQL
  - a cached replay mode for when Groq rate-limits
  - the deployed version uses the reference data and a small held-out sample, not the full dataset
- These come after the research-critical work (Section 0).
- No Node.js backend: Node is only tooling (npm, Vite). MongoDB is left for a future separate project.

### Working style
- Simple wording; Tanisha dislikes complicated phrasing.
- Give complete files, not diffs.
- Her setup: macOS, zsh, venv, python3/pip3.
- Never pass low_memory to read_parquet.
- Fix push rejections with `git pull origin main --rebase`.

## 3. Tech stack (current)

- **Frontend:** React 19, Vite, Tailwind CSS, Leaflet. JavaScript (JSX), about 3,700 lines.
- **Backend:** Python 3, FastAPI (/simulate, /runs, /runs/{id}, /results), WebSocket progress stream, Uvicorn. About 6,300 lines of Python, including the pipeline and experiments.
- **AI:** LangGraph; Groq API (openai/gpt-oss-20b).
- **Data:** GDELT 2.0, IMF PortWatch, pandas, Parquet, JSON reference files.
- **Tools:** Git/GitHub, .env for keys, Jupyter (EDA), npm, pip.
- **Planned:** PostgreSQL, pytest, Docker, Vercel/Render.

## 4. Code status and recovery

- **GitHub main** is at 47a021e (last push 26 Sep 2026).
- **The major-project work is three commits on branch major-project:**
  - a8770bf Stage 1: honesty and correctness fixes
  - 5ff2581 Stage 2-3: gap experiments, architecture variants, published comparison
  - f583b0b Stage 4: FastAPI + WebSocket backend and map simulator
- **These commits are NOT on GitHub.** They were delivered on 3 Nov as `supplypulse-major-project.patch` (plus a git bundle). The cloud workspace that held them has been reset.
- **To recover, on Tanisha's Mac:**
  1. `mdfind -name "supplypulse-major-project"` (finds the patch file).
  2. `find ~ -maxdepth 3 -type d -name "SupplyPulse*" 2>/dev/null`
  3. In each folder: `git branch -a && git log --oneline -5`
- **If the patch file exists:** attach it to the chat. Claude applies it with `git am` on a new major-project branch and pushes.
- **If the commits are already on her Mac:** run `git push origin major-project`.
- **If neither:** rebuild Stages 1 to 4 from Section 4a.

### 4b. Tanisha's Mac (checked 26 Nov 2026)
- The repo is `~/Desktop/Minor project` (the Downloads copy no longer exists), on `main` at 47a021e (same as GitHub), with no `major-project` branch.
- **Uncommitted local edits to keep:** max_tokens raised from 400 to 700, the confidence relabelled as "placeholder", and new labelling files. Save them first: `git checkout -b my-local-edits && git add -A && git commit -m "Local edits before rebuild"`.
- **Security:** the git remote URL contained a GitHub personal access token in plain text. It is not in any committed file. Revoke it at github.com/settings/tokens, then run `git remote set-url origin https://github.com/tanishakhantwal09/SupplyPulse.git`.

### 4a. What the three commits contain (now the rebuild specification)

**Stage 1: honesty fixes** — **DONE 26 Nov 2026** on branch `major-project` (commits 92cc44f to the Stage 1 tests commit; audit in docs/AUDIT.md, retired figures in docs/RETIRED.md). Extra items agreed with Tanisha and also done: approved local edits merged; requirements.txt + README "How to run"; BPR set to the standard alpha 0.15 / beta 4 (U.S. Bureau of Public Roads 1964) and diverted ships spread over max(duration_days, 1); dashboard hand-typed values removed or labelled demo; model name gpt-oss-20b; F1 0.974 and $0.0009 marked RETIRED; run outputs untracked (sample in docs/sample_run/); 73 pytest tests. EU ETS berth emissions are marked "not modelled" (ASSUMPTION). Shanghai, critical, 350 ships: Busan BPR delay 74.1 d → 1.26 d.
- Severity-fixed 91/82/71% confidence replaced by the signal gate.
- Route LLM explains instead of choosing.
- Risk term normalised to 0/0.5/1.
- Congestion-adjusted delay is priced.
- EU ETS coverage and phase-in.
- Invented CII mapping removed.
- Whole-word commodity matching (fixes "chemicals" matching Petrochemicals).
- Dev server no longer returns fabricated Ningbo/Suez results or claims 120B.
- Long Beach PortWatch id fixed.
- Shared agents/llm_utils.py: get_llm, invoke_with_retry, USAGE token counter, and switches SUPPLYPULSE_NO_LLM, SUPPLYPULSE_QUIET, SUPPLYPULSE_STATIC_UTIL, SUPPLYPULSE_NO_SAVE, SUPPLYPULSE_FAKE_LLM_SECONDS.
- Financial Auditor prices the capacity split per receiving port (cost and CO2 summed, delay weighted by vessels).
- New files: agents/confidence.py, agents/carbon.py.

**Stages 2 and 3: experiments** (documented in docs/EXPERIMENTS.md)
- *Status 26 Nov 2026:* Item 0 (LLM reasoning effort 'low', truncation flagged and not retried, port names for Inventory, split-plan vs single-port labels, number-and-wording check) **done**. **Stage 2a built and tested, not yet run at full size:** experiments/common.py, gap_ablation.py (with M/G/1; service-time SCV is an ASSUMPTION until the Rauca PDF), labelling_kit.py (waiting for the two reviewers' labels), published_comparison.py (all values empty, 'TO FILL FROM PDF'). Stage 2b (LLM) not started.
- *Status 28 Nov 2026 (Part A, Wardrop):* **done.** agents/wardrop.py solves the user equilibrium and the system optimum (bisection, bypass routes uncongested); SupplyPulse's plan is the user equilibrium; recommended port = most ships; the score is comparison only; delay priced as ship-weighted travel time; the free-capacity split is an ablation; gap_ablation has six strategies. Capacity inputs labelled ASSUMPTION. Part B (Groq check run, full ablation runs) waits for Tanisha's yes.
- **agents/architectures.py:** sequential, parallel (Route and Inventory together) and hierarchical (the supervisor picks agents by severity).
- **experiments/gap_ablation.py:** no LLM. Compares nearest-port vs score-without-BPR vs SupplyPulse, judged by over-capacity share and an M/G/1 queue (Rauca et al. 2025); also the carbon trade-off and the gate split.
- **experiments/labelling_kit.py:** 100 events, two reviewers, kappa, gate P/R/F1, severity check.
- **experiments/llm_vs_code_decision.py:** LLM-decides vs code-decides, in the style of Jannelli et al. This is the evidence for "why use LLM agents at all".
- **experiments/architecture_benchmark.py**
- **experiments/published_comparison.py:**
  - C1 Wen / Rauca
  - C2 Vaca-Cabrero
  - C3 Sun et al. 2026, Table 10 values
  - C4 Jannelli
- Shared code in experiments/common.py.

**Stage 4: application**
- **api/main.py (FastAPI):** POST /simulate builds an event for any of the 50 ports using the same rules as the dataset enrichment (agents/simulation.py). POST /runs runs a dataset event. WS /runs/{id}/stream sends one message as each agent finishes. GET /runs/{id} returns the plan and attribution record. GET /results serves the experiment results. Failed runs are reported as failed.
- **Dashboard /simulate page:** Leaflet map of the 50 ports and 10 routes, simulator form, live agent timeline, and the plan (ship allocation, scored ports, six cost parts, ETS coverage, options).
- **Honesty fixes on the dashboard:**
  - The client-side fallback (calculatePipelineResult) and the hard-coded confidences (92/93/88/84%) are removed.
  - Pages show "no run yet" until a real run finishes.
  - User-simulated events are marked USER_SIMULATION, and the news-signal gate is shown as not applicable for them.
- **Docs and tests:** README, requirements.txt, docs/CHANGELOG_MAJOR.md, tests/sample_events.py, tests/test_pipeline_offline.py.

## 5. Known open issues

1. **Cost model:** default vessel counts (for example 350 for a critical mega-hub) exceed the alternative ports' vessel_capacity, so BPR delays and the trade-delay cost explode. A Shanghai simulation gives a 74-day delay and about USD 94 billion. Calibrate vessel counts, capacities and daily trade values against published figures. This must be fixed before any result is reported.
   - *Status 26 Nov 2026 (Stage 1):* the delay blow-up is fixed (standard BPR alpha, ships spread per day): Shanghai now gives a ship-weighted delay of 3.0 days and a total of USD 9.1 B. **Still open:** USD 6.4 B of that is "inventory at risk", driven by 800 containers per vessel tied to severity and unsourced values; daily trade value (USD 850 M/day) is also unsourced. These are labelled ASSUMPTION and still need calibration (Section 7, item 1).
   - *Observation (development set, not tuned):* with the fixed 0.35/0.60 thresholds only 3% of development events reach PROCEED (11% of "critical" ones). To be discussed before Stage 2-3; thresholds must not be tuned on the held-out set.
2. **Cost constants** are still assumptions: daily trade value, 45 USD/nm, 15% inventory risk, 25,000 USD per vessel per day. Each needs a source or must be labelled as an assumption in the paper.
   - **Calibrate port capacities** (logged 28 Nov 2026): vessel_capacity = max(20, round(TEU × 2.5)), the 2.5 factor, the floor of 20 (25 of 44 cargo ports sit on it), annual_teu_millions (source not recorded), the baseline utilisation formula and the 6 hand-set chokepoint values are all ASSUMPTION (labelled in build_reference_databases.py). They drive BPR, the Wardrop equilibrium and the M/G/1 queue, so they need dated sources before results are reported.
   - **Port risk rating is no longer used in allocation** (28 Nov 2026): ships are allocated by Wardrop user equilibrium on travel time only; the 0.40/0.35/0.25 risk/delay/cost score is shown for comparison only. Decide later whether to exclude high-risk ports.
   - **Free-flow port time p_i = 1.0 day** (ports and canals) is an ASSUMPTION with no source; results are sensitive to it (see docs/EXPERIMENTS.md).
3. **Cost per analysis** is now measured from token counts (USAGE). The old $0.0009 figure is not measured and must not be used.
4. **Older dashboard pages** may still contain hard-coded demo values. The audit must find and remove them. *Done in Stage 1 (26 Nov 2026).*
   - **Irrelevant news in the development set** (logged 28 Nov 2026): development events include irrelevant news tagged critical (e.g. a Multan crime story → USD 3.98 B). The enrichment rules (enrich_gdelt.py: tone/mention filter, nearest port within 800 nm, rule-based severity) need fixing; plan an experiment (e.g. measure the share of off-topic events on a development-set sample, then test a relevance filter) before results are reported. Never tune it on the held-out set.
   - **Inventory reallocation ports ignore the disruption location** (logged 28 Nov 2026): agents/inventory_agent.py uses the first 2 primary_import_ports of each commodity from commodities.json, which are the same for every event (a Mundra event sends chemicals to Los Angeles / New York). A location-aware rule is proposed; waiting for Tanisha's decision.
5. **No results have been produced on the real dataset yet** (all experiments are pending).

## 6. Audit checklist (next chat, step 2)

Check each item and report pass, fail or unclear, with file and line references.

1. **It runs:** fresh venv, `pip3 install -r requirements.txt`, the offline test suite passes, the API starts, the dashboard builds.
2. **Formulas match the cited papers:**
   - BPR (alpha and beta values and their source)
   - capacity split across receiving ports
   - M/G/1 queue
   - confidence gate weights and thresholds
   - EU ETS coverage (50% for extra-EU voyages), phase-in (40% for 2024, 70% for 2025, 100% from 2026) and price source
   - Haversine distance for the nearest port
3. **No fabricated or hard-coded numbers** anywhere in the agents, API or dashboard. Every number shown must come from a calculation or a cited constant.
4. **No data leakage:** the held-out set is not used in tuning or rule design; the development/held-out split is fixed and reproducible.
5. **The LLM never decides a number:** check each agent's prompt and output parsing.
6. **Robustness:**
   - Groq 429 and timeouts
   - PortWatch down (fallback)
   - unknown port or commodity
   - zero-capacity alternatives
   - empty news feed (NFR2: no event without a real signal)
   - malformed LLM output
7. **Reproducibility:** fixed random seeds; every experiment writes its results and configuration to experiments/results/.
8. **The cost model gives plausible outputs** (issue 1) on 3 to 5 known disruptions, for example Shanghai 2022 and Suez 2021.

## 7. Remaining build work (after the audit fixes)

1. Fix and calibrate the cost model; document every constant's source.
2. Run the experiments on Tanisha's Mac (dataset and Groq key are there). Claude gives the exact commands; she sends back the result files.
   1. gap_ablation and published_comparison (no LLM).
   2. Tanisha and Mirza label 100 events; run the labelling_kit score.
   3. llm_vs_code_decision and architecture_benchmark with the Groq key, on separate days if the daily limit is hit.
3. Commit all results and generate the paper figures from them.
4. Add PostgreSQL, pytest, Docker and the deployment (Section 2, storage and deployment).

## 8. Research paper (after the project is complete)

- **Built around:**
  - the gap results (ablation)
  - the comparison with published systems C1 to C4 (at least 2 to 3 strong ones)
  - detection accuracy against the 100 labelled events
  - LLM-vs-code evidence
  - architecture comparison
  - response time and measured cost per analysis
- **Rules:**
  - Peer-reviewed sources only.
  - British spelling; no Oxford comma unless needed.
  - Simple wording.
  - Facts, numbers and citations exactly as in the sources.
  - "In our search" wording for the novelty claim.
  - IEEE format applied last.
- **Separate from the review paper:** "Multi-Agent and LLM-Based Maritime Disruption Response: A Review" (Khantwal, Farman, Sharma), finished 4 Nov 2026; see claude/literature-review-handoff.md.

## 9. Other deliverables already finished (for context)

- **Minor project (7th semester):** report submitted 26 Oct 2026; viva 3 Nov 2026 (done).
- **SPM project plan (TEAM_ARGO_PROJECT_PLAN.docx):** one whole project of 28 working weeks:
  - 10 Aug to 30 Oct 2026, semester break 2 Nov 2026 to 1 Jan 2027 (not counted), then 4 Jan to 23 Apr 2027
  - 22 activities A to V
  - critical path 140 days
  - lab-file cover page, index and page borders added
  - still needs the Amity logo and the SPM teacher's name on the cover
- **Timeline on record:** 8th-semester work runs January to April 2027: implementation, experiments, graphs, paper.
