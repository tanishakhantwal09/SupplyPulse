"""Gap 1: BPR port time, ships per day, Wardrop allocation in the route agent."""
import math

import pytest

from agents import route_optimization_agent as ra


def test_bpr_constants_are_the_standard_values():
    # U.S. Bureau of Public Roads (1964), Traffic Assignment Manual.
    assert ra.BPR_ALPHA == 0.15
    assert ra.BPR_BETA == 4.0


def test_port_time_uses_daily_load_plus_arrivals():
    # capacity 100/day, 70% used, 20 extra ships/day -> V/C = 0.9; p = 1 day; sailing 2 days
    alt = {"name": "X", "congested": True, "sailing_time_days": 2.0, "free_flow_days": 1.0,
           "port_capacity": 100, "port_utilization": 0.70}
    t = ra.link_times(alt, 20)
    assert t["volume_ratio"] == pytest.approx(0.9)
    assert t["port_time_days"] == pytest.approx(1 + 0.15 * 0.9 ** 4)
    assert t["travel_time_days"] == pytest.approx(2.0 + 1 + 0.15 * 0.9 ** 4)


def test_open_ocean_bypass_has_no_congestion():
    alt = {"name": "Cape", "congested": False, "sailing_time_days": 10.0, "free_flow_days": 0.0,
           "port_capacity": 300, "port_utilization": 0.15}
    t = ra.link_times(alt, 10_000)
    assert t["port_time_days"] == 0 and t["travel_time_days"] == 10.0 and t["volume_ratio"] is None


def test_link_types_follow_port_type():
    assert ra.link_type({"port_type": "alternate_route"}) == "open_ocean_bypass"
    assert ra.link_type({"port_type": "chokepoint"}) == "canal_or_strait"
    assert ra.link_type({"port_type": "mega_hub"}) == "port"


def test_free_flow_times_are_labelled_constants():
    assert ra.PORT_FREE_FLOW_DAYS == 1.0 and ra.CANAL_FREE_FLOW_DAYS == 1.0
    assert ra.MAIN_ALLOCATION == ra.USER_EQUILIBRIUM


@pytest.mark.parametrize("vessels,hours,expected", [
    (350, 144, 350 / 6),   # 6-day event
    (350, 24, 350),        # exactly one day
    (350, 12, 350),        # shorter than a day: max(duration_days, 1)
    (350, 0, 350),
    (0, 144, 0),
])
def test_ships_per_day(vessels, hours, expected):
    assert ra.ships_per_day(vessels, hours) == pytest.approx(expected)


def test_ships_per_day_never_exceeds_total():
    for hours in [0, 1, 6, 23.9, 24, 48]:
        assert ra.ships_per_day(100, hours) <= 100


def test_split_adds_up_exactly_and_follows_free_slots():
    shares = ra.split_vessels(350, [18.8, 20.9, 20.7])
    assert sum(shares) == 350
    assert shares[1] >= shares[2] >= shares[0]


def test_split_gives_nothing_to_full_ports():
    assert ra.split_vessels(10, [0, 5, 5]) == [0, 5, 5]
    assert ra.split_vessels(10, [0, 0, 0]) == [0, 0, 0]


def test_shanghai_user_equilibrium():
    plan = ra.plan_routes("P001", "critical", 350, 144)
    alts = plan["alternates"]
    assert plan["converged"] and sum(a["vessels_diverted_here"] for a in alts) == 350
    used = [a for a in alts if a["vessels_diverted_here"] > 0]
    assert max(a["travel_time_days"] for a in used) - min(a["travel_time_days"] for a in used) < 1e-3
    unused = [a for a in alts if a["vessels_diverted_here"] == 0]
    assert all(a["travel_time_days"] >= plan["level"] - 1e-3 for a in unused)
    assert alts[0]["name"] == "Port of Busan"                      # most ships
    assert next(a for a in alts if a["name"] == "Port of Singapore")["vessels_diverted_here"] == 0
    assert all(a["score_note"] == ra.SCORE_NOTE for a in alts)


def test_free_capacity_split_is_kept_as_ablation():
    alts = ra.get_alternate_ports("P001", "critical", 350, 144, method=ra.FREE_CAPACITY_SPLIT)
    ships = {a["name"]: a["vessels_diverted_here"] for a in alts}
    assert ships == {"Port of Busan": 109, "Port of Shenzhen": 121, "Port of Singapore": 120}


def test_suez_uses_the_uncongested_cape_route():
    plan = ra.plan_routes("P045", "critical", 500, 144)
    cape = next(a for a in plan["alternates"] if a["name"] == "Cape of Good Hope Route")
    assert cape["link_type"] == "open_ocean_bypass" and cape["port_time_days"] == 0
    if cape["vessels_diverted_here"] > 0:
        assert plan["level"] == pytest.approx(cape["sailing_time_days"], abs=1e-3)


def test_full_port_gets_fewer_ships(monkeypatch):
    def util(name, static):
        return (1.2, "test") if name == "Port of Busan" else (static, "static")
    monkeypatch.setattr(ra, "get_port_utilization", util)
    alts = ra.get_alternate_ports("P001", "critical", 350, 144)
    busan = next(a for a in alts if a["name"] == "Port of Busan")
    assert busan["vessels_diverted_here"] < 259                   # 259 with its normal load
    assert sum(a["vessels_diverted_here"] for a in alts) == 350


@pytest.mark.parametrize("method", ["user_equilibrium", "system_optimal", "free_capacity_split"])
def test_every_method_places_every_ship(method):
    alts = ra.get_alternate_ports("P021", "high", 90, 72, method=method)
    assert sum(a["vessels_diverted_here"] for a in alts) == 90


def test_unknown_method_is_an_error():
    with pytest.raises(ValueError):
        ra.get_alternate_ports("P001", "critical", 10, 24, method="whatever")


def test_unknown_port_raises():
    with pytest.raises(ra.UnknownPortError):
        ra.get_alternate_ports("P999", "critical", 10, 24)


def test_risk_term_is_normalised():
    assert set(ra.RISK_BY_IMPORTANCE.values()) | {ra.RISK_DEFAULT} == {0.0, 0.5, 1.0}


def test_haversine_known_distance():
    # Shanghai -> Busan, about 449 nm on the reference coordinates
    alts = ra.get_alternate_ports("P001", "critical", 0, 24)
    busan = next(a for a in alts if a["name"] == "Port of Busan")
    assert math.isclose(busan["distance_nm"], 449.3, abs_tol=0.5)
