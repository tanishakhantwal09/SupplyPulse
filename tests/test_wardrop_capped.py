"""A2: capacity-constrained Wardrop equilibrium (utilisation ceiling rho_max)."""
import pytest

from agents import wardrop as w

RHO = 0.95
TOL = 1e-6


def ports(rho=RHO):
    # name, sailing s_i, free-flow p_i, capacity C_i, current load L_i (ships/day): the Shanghai alternates
    return [w.Link("Busan", 1.123, 1.0, 57, 38.19, rho_max=rho),
            w.Link("Shenzhen", 1.638, 1.0, 72, 51.12, rho_max=rho),
            w.Link("Singapore", 5.144, 1.0, 94, 73.32, rho_max=rho)]


def total_cap(links):
    return sum(l.cap_flow for l in links)


@pytest.mark.parametrize("method", [w.UE, w.SO])
@pytest.mark.parametrize("demand", [5, 20, 40, 49])
def test_flows_never_exceed_the_ceiling(method, demand):
    links = ports()
    r = w.solve(links, demand, method)
    for l, x in zip(links, r["flows"]):
        assert l.current_load + x <= RHO * l.capacity + 1e-9


@pytest.mark.parametrize("demand", [5, 20, 40, 49])
def test_capacity_constrained_equilibrium_conditions(demand):
    links = ports()
    r = w.solve(links, demand, w.UE)
    assert r["excess_demand"] == 0 and sum(r["flows"]) == pytest.approx(demand)
    T = r["level"]
    for l, x in zip(links, r["flows"]):
        t = w.travel_time(l, x)
        if x <= 1e-12:
            assert w.travel_time(l, 0) >= T - TOL          # unused: not faster than T
        elif x >= l.cap_flow - 1e-9:
            assert t <= T + TOL                            # at its cap: may be faster than T
        else:
            assert abs(t - T) < TOL                        # below cap: exactly T
    assert w.is_equilibrium(links, r["flows"])


def test_port_at_cap_can_be_faster_than_T():
    # A fast but small port fills up; the others then set a higher common time.
    links = [w.Link("small fast", 1.0, 1.0, 10, 5, rho_max=RHO), w.Link("big slow", 3.0, 1.0, 100, 10, rho_max=RHO)]
    r = w.solve(links, 20, w.UE)
    assert r["flows"][0] == pytest.approx(links[0].cap_flow)           # full: 4.5 ships/day
    assert w.travel_time(links[0], r["flows"][0]) < r["level"] - 1e-3
    assert w.is_equilibrium(links, r["flows"])


def test_excess_demand_is_reported_not_forced_in():
    # Replaces the Part A rule "every ship is assigned even above capacity".
    links = ports()
    cap = total_cap(links)                                             # about 49.2 ships/day
    r = w.solve(links, 1e7, w.UE)
    assert r["saturated"] and r["excess_demand"] == pytest.approx(1e7 - cap)
    assert r["flows"] == pytest.approx([l.cap_flow for l in links])
    assert sum(r["flows"]) + r["excess_demand"] == pytest.approx(1e7)


def test_shanghai_demand_exceeds_capped_capacity():
    links = ports()
    r = w.solve(links, 350 / 6, w.UE)                                  # 58.33 ships/day
    assert r["excess_demand"] == pytest.approx(350 / 6 - total_cap(links))
    assert r["excess_demand"] > 0


def test_port_already_above_ceiling_gets_nothing():
    links = [w.Link("full", 1.0, 1.0, 50, 49, rho_max=RHO), w.Link("ok", 2.0, 1.0, 50, 10, rho_max=RHO)]
    r = w.solve(links, 5, w.UE)
    assert r["flows"][0] == 0 and r["flows"][1] == pytest.approx(5)


def test_bypass_has_no_cap_and_takes_the_rest():
    links = [w.Link("port", 1.0, 1.0, 20, 15, rho_max=RHO), w.Link("ocean bypass", 3.0, congested=False)]
    r = w.solve(links, 200, w.UE)
    assert r["excess_demand"] == 0 and sum(r["flows"]) == pytest.approx(200)
    assert links[0].current_load + r["flows"][0] <= RHO * links[0].capacity + 1e-9
    assert r["level"] == 3.0


def test_zero_demand_capped():
    r = w.solve(ports(), 0, w.UE)
    assert r["flows"] == [0, 0, 0] and r["excess_demand"] == 0


@pytest.mark.parametrize("demand", [10, 30, 45])
def test_capped_system_optimum_not_above_capped_user_equilibrium(demand):
    links = ports()
    ue, so = w.solve(links, demand, w.UE), w.solve(links, demand, w.SO)
    assert ue["excess_demand"] == so["excess_demand"] == 0
    assert w.system_total_time(links, so["flows"]) <= w.system_total_time(links, ue["flows"]) + 1e-9


def test_uncapped_link_is_unchanged():
    assert w.Link("x", 1, 1, 10, 5).cap_flow == float("inf")
    assert w.Link("bypass", 1, congested=False, rho_max=RHO).cap_flow == float("inf")
