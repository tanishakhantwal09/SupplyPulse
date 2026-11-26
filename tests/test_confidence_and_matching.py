"""Gap 2 signal gate and whole-word commodity matching."""
import pytest

from agents import confidence
from agents.inventory_agent import match_commodities


def test_weights_sum_to_one_and_thresholds():
    assert sum(confidence.WEIGHTS.values()) == pytest.approx(1.0)
    assert (confidence.REJECT_BELOW, confidence.PROCEED_FROM) == (0.35, 0.60)


def test_known_score():
    g = confidence.score_signal(60, -8.0, -9.0)
    assert g["score"] == pytest.approx(0.40 * 1.0 + 0.35 * 0.8 + 0.25 * 0.9, abs=1e-3)
    assert g["action"] == confidence.PROCEED


@pytest.mark.parametrize("m,g,t,action", [
    (3, -1.0, -2.5, confidence.REJECT),
    (25, -5.0, -5.0, confidence.MONITOR),   # 0.2 + 0.175 + 0.125 = 0.5
    (50, -10.0, -10.0, confidence.PROCEED),
])
def test_actions(m, g, t, action):
    assert confidence.score_signal(m, g, t)["action"] == action


def test_missing_values_are_rejected_not_filled_in():
    assert confidence.score_signal(None, -5, -5)["action"] == confidence.REJECT
    assert confidence.score_signal(float("nan"), -5, -5)["action"] == confidence.REJECT


def test_gate_does_not_depend_on_severity():
    base = {"num_mentions": 25, "goldstein_scale": -5.0, "avg_tone": -5.0}
    scores = {confidence.gate_event({**base, "severity": s})["score"] for s in ["critical", "high", "medium", "low"]}
    assert len(scores) == 1


def test_user_simulation_is_not_applicable():
    g = confidence.gate_event({"data_source": "USER_SIMULATION", "num_mentions": 0})
    assert g["action"] == confidence.NOT_APPLICABLE


def _names(terms):
    matched, unmatched = match_commodities(terms)
    return [c["name"] for c in matched], unmatched


def test_chemicals_does_not_match_petrochemicals():
    names, _ = _names(["chemicals"])
    assert names == ["Chemicals and Pharmaceuticals"]


def test_petrochemicals_and_oil_match_oil():
    assert _names(["petrochemicals"])[0] == ["Oil and Petrochemicals"]
    assert _names(["oil"])[0] == ["Oil and Petrochemicals"]


def test_palm_oil_is_not_crude_oil():
    names, unmatched = _names(["palm_oil"])
    assert names == [] and unmatched == ["palm_oil"]


def test_name_match_beats_subcategory_match():
    # 'agricultural' is in the Agricultural name and in Machinery's 'agricultural_machinery'
    assert _names(["agricultural"])[0] == ["Agricultural Products and Food"]


def test_unmatched_terms_are_reported():
    _, unmatched = _names(["electronics", "furniture", "all"])
    assert unmatched == ["furniture", "all"]
