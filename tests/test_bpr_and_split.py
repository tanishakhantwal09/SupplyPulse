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
    assert ra.MAIN_ALLOCATION == ra.CAPPED_USER_EQUILIBRIUM and ra.RHO_MAX == 0.95


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


def test_shanghai_capped_user_equilibrium_is_the_main_plan():
    plan = ra.plan_routes("P001", "critical", 350, 144)
    alts = plan["alternates"]
    assert plan["method"] == ra.CAPPED_USER_EQUILIBRIUM and plan["rho_max"] == 0.95
    assert all(a["utilisation"] <= 0.95 + 1e-3 for a in alts)                # never above the ceiling
    assert plan["excess_ships"] == 0                                         # 1,500 nm candidates: room 101/day
    assert sum(a["vessels_diverted_here"] for a in alts) == 350
    assert alts[0]["name"] == "Port of Ningbo-Zhoushan"                      # 82 nm, the most ships


def test_shanghai_candidates_within_1500_nm():
    names = [a["name"] for a in ra.plan_routes("P001", "critical", 350, 144)["alternates"]]
    assert set(names) == {"Port of Ningbo-Zhoushan", "Port of Busan", "Port of Guangzhou", "Port of Shenzhen",
                          "Port of Osaka-Kobe", "Port of Tokyo-Yokohama", "Port of Ho Chi Minh"}
    assert "Port of Singapore" not in names and "Port of Shanghai" not in names    # 2,057 nm; disrupted port


def test_fallback_gives_at_least_three_candidates():
    for pid in ("P036", "P041"):                  # Santos, Lagos: no cargo port within 1,500 nm
        alts = ra.plan_routes(pid, "critical", 50, 144)["alternates"]
        assert len(alts) == ra.MIN_CANDIDATES
        assert all("nearest cargo port" in a["candidate_basis"] for a in alts)


def test_canal_keeps_its_listed_alternatives():
    alts = ra.plan_routes("P045", "critical", 500, 144)["alternates"]
    assert {a["name"] for a in alts} == {"Cape of Good Hope Route", "Port of Durban", "Port of Cape Town"}


def test_waiting_ships_get_a_newell_waiting_time():
    # 500 nm radius -> Ningbo, Busan + fallback Guangzhou: 49.5 ships/day of room for 58.33/day
    plan = ra.plan_routes("P001", "critical", 350, 144, radius_nm=500)
    lam, mu, D = 350 / 6, sum(a["vessels_per_day_here"] for a in plan["alternates"]), 6
    assert plan["excess_ships"] > 0
    assert plan["waiting_ships_exact"] == pytest.approx((lam - mu) * D, abs=0.1)
    assert plan["avg_wait_of_waiting_days"] == pytest.approx(lam * D / (2 * mu), rel=1e-3)
    assert plan["total_waiting_ship_days"] == pytest.approx(plan["waiting_ships_exact"] * plan["avg_wait_of_waiting_days"])
    assert plan["all_ships_avg_travel_time_days"] > plan["placed_avg_travel_time_days"]
    alts = plan["alternates"]
    assert sum(a["vessels_diverted_here"] + a["vessels_waiting_for_here"] for a in alts) == 350


def test_shanghai_uncapped_user_equilibrium_ablation():
    plan = ra.plan_routes("P001", "critical", 350, 144, method=ra.USER_EQUILIBRIUM)
    alts = plan["alternates"]
    assert plan["converged"] and sum(a["vessels_diverted_here"] for a in alts) == 350
    used = [a for a in alts if a["vessels_diverted_here"] > 0]
    assert max(a["travel_time_days"] for a in used) - min(a["travel_time_days"] for a in used) < 1e-3
    unused = [a for a in alts if a["vessels_diverted_here"] == 0]
    assert all(a["travel_time_days"] >= plan["level"] - 1e-3 for a in unused)
    assert alts[0]["name"] == "Port of Ningbo-Zhoushan"            # most ships
    assert all(a["score_note"] == ra.SCORE_NOTE for a in alts)


def test_free_capacity_split_is_kept_as_ablation():
    alts = ra.get_alternate_ports("P001", "critical", 350, 144, method=ra.FREE_CAPACITY_SPLIT)
    assert sum(a["vessels_diverted_here"] for a in alts) == 350
    assert all(a["vessels_diverted_here"] > 0 for a in alts)       # every candidate gets a share of free room


def test_suez_uses_the_uncongested_cape_route():
    plan = ra.plan_routes("P045", "critical", 500, 144)
    cape = next(a for a in plan["alternates"] if a["name"] == "Cape of Good Hope Route")
    assert cape["link_type"] == "open_ocean_bypass" and cape["port_time_days"] == 0
    if cape["vessels_diverted_here"] > 0:
        assert plan["level"] == pytest.approx(cape["sailing_time_days"], abs=1e-3)


def test_port_above_the_ceiling_gets_no_ships(monkeypatch):
    def util(name, static):
        return (1.2, "test") if name == "Port of Busan" else (static, "static")
    monkeypatch.setattr(ra, "get_port_utilization", util)
    plan = ra.plan_routes("P001", "critical", 350, 144)
    busan = next(a for a in plan["alternates"] if a["name"] == "Port of Busan")
    assert busan["vessels_diverted_here"] == 0                    # already at 120% > 95% ceiling
    assert sum(a["vessels_diverted_here"] for a in plan["alternates"]) + plan["excess_ships"] == 350
    uncapped = ra.get_alternate_ports("P001", "critical", 350, 144, method=ra.USER_EQUILIBRIUM)
    assert next(a for a in uncapped if a["name"] == "Port of Busan")["vessels_diverted_here"] < 259


@pytest.mark.parametrize("method", ["capped_user_equilibrium", "capped_system_optimal", "user_equilibrium",
                                    "system_optimal", "free_capacity_split"])
def test_every_ship_is_assigned_or_reported_waiting(method):
    plan = ra.plan_routes("P021", "high", 90, 72, method=method)
    assert sum(a["vessels_diverted_here"] for a in plan["alternates"]) + plan["excess_ships"] == 90
    if method in ("user_equilibrium", "system_optimal", "free_capacity_split"):
        assert plan["excess_ships"] == 0                          # uncapped strategies force every ship in


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
