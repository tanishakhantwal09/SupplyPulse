"""Wardrop user equilibrium (UE) and system optimum (SO): agents/wardrop.py."""
import pytest

from agents import wardrop as w

TOL = 1e-6


def ports():
    # name, sailing s_i, free-flow p_i, capacity C_i, current load L_i (ships/day)
    return [w.Link("A", 1.1, 1.0, 57, 38.2), w.Link("B", 1.6, 1.0, 72, 51.1), w.Link("C", 5.1, 1.0, 94, 73.3)]


@pytest.mark.parametrize("demand", [5, 58.3, 150, 400])
def test_used_ports_share_one_time_and_unused_are_not_faster(demand):
    links = ports()
    r = w.solve(links, demand)
    assert r["converged"]
    times = [w.travel_time(l, x) for l, x in zip(links, r["flows"]) if x > 1e-12]
    assert max(times) - min(times) < TOL
    assert all(abs(t - r["level"]) < TOL for t in times)
    for l, x in zip(links, r["flows"]):
        if x <= 1e-12:
            assert w.travel_time(l, 0) >= r["level"] - TOL      # t_i(0) >= T
    assert w.is_equilibrium(links, r["flows"])


@pytest.mark.parametrize("method", [w.UE, w.SO])
@pytest.mark.parametrize("demand", [0.5, 58.3, 1000])
def test_every_ship_is_assigned(method, demand):
    r = w.solve(ports(), demand, method)
    assert sum(r["flows"]) == pytest.approx(demand, rel=1e-12)
    assert all(x >= 0 for x in r["flows"])


def test_one_usable_port_gets_everything():
    links = [w.Link("A", 1.0, 1.0, 50, 10), w.Link("dead", 0.5, 1.0, 0, 0), w.Link("none", 0.2, 1.0, 0, 0)]
    r = w.solve(links, 120)
    assert r["flows"] == pytest.approx([120, 0, 0])


def test_no_usable_port_is_an_error():
    with pytest.raises(ValueError):
        w.solve([w.Link("dead", 1.0, 1.0, 0, 0)], 10)


def test_zero_demand_gives_all_zeros():
    r = w.solve(ports(), 0)
    assert r["flows"] == [0, 0, 0] and r["level"] is None


def test_very_large_demand_still_converges():
    links = ports()
    r = w.solve(links, 1e7)                          # far above total capacity (223 ships/day)
    assert r["converged"] and sum(r["flows"]) == pytest.approx(1e7, rel=1e-9)
    assert w.is_equilibrium(links, r["flows"], tol=1e-9 * r["level"])
    assert r["iterations"] <= w.MAX_ITERATIONS


@pytest.mark.parametrize("demand", [5, 58.3, 150, 400])
def test_system_optimum_total_time_not_above_user_equilibrium(demand):
    links = ports()
    ue, so = w.solve(links, demand, w.UE), w.solve(links, demand, w.SO)
    assert w.system_total_time(links, so["flows"]) <= w.system_total_time(links, ue["flows"]) + 1e-9


def test_system_optimum_equalises_marginal_time():
    links = ports()
    so = w.solve(links, 150, w.SO)
    m = [w.marginal_time(l, x) for l, x in zip(links, so["flows"]) if x > 1e-12]
    assert max(m) - min(m) < TOL


def test_so_formula_factor_is_derived():
    assert w.SO_FACTOR == pytest.approx(0.75)


# ── Open-ocean bypass (uncongested, no capacity limit) ───────────────────────
def test_bypass_used_sets_time_to_its_sailing_time():
    links = [w.Link("canal port", 1.0, 1.0, 20, 15), w.Link("ocean bypass", 3.0, congested=False)]
    r = w.solve(links, 200)                          # far more than the port can take quickly
    assert r["level"] == 3.0
    assert r["flows"][1] > 0
    assert w.travel_time(links[0], r["flows"][0]) == pytest.approx(3.0)   # port filled up to T = s_bypass
    assert sum(r["flows"]) == pytest.approx(200)
    assert w.port_time(links[1], r["flows"][1]) == 0


def test_bypass_unused_when_ports_are_faster():
    links = [w.Link("port", 1.0, 1.0, 100, 10), w.Link("ocean bypass", 30.0, congested=False)]
    r = w.solve(links, 5)
    assert r["flows"][1] == 0 and r["level"] < 30.0
    assert w.is_equilibrium(links, r["flows"])


def test_only_bypass_routes():
    links = [w.Link("cape", 10.0, congested=False), w.Link("horn", 12.0, congested=False)]
    r = w.solve(links, 50)
    assert r["flows"] == [50, 0] and r["level"] == 10.0


def test_bypass_with_system_optimum():
    links = [w.Link("port", 1.0, 1.0, 20, 15), w.Link("ocean bypass", 3.0, congested=False)]
    so = w.solve(links, 200, w.SO)
    assert sum(so["flows"]) == pytest.approx(200) and so["level"] == 3.0


def test_shanghai_system_optimum_not_worse_than_all_to_busan():
    """Guaranteed by Wardrop's second principle (system total, incl. ships already at the ports)."""
    from agents import route_optimization_agent as ra
    alts = ra.get_alternate_ports("P001", "critical", 350, 144)
    links = [ra.to_link(a) for a in alts]
    per_day = ra.ships_per_day(350, 144)
    so = w.solve(links, per_day, w.SO)["flows"]
    ue = w.solve(links, per_day, w.UE)["flows"]
    busan = [per_day if a["name"] == "Port of Busan" else 0.0 for a in alts]
    assert w.system_total_time(links, so) <= w.system_total_time(links, busan)
    assert w.system_total_time(links, so) <= w.system_total_time(links, ue)
