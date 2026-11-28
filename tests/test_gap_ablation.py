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
    assert set(out) == set(ga.STRATEGIES)
    assert out["nearest"]["ports"] == {"Port of Ningbo-Zhoushan": 350}   # nearest by distance (82 nm)
    assert out["nearest"]["over_capacity_share"] == 1.0
    for s in ga.STRATEGIES:
        assert sum(out[s]["ports_all_ships"].values()) == 350               # every ship placed or waiting
        assert out[s]["ets_cost_usd"] == 0                                   # no EU port involved
    for s in ("capped_user_equilibrium", "capped_system_optimal"):
        assert out[s]["max_utilisation"] <= 0.95 + 1e-6
        assert out[s]["unstable_queue_share"] == 0                           # M/G/1 stays stable
    so = out["system_optimal"]["system_total_time"]
    full = [s for s in ga.STRATEGIES if out[s]["waiting_ships"] == 0]
    assert all(so <= out[s]["system_total_time"] + 1e-9 for s in full)


def test_waiting_ships_are_included_in_every_average():
    out = ga.evaluate_case("P001", "critical", 350, 144, 2026, radius_nm=500)
    m = out["capped_user_equilibrium"]
    assert m["waiting_ships"] > 0 and m["avg_wait_of_waiting_days"] > 0
    assert m["travel_time_days"] > m["travel_time_placed_days"]             # waiting raises the all-ship mean
    assert m["total_waiting_ship_days"] == pytest.approx(m["waiting_ships"] * m["avg_wait_of_waiting_days"])
    for s in ("nearest", "user_equilibrium", "system_optimal", "free_capacity_split"):
        assert out[s]["waiting_ships"] == 0                                  # uncapped: nobody waits


def test_service_time_spread_changes_only_queue_waits():
    a = ga.evaluate_case("P001", "critical", 350, 144, 2026, scv=1.0)
    b = ga.evaluate_case("P001", "critical", 350, 144, 2026, scv=0.04)     # Rauca et al. Cs = 0.2
    for s in ga.STRATEGIES:
        for k in ("over_capacity_share", "unstable_queue_share", "travel_time_days", "waiting_ships", "co2_tonnes"):
            assert a[s][k] == b[s][k]
        if a[s]["mg1_wait_days_stable_ports"]:
            assert b[s]["mg1_wait_days_stable_ports"] < a[s]["mg1_wait_days_stable_ports"]


def test_allocations_always_place_every_ship():
    alts = route.get_alternate_ports("P021", "high", 90, 72)
    per_day = route.ships_per_day(90, 72)
    for name, flows in ga.allocations(alts, 90, 72).items():
        if name.startswith("capped_"):
            assert sum(flows) <= per_day + 1e-9          # the rest is excess demand (Rotterdam: 7 ships wait)
        else:
            assert sum(flows) == pytest.approx(per_day)


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


def test_floating_point_noise_is_not_counted_as_waiting():
    out = ga.evaluate_case("P021", "high", 90, 72, 2025)
    for s in ("free_capacity_split", "user_equilibrium", "system_optimal", "nearest"):
        assert out[s]["waiting_ships"] == 0 and out[s]["avg_wait_of_waiting_days"] == 0
