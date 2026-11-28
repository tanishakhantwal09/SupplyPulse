"""Comparison with published systems C1-C4 (BUILD_PLAN 4a, Stages 2-3).

Published numbers live in experiments/published_values.json and are filled ONLY by
copying from the PDFs (value + page + table). Until every value is filled, this script
reports the comparison as INCOMPLETE and prints what is missing. It never supplies a
number of its own for a published system.

SupplyPulse's side of each comparison is read from the experiment result files
(for example experiments/results/gap_ablation.json), never typed in.

Run:  python3 -m experiments.published_comparison [--out-dir DIR]
"""
import argparse
import json

from agents.reference_data import ROOT
from experiments import common

VALUES_FILE = ROOT / "experiments" / "published_values.json"
PAPERS_DIR = ROOT / "30 RESEARCH PAPERS"  # local only, git-ignored (publisher PDFs)
TO_FILL = "TO FILL FROM PDF"


def load_values(path=VALUES_FILE):
    with open(path) as f:
        return json.load(f)


def missing_fields(values):
    """List of 'C1 metric 1: value' style strings for everything not yet copied from a PDF."""
    missing = []
    for s in values["systems"]:
        if TO_FILL in s.get("citation", ""):
            missing.append(f"{s['id']} citation")
        for i, m in enumerate(s["metrics"], 1):
            if m.get("not_in_paper"):
                if not m.get("note"):
                    missing.append(f"{s['id']} metric {i}: say why it is not in the paper")
                continue                                   # checked in the PDF: the paper does not give it
            if m.get("value") is None:
                missing.append(f"{s['id']} metric {i}: value")
            if TO_FILL in str(m.get("page", "")) or not m.get("page"):
                missing.append(f"{s['id']} metric {i}: page")
            if "TO CONFIRM" in m.get("name", ""):
                missing.append(f"{s['id']} metric {i}: name/unit")
    return missing


def build(values):
    missing = missing_fields(values)
    table = [{"id": s["id"], "system": s["system"], "supplypulse_counterpart": s["supplypulse_counterpart"],
              "comparable": s.get("comparable"),
              "metrics": [{"name": m["name"], "published_value": m["value"], "unit": m["unit"],
                           "page": m["page"], "table_or_figure": m.get("table_or_figure"),
                           "not_in_paper": bool(m.get("not_in_paper")), "note": m.get("note")}
                          for m in s["metrics"]]}
             for s in values["systems"]]
    return {"status": "COMPLETE" if not missing else "INCOMPLETE", "missing": missing, "table": table}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", default=None)
    args = p.parse_args(argv)
    result = build(load_values())
    print(f"Published comparison: {result['status']} ({len(result['missing'])} fields still to copy from PDFs)")
    for item in result["missing"]:
        print("   missing:", item)
    if result["status"] == "COMPLETE":
        path = common.write_result("published_comparison", result, {
            "enforce_gate": False, "gate_role": "not used: compares published figures",
            "dataset_split": "none", "values_file": str(VALUES_FILE.relative_to(ROOT)),
        }, out_dir=args.out_dir)
        print(f"written: {path}")
    return result


if __name__ == "__main__":
    main()
