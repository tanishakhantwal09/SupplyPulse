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


@pytest.mark.parametrize("source,enforced", [
    ("GDELT_LIVE_API", True),      # live feed: gate enforced
    ("USER_SIMULATION", False),    # dashboard / API simulation
    ("GDELT_real", False),         # dataset event run by a user
    ("TEST", False),
    (None, False),
])
def test_gate_enforced_for_live_events_only(source, enforced):
    g = confidence.gate_event({"data_source": source, "num_mentions": 3,
                               "goldstein_scale": -1.0, "avg_tone": -2.5})
    assert g["enforced"] is enforced
    assert g["score"] == pytest.approx(0.1215, abs=1e-3)        # score is always computed
    assert g["action"] == confidence.REJECT                    # and the signal verdict is still shown
    assert g["label"] == (confidence.LIVE_LABEL if enforced else confidence.MANUAL_LABEL)


def test_manual_label_text():
    assert confidence.MANUAL_LABEL == "manual scenario – user-confirmed disruption"


def test_thresholds_unchanged_by_policy():
    assert (confidence.REJECT_BELOW, confidence.PROCEED_FROM) == (0.35, 0.60)


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


@pytest.mark.parametrize("source,signal,expected", [
    ("USER_SIMULATION", (25, -5.0, -5.0), "Gate not enforced"),        # MONITOR signal, manual: agents ran
    ("GDELT_real", (3, -1.0, -2.5), "Gate not enforced"),               # REJECT signal, manual: agents ran
    ("GDELT_LIVE_API", (25, -5.0, -5.0), "logged for monitoring, agents not activated"),
    ("GDELT_LIVE_API", (3, -1.0, -2.5), "Gate enforced: agents not activated"),
    ("GDELT_LIVE_API", (60, -8.0, -9.0), "Gate enforced: agents activated"),
])
def test_reason_text_matches_what_happened(source, signal, expected):
    m, g, t = signal
    gate = confidence.gate_event({"data_source": source, "num_mentions": m, "goldstein_scale": g, "avg_tone": t})
    assert expected in gate["reason"]
    if not gate["enforced"]:
        assert "not activated" not in gate["reason"]


def test_threshold_uses_the_unrounded_score():
    # 0.40*(6/50) + 0.35*1.0 + 0.25*0.806 = 0.5995: displays as 0.6 but is below 0.60.
    g = confidence.score_signal(6, -10.0, -8.06)
    assert g["score_unrounded"] < 0.60 and g["score"] == 0.6
    assert g["action"] == confidence.MONITOR
    assert "uncertain signal" in g["reason"]


def test_exactly_at_threshold_proceeds():
    g = confidence.score_signal(50, -10.0, -4.0)        # 0.40 + 0.35 + 0.25*0.4 = 0.85
    assert g["action"] == confidence.PROCEED
    g = confidence.score_signal(0, -10.0, -10.0)        # 0.35 + 0.25 = 0.60 exactly (in floating point)
    assert (g["action"] == confidence.PROCEED) == (g["score_unrounded"] >= 0.60)
