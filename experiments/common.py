"""Shared code for the Stage 2-3 experiments.

Rules enforced here (BUILD_PLAN sections 2 and 6):
- The development set is the default. The held-out set (186,810 events) can only be
  loaded with purpose="final_evaluation"; it is never used for tuning or choosing.
- Every result file records its configuration: git commit, seed, dataset split,
  the gate setting (which must be given explicitly), model and key constants.
"""
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from agents import carbon, confidence, llm_utils
from agents import route_optimization_agent as route
from agents.reference_data import DATA_DIR, ROOT

SEED = 42  # Fixed seed for every sample (BUILD_PLAN 6, item 7). Same seed as the 70/30 split.
DEV_FILE = DATA_DIR / "training_set.parquet"
HELD_OUT_FILE = DATA_DIR / "validation_set_REAL_ONLY.parquet"
RESULTS_DIR = ROOT / "experiments" / "results"
FINAL_EVALUATION = "final_evaluation"


class HeldOutAccessError(PermissionError):
    """The held-out set was requested without purpose='final_evaluation'."""


class GateSettingError(ValueError):
    """An experiment did not state the gate setting explicitly."""


def load_dev(columns=None):
    return pd.read_parquet(DEV_FILE, columns=columns)


def load_held_out(columns=None, *, purpose=None):
    if purpose != FINAL_EVALUATION:
        raise HeldOutAccessError(
            "The held-out set is only for the final evaluation. "
            f"Call load_held_out(..., purpose='{FINAL_EVALUATION}') and say so in the result file.")
    return pd.read_parquet(HELD_OUT_FILE, columns=columns)


def sample(df, n, seed=SEED):
    """Seeded random sample of n rows (all rows if n is None or >= len(df))."""
    if n is None or n >= len(df):
        return df
    return df.sample(n=n, random_state=seed)


def require_gate_setting(enforce_gate):
    if not isinstance(enforce_gate, bool):  # 1 == True in Python, so check the type
        raise GateSettingError("Every experiment must set enforce_gate=True or False explicitly.")
    return enforce_gate


def apply_gate(df, enforce_gate):
    """Gate scores for every row; if enforce_gate, keep only rows the gate says PROCEED to."""
    require_gate_setting(enforce_gate)
    scores = df.apply(lambda r: confidence.score_signal(r["num_mentions"], r["goldstein_scale"], r["avg_tone"]),
                      axis=1)
    out = df.assign(gate_score=[g["score"] for g in scores], gate_action=[g["action"] for g in scores])
    if enforce_gate:
        out = out[out["gate_action"] == confidence.PROCEED]
    return out


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def run_metadata(config):
    """Configuration block saved in every result file."""
    require_gate_setting(config.get("enforce_gate"))
    if config.get("dataset_split") not in ("development", "held_out_final_evaluation", "none"):
        raise ValueError("config['dataset_split'] must be 'development', 'held_out_final_evaluation' or 'none'")
    return {
        **config,
        "seed": config.get("seed", SEED),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "llm_model": llm_utils.MODEL_NAME,
        "llm_enabled": not llm_utils.no_llm(),
        "constants": {
            "bpr_alpha": route.BPR_ALPHA, "bpr_beta": route.BPR_BETA,
            "gate_weights": confidence.WEIGHTS,
            "gate_thresholds": [confidence.REJECT_BELOW, confidence.PROCEED_FROM],
            "eua_price_eur": carbon.EUA_PRICE_EUR,
        },
    }


def write_result(name, results, config, out_dir=None):
    """Write experiments/results/<name>.json with results and full configuration."""
    out_dir = Path(out_dir) if out_dir else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    payload = {"experiment": name, "config": run_metadata(config), "results": results}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return path
