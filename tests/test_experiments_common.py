"""experiments/common.py: held-out guard, explicit gate setting, result metadata."""
import json

import pandas as pd
import pytest

from experiments import common


def test_held_out_needs_explicit_final_evaluation_purpose():
    with pytest.raises(common.HeldOutAccessError):
        common.load_held_out(["event_id"])
    with pytest.raises(common.HeldOutAccessError):
        common.load_held_out(["event_id"], purpose="tuning")


@pytest.mark.parametrize("bad", [None, "yes", 1, 0])
def test_gate_setting_must_be_explicit_bool(bad):
    with pytest.raises(common.GateSettingError):
        common.require_gate_setting(bad)


def test_apply_gate_enforced_keeps_only_proceed():
    df = pd.DataFrame({"num_mentions": [60, 3], "goldstein_scale": [-8.0, -1.0], "avg_tone": [-9.0, -2.5]})
    assert len(common.apply_gate(df, enforce_gate=True)) == 1
    off = common.apply_gate(df, enforce_gate=False)
    assert len(off) == 2 and list(off["gate_action"]) == ["PROCEED", "REJECTED"]


def test_sample_is_seeded_and_reproducible():
    df = pd.DataFrame({"x": range(1000)})
    a, b = common.sample(df, 50), common.sample(df, 50)
    assert list(a["x"]) == list(b["x"]) and len(a) == 50
    assert common.sample(df, None) is df


def test_result_file_records_configuration(tmp_path):
    path = common.write_result("unit", {"value": 1}, {"enforce_gate": True, "dataset_split": "development"},
                               out_dir=tmp_path)
    data = json.loads(path.read_text())
    cfg = data["config"]
    assert cfg["enforce_gate"] is True and cfg["dataset_split"] == "development" and cfg["seed"] == 42
    assert cfg["git_commit"] and cfg["llm_model"] == "openai/gpt-oss-20b"
    assert cfg["constants"]["bpr_alpha"] == 0.15 and cfg["constants"]["gate_thresholds"] == [0.35, 0.60]


def test_result_file_refuses_missing_gate_setting(tmp_path):
    with pytest.raises(common.GateSettingError):
        common.write_result("unit", {}, {"dataset_split": "development"}, out_dir=tmp_path)


def test_result_file_refuses_unknown_split(tmp_path):
    with pytest.raises(ValueError):
        common.write_result("unit", {}, {"enforce_gate": False, "dataset_split": "whatever"}, out_dir=tmp_path)


def test_response_times_are_split_cold_and_warm():
    runs = [{"total_response_time_seconds": t, "timing_condition": {"portwatch": pw, "llm_client": c}}
            for t, pw, c in [(9.0, "cold", "new"), (2.0, "warm", "reused"), (3.0, "warm", "reused"),
                             (2.5, "warm", "reused")]]
    s = common.split_by_timing(runs)
    assert s["portwatch=cold, llm_client=new"]["runs"] == 1
    warm = s["portwatch=warm, llm_client=reused"]
    assert warm["runs"] == 3 and warm["median_seconds"] == 2.5 and warm["max_seconds"] == 3.0
