"""Deterministic (fluid) queue for diverted ships that do not fit under the ceiling (A3).

Source: Newell, G.F. (1982). Applications of Queueing Theory, 2nd ed. Chapman & Hall:
deterministic queueing with cumulative arrival and departure curves.

During an event of D days, diverted ships arrive at a steady rate lambda (ships/day);
the receiving ports can take mu ships/day under the utilisation ceiling. If lambda > mu,
the anchorage queue grows at (lambda - mu) per day; after the event it is served at mu.

  E = (lambda - mu) * D             ships that cannot be placed immediately (wait at anchorage)
  W = lambda * D / (2 * mu)         average wait of a waiting ship (days)
  E * W = (lambda - mu) * lambda * D^2 / (2 * mu)
                                    total waiting in ship-days = the area between the cumulative
                                    arrival and departure curves
  E * W / (lambda * D) = (lambda - mu) * D / (2 * mu)
                                    average wait over ALL diverted ships

ASSUMPTIONS: arrivals are spread evenly over the event (as elsewhere in SupplyPulse); after
the event the ports keep the same room mu for the waiting ships (their own traffic unchanged);
waiting ships are served first-in first-out.
"""
import math


def fluid_queue(arrivals_per_day, service_per_day, days):
    """Waiting ships and waiting times of the deterministic queue (see module docstring)."""
    lam, mu, D = float(arrivals_per_day), float(service_per_day), float(days)
    if lam <= 0 or D <= 0 or lam <= mu:
        return {"waiting_ships": 0.0, "avg_wait_of_waiting_days": 0.0, "total_waiting_ship_days": 0.0,
                "avg_wait_all_ships_days": 0.0, "placeable": True}
    if mu <= 0:
        # No room at all under the ceiling: the waiting ships cannot be placed during or after the event.
        return {"waiting_ships": lam * D, "avg_wait_of_waiting_days": math.inf,
                "total_waiting_ship_days": math.inf, "avg_wait_all_ships_days": math.inf, "placeable": False}
    E = (lam - mu) * D
    W = lam * D / (2 * mu)
    return {"waiting_ships": E, "avg_wait_of_waiting_days": W, "total_waiting_ship_days": E * W,
            "avg_wait_all_ships_days": E * W / (lam * D), "placeable": True}
