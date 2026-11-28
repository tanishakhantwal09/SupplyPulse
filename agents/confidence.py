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
    # The signal verdict only; what happened to the agents is added by outcome_reason().
    if score < REJECT_BELOW:
        action, reason = REJECT, f"Score {score} < {REJECT_BELOW}: weak signal"
    elif score < PROCEED_FROM:
        action, reason = MONITOR, f"Score {score} in [{REJECT_BELOW}, {PROCEED_FROM}): uncertain signal"
    else:
        action, reason = PROCEED, f"Score {score} >= {PROCEED_FROM}: strong signal"
    return {"score": score, "action": action, "reason": reason,
            "factors": {k: round(v, 3) for k, v in factors.items()},
            "weights": WEIGHTS, "thresholds": {"reject_below": REJECT_BELOW, "proceed_from": PROCEED_FROM}}


# Gate policy (Tanisha, 26 Nov 2026): thresholds stay 0.35 / 0.60.
# The gate is ENFORCED only for live GDELT events. Every other run is a manual
# scenario that a user triggered (dashboard / API / script): the pipeline always
# runs, and the gate score is still computed and shown with MANUAL_LABEL.
LIVE_SOURCES = {"GDELT_LIVE_API"}
LIVE_LABEL = "live GDELT event – gated"
MANUAL_LABEL = "manual scenario – user-confirmed disruption"


def is_live(event):
    return str(event.get("data_source", "")).upper() in LIVE_SOURCES


def outcome_reason(gate):
    """Reason text that matches what actually happened (enforced gate vs manual scenario)."""
    verdict = gate.get("signal_reason") or gate["reason"]
    if not gate.get("enforced"):
        return f"{verdict}. Gate not enforced ({gate.get('label', MANUAL_LABEL)}): the agents ran anyway."
    if gate["action"] == PROCEED:
        return f"{verdict}. Gate enforced: agents activated."
    if gate["action"] == MONITOR:
        return f"{verdict}. Gate enforced: logged for monitoring, agents not activated."
    return f"{verdict}. Gate enforced: agents not activated."


def gate_event(event):
    """Score the event's news signal and say whether the gate is enforced for it."""
    result = score_signal(event.get("num_mentions"), event.get("goldstein_scale"), event.get("avg_tone"))
    live = is_live(event)
    result.update({
        "mode": "live" if live else "manual",
        "enforced": live,
        "label": LIVE_LABEL if live else MANUAL_LABEL,
        "signal_reason": result["reason"],
    })
    result["reason"] = outcome_reason(result)
    return result
