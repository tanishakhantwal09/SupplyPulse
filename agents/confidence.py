"""Gap 2: three-factor signal-confidence gate (replaces the old fixed 91/82/71%).

The gate scores how strong the NEWS SIGNAL behind an event is, before any
agent runs. It does not depend on the severity label.

Inspired by Angelopoulos and Bates (2023), "Conformal Prediction: A Gentle
Introduction". It is NOT a conformal method: there is no calibration set and
no coverage guarantee. The weights and thresholds are design choices.

Factors (each scaled to 0..1):
  mention volume  min(NumMentions / 50, 1)   GDELT NumMentions (mentions, not distinct sources)
  signal strength min(|Goldstein| / 10, 1)   Goldstein scale runs from -10 to +10 (Goldstein 1992)
  tone            min(|AvgTone| / 10, 1)
"""

WEIGHTS = {"mention_volume": 0.40, "signal_strength": 0.35, "tone": 0.25}  # ASSUMPTION: BUILD_PLAN section 2 design choice; not tuned.
MENTION_SATURATION = 50.0  # ASSUMPTION: 50 mentions counts as a fully reported event.
GOLDSTEIN_MAX = 10.0       # Goldstein, J.S. (1992), J. Conflict Resolution 36(2): scale is -10..+10.
TONE_SATURATION = 10.0     # ASSUMPTION: GDELT AvgTone is usually within -10..+10.
REJECT_BELOW = 0.35        # ASSUMPTION: BUILD_PLAN section 2 threshold; not tuned.
PROCEED_FROM = 0.60        # ASSUMPTION: BUILD_PLAN section 2 threshold; not tuned.

PROCEED = "PROCEED"
MONITOR = "MONITOR_AND_HOLD"
REJECT = "REJECTED"
NOT_APPLICABLE = "NOT_APPLICABLE"
USER_SIMULATION = "USER_SIMULATION"


def _num(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if v != v else v  # NaN -> None


def score_signal(num_mentions, goldstein, avg_tone):
    """Return the gate result for one event's news signal."""
    m, g, t = _num(num_mentions), _num(goldstein), _num(avg_tone)
    if m is None or g is None or t is None:
        return {"score": 0.0, "action": REJECT, "factors": None,
                "reason": "Missing news-signal values (mentions, Goldstein or tone)"}
    factors = {
        "mention_volume": min(max(m, 0) / MENTION_SATURATION, 1.0),
        "signal_strength": min(abs(g) / GOLDSTEIN_MAX, 1.0),
        "tone": min(abs(t) / TONE_SATURATION, 1.0),
    }
    score = round(sum(WEIGHTS[k] * v for k, v in factors.items()), 3)
    if score < REJECT_BELOW:
        action, reason = REJECT, f"Score {score} < {REJECT_BELOW}: weak signal, agents not activated"
    elif score < PROCEED_FROM:
        action, reason = MONITOR, f"Score {score} in [{REJECT_BELOW}, {PROCEED_FROM}): logged, agents not activated"
    else:
        action, reason = PROCEED, f"Score {score} >= {PROCEED_FROM}: agents activated"
    return {"score": score, "action": action, "reason": reason,
            "factors": {k: round(v, 3) for k, v in factors.items()},
            "weights": WEIGHTS, "thresholds": {"reject_below": REJECT_BELOW, "proceed_from": PROCEED_FROM}}


def gate_event(event):
    """Gate a pipeline event. User-simulated events have no news signal."""
    if str(event.get("data_source", "")).upper() == USER_SIMULATION:
        return {"score": None, "action": NOT_APPLICABLE, "factors": None,
                "reason": "User-simulated event: there is no news signal to gate"}
    return score_signal(event.get("num_mentions"), event.get("goldstein_scale"), event.get("avg_tone"))
