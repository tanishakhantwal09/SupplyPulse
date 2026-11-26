# SupplyPulse

An autonomous multi-agent LLM framework for supply chain disruption monitoring and emergency rerouting.
Four agents (Supervisor, Route Optimization, Inventory, Financial Auditor) are coordinated with LangGraph.
Deterministic code calculates every number; the LLM (openai/gpt-oss-20b on Groq) only writes the explanation.

The full plan and all decisions are in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md). The audit of the old code is in [docs/AUDIT.md](docs/AUDIT.md).

## How to run

Requirements: macOS or Linux, Python 3.14, Node.js 20 or newer.

### 1. Python setup

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Create a `.env` file in the project root with your Groq key (never commit it):

```
GROQ_API_KEY=your-key-here
```

### 2. Data

The GDELT Parquet files (`dataset/final/*.parquet`) are not in the repo. Copy them into `dataset/final/`.
The reference data (50 ports, 10 routes, 8 commodities) is in `dataset/reference/`.

### 3. Run the tests (no Groq key or dataset needed)

```bash
python3 -m pytest
```

### 4. Run the pipeline on one event

```bash
python3 -m agents.langgraph_orchestrator
```

### 5. Dashboard

```bash
python3 dev_dashboard/server.py
```

In a second terminal:

```bash
cd dev_dashboard
npm ci
npm run dev
```

## Switches (environment variables)

| Variable | Effect |
|---|---|
| `SUPPLYPULSE_NO_LLM=1` | Skip every LLM call; the explanation text says "LLM disabled". Numbers are unchanged. |
| `SUPPLYPULSE_QUIET=1` | Hide console tables. |
| `SUPPLYPULSE_STATIC_UTIL=1` | Use the static port utilisation in `ports.json` instead of IMF PortWatch. |
| `SUPPLYPULSE_NO_SAVE=1` | Do not write `agents/pipeline_result.json` or `agents/pipeline_attribution.json`. |
| `SUPPLYPULSE_FAKE_LLM_SECONDS=<n>` | With `SUPPLYPULSE_NO_LLM`, wait n seconds per call to imitate LLM latency (for timing tests only). |

## Team

Team ARGO, Amity University Noida: Tanisha Khantwal and Mirza Farman. Guide: Dr. Dolly Sharma.
