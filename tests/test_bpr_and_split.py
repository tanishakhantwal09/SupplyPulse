"""Gap 1: BPR congestion, ships per day and the capacity split."""
import math

import pytest

from agents import route_optimization_agent as ra


def test_bpr_constants_are_the_standard_values():
    # U.S. Bureau of Public Roads (1964), Traffic Assignment Manual.
    assert ra.BPR_ALPHA == 0.15
    assert ra.BPR_BETA == 4.0


def test_bpr_multiplier_known_values():
    assert ra.bpr_multiplier(0.0) == 1.0
    assert ra.bpr_multiplier(1.0) == pytest.approx(1.15)          # 1 + 0.15 * 1^4
    assert ra.bpr_multiplier(2.0) == pytest.approx(1 + 0.15 * 16)  # 3.4


def test_bpr_penalty_uses_daily_load_plus_arrivals():
    # capacity 100/day, 70% used, 20 extra ships/day -> V/C = 0.9
    delay, load, vc, mult = ra.bpr_congestion_penalty(2.0, 20, 100, 0.70)
    assert load == 70
    assert vc == pytest.approx(0.9)
    assert mult == pytest.approx(1 + 0.15 * 0.9 ** 4, abs=1e-3)
    assert delay == pytest.approx(2.0 * (1 + 0.15 * 0.9 ** 4), abs=0.01)


def test_zero_capacity_is_an_error_not_free_capacity():
    with pytest.raises(ValueError):
        ra.bpr_congestion_penalty(1.0, 5, 0, 0.5)


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


def test_shanghai_alternates_are_not_overloaded_after_spreading():
    alts = ra.get_alternate_ports("P001", "critical", 350, 144)
    assert sum(a["vessels_diverted_here"] for a in alts) == 350
    for a in alts:
        assert a["volume_ratio"] < 1.01           # was 2.0-2.6 before the fix
        assert a["bpr_adjusted_delay"] < 2 * a["estimated_delay_days"]
    assert alts[0]["name"] == "Port of Busan"


def test_full_port_receives_no_ships_and_ranks_last(monkeypatch):
    def util(name, static):
        return (1.2, "test") if name == "Port of Busan" else (static, "static")
    monkeypatch.setattr(ra, "get_port_utilization", util)
    alts = ra.get_alternate_ports("P001", "critical", 350, 144)
    busan = next(a for a in alts if a["name"] == "Port of Busan")
    assert busan["vessels_diverted_here"] == 0
    assert alts[-1]["name"] == "Port of Busan"
    assert alts[0]["receives_ships"]


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
