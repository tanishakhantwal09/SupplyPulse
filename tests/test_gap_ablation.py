"""Gap ablation maths and strategies (no dataset needed)."""
import math

import pandas as pd
import pytest

from agents import route_optimization_agent as route
from experiments import gap_ablation as ga


def test_mg1_equals_mm1_when_scv_is_one():
    # M/M/1: Wq = rho / (mu - lambda). lambda = 0.5/day, mu = 1/day -> 1.0 day.
    assert ga.mg1_wait_days(0.5, 1.0, scv=1.0) == pytest.approx(1.0)


def test_mg1_deterministic_service_halves_the_wait():
    # M/D/1 (scv = 0) waits half as long as M/M/1.
    assert ga.mg1_wait_days(0.5, 1.0, scv=0.0) == pytest.approx(0.5)


def test_mg1_unstable_queue_is_infinite():
    assert math.isinf(ga.mg1_wait_days(1.0, 1.0))
    assert math.isinf(ga.mg1_wait_days(2.0, 1.0))
    assert math.isinf(ga.mg1_wait_days(1.0, 0))


def test_mg1_scv_is_labelled_assumption():
    assert ga.SERVICE_TIME_SCV == 1.0


def test_shanghai_case_strategies():
    out = ga.evaluate_case("P001", "critical", 350, 144, 2026)
    assert out["nearest"]["ports"] == {"Port of Busan": 350}         # nearest by distance
    assert out["nearest"]["over_capacity_share"] == 1.0              # all 350 into Busan: V/C 1.69
    assert out["supplypulse"]["over_capacity_share"] == 0.0          # split: every port at V/C ~0.99
    assert out["supplypulse"]["ports_used"] == 3
    assert sum(out["supplypulse"]["ports"].values()) == 350
    for s in ga.STRATEGIES:
        assert out[s]["ets_cost_usd"] == 0                           # no EU port involved


def test_allocations_always_place_every_ship():
    alts = route.get_alternate_ports("P021", "high", 90, 72)
    for ships in ga.allocations(alts, 90, 72).values():
        assert sum(ships) == 90


def _events():
    return pd.DataFrame({
        "event_id": [1, 2, 3],
        "event_date": ["2026-03-01", "2026-03-02", "2025-01-01"],
        "severity": ["critical", "critical", "high"],
        "nearest_port_id": ["P001", "P001", "P021"],
        "vessels_affected": [350, 350, 90],
        "duration_hours": [144, 144, 72],
        "num_mentions": [60, 60, 3],
        "goldstein_scale": [-8.0, -8.0, -1.0],
        "avg_tone": [-9.0, -9.0, -2.5],
    })


def test_run_groups_identical_cases_and_weights_them():
    r = ga.run(_events(), enforce_gate=False)
    assert r["events_in"] == 3 and r["events_evaluated"] == 3 and r["distinct_cases"] == 2
    shanghai = next(c for c in r["cases"] if c["port_id"] == "P001")
    assert shanghai["events"] == 2


def test_run_with_gate_enforced_drops_weak_signals():
    r = ga.run(_events(), enforce_gate=True)
    assert r["events_evaluated"] == 2                                # the weak Rotterdam event is dropped
    assert r["gate_split_by_severity"]["high"]["REJECTED"] == 1


def test_run_requires_explicit_gate_setting():
    from experiments.common import GateSettingError
    with pytest.raises(GateSettingError):
        ga.run(_events(), enforce_gate=None)


def test_cli_requires_gate_flag():
    with pytest.raises(SystemExit):
        ga.main([])
