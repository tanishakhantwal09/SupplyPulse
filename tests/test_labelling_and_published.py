"""Labelling kit (kappa, gate P/R/F1) on made-up labels, and the published-values guard."""
import copy

import pandas as pd
import pytest

from experiments import labelling_kit as lk
from experiments import published_comparison as pc


def _sheet(a1, a2, adjudicated=None):
    d = {"event_id": [str(i) for i in range(len(a1))], "annotator_1": a1, "annotator_2": a2}
    if adjudicated is not None:
        d["adjudicated"] = adjudicated
    return pd.DataFrame(d)


def _events(n):
    # first half strong signal (PROCEED), second half weak (REJECTED)
    strong = [(60, -8.0, -9.0)] * (n // 2)
    weak = [(3, -1.0, -2.5)] * (n - n // 2)
    rows = strong + weak
    return pd.DataFrame({"event_id": [str(i) for i in range(n)],
                         "severity": ["critical"] * (n // 2) + ["low"] * (n - n // 2),
                         "num_mentions": [r[0] for r in rows], "goldstein_scale": [r[1] for r in rows],
                         "avg_tone": [r[2] for r in rows]})


def test_kappa_perfect_and_chance():
    assert lk.reliability(_sheet(["1", "0", "1", "0"], ["1", "0", "1", "0"]))["cohens_kappa"] == pytest.approx(1.0)
    # agreement no better than chance -> kappa 0
    r = lk.reliability(_sheet(["1", "1", "0", "0"], ["1", "0", "1", "0"]))
    assert r["cohens_kappa"] == pytest.approx(0.0) and r["raw_agreement"] == 0.5


def test_unjudgeable_rows_are_excluded_and_counted():
    r = lk.reliability(_sheet(["1", "X", "0"], ["1", "0", "0"]))
    assert r["rows_both_judged"] == 2 and r["rows_unjudgeable"] == 1


def test_unknown_label_code_is_an_error():
    with pytest.raises(ValueError):
        lk.reliability(_sheet(["1", "maybe"], ["1", "0"]))


def test_agreed_labels_use_adjudication_for_disagreements():
    agreed = lk.agreed_labels(_sheet(["1", "1", "0"], ["1", "0", "0"], adjudicated=[None, "0", None]))
    assert list(agreed["label"]) == ["1", "0", "0"]


def test_gate_scored_against_agreed_labels():
    sheet = _sheet(["1", "1", "0", "0"], ["1", "1", "0", "0"])
    r = lk.score(sheet, _events(4))["gate_primary_PROCEED"]
    assert (r["precision"], r["recall"], r["f1"]) == (1.0, 1.0, 1.0)


def test_incomplete_labels_are_refused():
    sheet = _sheet(["1", None], ["1", "0"])
    with pytest.raises(lk.LabelsIncompleteError):
        lk.run(sheet, _events(2))


def test_real_label_sheet_is_still_empty_and_main_loads_no_held_out(monkeypatch):
    from experiments import common

    def forbidden(*a, **k):
        raise AssertionError("held-out data must not be loaded while labels are incomplete")
    monkeypatch.setattr(common, "load_held_out", forbidden)
    assert lk.main([]) is None


def test_every_published_value_has_a_page_and_a_table():
    values = pc.load_values()
    for s in values["systems"]:
        assert "TO FILL" not in s["citation"]
        for m in s["metrics"]:
            if m.get("not_in_paper"):
                assert m["value"] is None and m.get("note")         # empty, with the reason
            else:
                assert m["value"] is not None and m["page"] not in (None, "", "-")
                assert m.get("table_or_figure")
    assert pc.build(values)["status"] == "COMPLETE"


def test_not_in_paper_needs_a_reason():
    values = copy.deepcopy(pc.load_values())
    m = values["systems"][0]["metrics"][0]
    m.update(value=None, not_in_paper=True, note=None)
    assert pc.build(values)["status"] == "INCOMPLETE"


def test_published_comparison_complete_only_when_everything_filled():
    values = copy.deepcopy(pc.load_values())
    for s in values["systems"]:
        s["citation"] = "Author (2024), Journal"
        for m in s["metrics"]:
            m.update(name="metric", value=1.0, unit="u", page="p. 7")
    assert pc.build(values)["status"] == "COMPLETE"
