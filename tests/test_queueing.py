"""Deterministic fluid queue for waiting ships (Newell 1982)."""
import math

import pytest

from agents.queueing import fluid_queue


def test_shanghai_old_candidates_example():
    # lambda = 350/6 = 58.33, mu = 49.22 (old 3 alternates at 95%), D = 6 days
    q = fluid_queue(350 / 6, 49.22, 6)
    assert q["waiting_ships"] == pytest.approx((350 / 6 - 49.22) * 6)          # 54.7 ships
    assert q["avg_wait_of_waiting_days"] == pytest.approx(350 / (2 * 49.22))   # 3.56 days
    assert q["total_waiting_ship_days"] == pytest.approx(q["waiting_ships"] * q["avg_wait_of_waiting_days"])
    assert q["avg_wait_all_ships_days"] == pytest.approx((350 / 6 - 49.22) * 6 / (2 * 49.22))


def test_total_waiting_equals_area_between_the_curves():
    lam, mu, D = 30.0, 20.0, 4.0
    q = fluid_queue(lam, mu, D)
    # numeric area between cumulative arrivals A(t) = lam*min(t, D) and departures S(t) = min(mu*t, A)
    dt, t, area = 1e-4, 0.0, 0.0
    while t < lam * D / mu:
        A = lam * min(t, D)
        area += (A - min(mu * t, A)) * dt
        t += dt
    assert q["total_waiting_ship_days"] == pytest.approx(area, rel=1e-3)


@pytest.mark.parametrize("lam,mu", [(10, 10), (10, 20), (0, 5)])
def test_no_queue_when_ships_fit(lam, mu):
    q = fluid_queue(lam, mu, 6)
    assert q["waiting_ships"] == 0 and q["avg_wait_of_waiting_days"] == 0 and q["placeable"]


def test_no_room_at_all_is_flagged_not_hidden():
    q = fluid_queue(10, 0, 6)
    assert q["waiting_ships"] == 60 and math.isinf(q["avg_wait_of_waiting_days"]) and not q["placeable"]
