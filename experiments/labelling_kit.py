"""Detection accuracy against two human reviewers (BUILD_PLAN section 2, evaluation rules).

Input: experiments/labeling/label_sheet.csv, 100 HELD-OUT events (seed 42), with columns
annotator_1 (Tanisha) and annotator_2 (Mirza). Label codes:
    1 = real maritime / supply-chain disruption
    0 = not a disruption
    X = cannot be judged (dead link, no article): excluded and counted
Optional column 'adjudicated' (0/1) settles disagreements after discussion.

Steps:
  1. Label reliability: Cohen's kappa between the two reviewers (Cohen 1960) on rows both judged.
  2. Agreed labels: rows where both agree, plus adjudicated rows.
  3. Gate accuracy (pre-registered before any label is seen):
       PRIMARY   positive = gate action PROCEED (score >= 0.60)
       SECONDARY positive = MONITOR_AND_HOLD or PROCEED (score >= 0.35)
     precision, recall and F1 against the agreed labels.
  4. Severity check: crosstab of the rule-based severity against the agreed labels, and
     "severity is critical or high" scored as a baseline detector.

The held-out set is loaded with purpose='final_evaluation'. This is evaluation only:
nothing here may be used to change the gate or the severity rules.

Run:  python3 -m experiments.labelling_kit [--allow-partial]
"""
import argparse

import pandas as pd
from sklearn.metrics import cohen_kappa_score, f1_score, precision_score, recall_score

from agents import confidence
from agents.reference_data import ROOT
from experiments import common

LABEL_SHEET = ROOT / "experiments" / "labeling" / "label_sheet.csv"
VALID = {"0", "1"}
UNJUDGEABLE = "X"
HELD_OUT_COLUMNS = ["event_id", "severity", "num_mentions", "goldstein_scale", "avg_tone"]


class LabelsIncompleteError(RuntimeError):
    """Not every row has both reviewers' labels."""


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().upper()
    if s in ("1", "1.0"):
        return "1"
    if s in ("0", "0.0"):
        return "0"
    return s or None


def label_status(sheet):
    a1, a2 = sheet["annotator_1"].map(_clean), sheet["annotator_2"].map(_clean)
    return {"rows": int(len(sheet)), "annotator_1_filled": int(a1.notna().sum()),
            "annotator_2_filled": int(a2.notna().sum()),
            "both_filled": int((a1.notna() & a2.notna()).sum())}


def reliability(sheet):
    a1, a2 = sheet["annotator_1"].map(_clean), sheet["annotator_2"].map(_clean)
    both = a1.isin(VALID) & a2.isin(VALID)
    unjudgeable = int(((a1 == UNJUDGEABLE) | (a2 == UNJUDGEABLE)).sum())
    invalid = sorted((set(a1.dropna()) | set(a2.dropna())) - VALID - {UNJUDGEABLE})
    if invalid:
        raise ValueError(f"Unknown label codes: {invalid} (use 1, 0 or X)")
    x, y = a1[both].astype(int), a2[both].astype(int)
    kappa = float(cohen_kappa_score(x, y)) if len(x) and (x.nunique() > 1 or y.nunique() > 1) else None
    return {"rows_both_judged": int(both.sum()), "rows_unjudgeable": unjudgeable,
            "raw_agreement": float((x == y).mean()) if len(x) else None,
            "cohens_kappa": kappa, "disagreements": sheet.loc[both & (a1 != a2), "event_id"].astype(str).tolist()}


def agreed_labels(sheet):
    a1, a2 = sheet["annotator_1"].map(_clean), sheet["annotator_2"].map(_clean)
    label = pd.Series(pd.NA, index=sheet.index, dtype="object")
    agree = a1.isin(VALID) & (a1 == a2)
    label[agree] = a1[agree]
    if "adjudicated" in sheet.columns:
        adj = sheet["adjudicated"].map(_clean)
        use = adj.isin(VALID) & ~agree
        label[use] = adj[use]
    return sheet.assign(label=label)[["event_id", "label"]].dropna()


def _prf(y_true, y_pred):
    return {"precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "positives_true": int(sum(y_true)), "positives_predicted": int(sum(y_pred)), "n": int(len(y_true))}


def score(sheet, events):
    """events: held-out rows (event_id, severity, num_mentions, goldstein_scale, avg_tone)."""
    agreed = agreed_labels(sheet)
    merged = agreed.merge(events.assign(event_id=events["event_id"].astype(str)),
                          on="event_id", how="left", validate="one_to_one")
    if merged["severity"].isna().any():
        raise ValueError("Some labelled events are not in the held-out set")
    gates = merged.apply(lambda r: confidence.score_signal(r["num_mentions"], r["goldstein_scale"],
                                                           r["avg_tone"]), axis=1)
    action = pd.Series([g["action"] for g in gates], index=merged.index)
    y = merged["label"].astype(int).tolist()
    return {
        "n_agreed_labels": int(len(merged)),
        "gate_primary_PROCEED": _prf(y, (action == confidence.PROCEED).astype(int).tolist()),
        "gate_secondary_MONITOR_or_PROCEED": _prf(y, action.isin([confidence.PROCEED, confidence.MONITOR])
                                                   .astype(int).tolist()),
        "severity_baseline_critical_or_high": _prf(y, merged["severity"].isin(["critical", "high"])
                                                   .astype(int).tolist()),
        "severity_by_label": pd.crosstab(merged["severity"], merged["label"]).to_dict(orient="index"),
    }


def run(sheet, events, allow_partial=False):
    status = label_status(sheet)
    if status["both_filled"] < status["rows"] and not allow_partial:
        raise LabelsIncompleteError(f"Labels incomplete: {status}. Fill both columns, or pass allow_partial.")
    return {"label_status": status, "reliability": reliability(sheet), "detection": score(sheet, events)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--allow-partial", action="store_true")
    p.add_argument("--out-dir", default=None)
    args = p.parse_args(argv)
    sheet = pd.read_csv(LABEL_SHEET, dtype={"event_id": str})
    status = label_status(sheet)
    print("Label status:", status)
    if status["both_filled"] < status["rows"] and not args.allow_partial:
        print("Labels are not complete; nothing scored. (No held-out data was loaded.)")
        return None
    events = common.load_held_out(HELD_OUT_COLUMNS, purpose=common.FINAL_EVALUATION)
    events = events[events["event_id"].astype(str).isin(sheet["event_id"])]
    results = run(sheet, events, allow_partial=args.allow_partial)
    path = common.write_result("labelling_kit", results, {
        "enforce_gate": True, "gate_role": "the gate is the detector being scored",
        "dataset_split": "held_out_final_evaluation", "label_sheet": str(LABEL_SHEET.relative_to(ROOT)),
        "positive_rule_primary": "PROCEED", "positive_rule_secondary": "MONITOR_AND_HOLD or PROCEED",
    }, out_dir=args.out_dir)
    print(f"written: {path}")
    return results


if __name__ == "__main__":
    main()
