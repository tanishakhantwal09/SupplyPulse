"""Gap 1: Wardrop (1952) user equilibrium and system optimum over the receiving ports.

Wardrop, J.G. (1952). Some theoretical aspects of road traffic research.
Proceedings of the Institution of Civil Engineers 1(3), 325-378.
  - First principle (user equilibrium, UE): every port that receives ships has the
    same travel time T, and no unused port could offer a time below T.
  - Second principle (system optimum, SO): total time of all ships is minimised,
    i.e. every used port has the same MARGINAL time.

Travel time of a diverted ship at link i, with x_i diverted ships per day:
    t_i(x_i) = s_i + p_i * (1 + alpha * ((L_i + x_i) / C_i) ** beta)
  s_i  sailing time from the disrupted port (fixed, not congested)
  p_i  free-flow time at the port / canal (congested by the BPR term)
  L_i  ships already using the port per day (current utilisation * capacity)
  C_i  full daily capacity (vessel_capacity in ports.json)
  BPR: U.S. Bureau of Public Roads (1964), Traffic Assignment Manual: alpha 0.15, beta 4.

Open-ocean bypass routes (port_type 'alternate_route') are uncongested: t_i = s_i,
with no capacity limit. If one is used, T = its s_i.

Capacity-constrained equilibrium (A2, 28 Nov 2026): with a utilisation ceiling
rho_max, a congested link takes at most L_i + x_i <= rho_max * C_i, so
    x_i(T) = min(uncapped x_i(T), rho_max * C_i - L_i)   (0 if already at/above the ceiling).
A link at its cap may have t_i < T; unused links still have t_i(0) >= T. If demand is
larger than the total capped capacity and there is no bypass route, the ships that fit
are assigned and the rest is returned as excess demand (ships per day waiting); they are
never forced over the cap.

System objective (all ships at each port, diverted + existing):
    Z = sum_i [ x_i * s_i + (L_i + x_i) * p_i * (1 + alpha * v_i ** beta) ],  v_i = (L_i + x_i) / C_i
    dZ/dx_i = s_i + p_i * (1 + alpha * (beta + 1) * v_i ** beta)     (alpha*(beta+1) = 0.75)
"""
from dataclasses import dataclass

BPR_ALPHA = 0.15  # U.S. Bureau of Public Roads (1964), Traffic Assignment Manual.
BPR_BETA = 4.0    # U.S. Bureau of Public Roads (1964), Traffic Assignment Manual.
SO_FACTOR = BPR_ALPHA * (BPR_BETA + 1)  # = 0.75, from the derivative above (not a separate constant)

# Numerical settings of the solver (not data values).
TIME_TOLERANCE_DAYS = 1e-9   # stop when the bracket on T is narrower than this (about 0.1 ms) ...
TIME_TOLERANCE_REL = 1e-12   # ... or than this fraction of T, whichever is larger (floating-point limit)
MAX_ITERATIONS = 200         # bisection steps; 200 halvings exceed double precision for any bracket
MAX_BRACKET_DOUBLINGS = 200  # to find an upper bound on T for very large demand

UE = "user_equilibrium"
SO = "system_optimal"


@dataclass
class Link:
    name: str
    sailing_days: float          # s_i
    free_flow_days: float = 0.0  # p_i (0 for an uncongested bypass)
    capacity: float = 0.0        # C_i, ships per day
    current_load: float = 0.0    # L_i, ships per day
    congested: bool = True
    rho_max: float = None        # utilisation ceiling; None = uncapped (classic Wardrop)

    @property
    def usable(self):
        return (not self.congested) or self.capacity > 0

    @property
    def cap_flow(self):
        """Most diverted ships per day this link can take (inf if uncapped or a bypass)."""
        if not self.congested or self.rho_max is None:
            return float("inf")
        return max(self.rho_max * self.capacity - self.current_load, 0.0)


def volume_ratio(link, x):
    return (link.current_load + x) / link.capacity if link.congested else None


def port_time(link, x):
    """BPR port time p_i * (1 + alpha * v^beta); 0 for an uncongested bypass."""
    if not link.congested:
        return 0.0
    return link.free_flow_days * (1 + BPR_ALPHA * volume_ratio(link, x) ** BPR_BETA)


def travel_time(link, x):
    return link.sailing_days + port_time(link, x)


def marginal_time(link, x):
    """dZ/dx_i (see module docstring)."""
    if not link.congested:
        return link.sailing_days
    return link.sailing_days + link.free_flow_days * (1 + SO_FACTOR * volume_ratio(link, x) ** BPR_BETA)


def system_total_time(links, flows):
    """Z: ship-days per day of all ships at the links (diverted + existing load)."""
    total = 0.0
    for link, x in zip(links, flows):
        total += x * link.sailing_days
        if link.congested:
            total += (link.current_load + x) * port_time(link, x)
    return total


def _cost_at_zero(link, k):
    if not link.congested:
        return link.sailing_days
    v0 = link.current_load / link.capacity
    return link.sailing_days + link.free_flow_days * (1 + k * v0 ** BPR_BETA)


def _flow_at(link, T, k):
    """Diverted ships per day at which link i's (marginal) time equals T. Congested links only."""
    if link.free_flow_days <= 0:
        raise ValueError(f"{link.name}: a congested link needs free_flow_days > 0")
    r = (T - link.sailing_days) / link.free_flow_days - 1
    if r <= 0:
        return 0.0
    return min(max(link.capacity * (r / k) ** (1 / BPR_BETA) - link.current_load, 0.0), link.cap_flow)


def solve(links, demand, method=UE):
    """Assign `demand` ships per day over `links` by Wardrop UE or SO.

    Returns dict: flows (ships/day, same order as links; 0 for unusable links),
    level (common time T for UE, common marginal time for SO), iterations, converged,
    excess_demand (ships/day that do not fit under the caps; 0 when uncapped or a
    bypass is available) and saturated (every capped link full).
    Uncapped links take every ship (BPR has no hard limit); capped links never exceed rho_max.
    """
    k = BPR_ALPHA if method == UE else SO_FACTOR if method == SO else None
    if k is None:
        raise ValueError(f"unknown method {method!r}")
    usable = [i for i, l in enumerate(links) if l.usable]
    if not usable:
        raise ValueError("no usable link (all have zero or no capacity)")
    flows = [0.0] * len(links)
    if demand <= 0:
        return {"flows": flows, "level": None, "iterations": 0, "converged": True, "method": method,
                "excess_demand": 0.0, "saturated": False}

    congested = [i for i in usable if links[i].congested]
    free = [i for i in usable if not links[i].congested]

    def assigned(T):
        return sum(_flow_at(links[i], T, k) for i in congested)

    # An uncongested bypass caps the common time at its sailing time.
    if free:
        best_free = min(free, key=lambda i: links[i].sailing_days)
        T_free = links[best_free].sailing_days
        if assigned(T_free) <= demand:
            for i in congested:
                flows[i] = _flow_at(links[i], T_free, k)
            flows[best_free] = demand - sum(flows)
            return {"flows": flows, "level": T_free, "iterations": 0, "converged": True, "method": method,
                    "excess_demand": 0.0, "saturated": False}
    else:
        # No bypass: if the capped links cannot take everything, fill them and report the rest.
        total_cap = sum(links[i].cap_flow for i in congested)
        if total_cap <= demand:
            for i in congested:
                flows[i] = links[i].cap_flow
            level = max((travel_time(links[i], flows[i]) for i in congested if flows[i] > 0), default=None)
            return {"flows": flows, "level": level, "iterations": 0, "converged": True, "method": method,
                    "excess_demand": demand - total_cap, "saturated": True}

    lo = min(_cost_at_zero(links[i], k) for i in congested)
    hi = lo + 1.0
    for _ in range(MAX_BRACKET_DOUBLINGS):
        if assigned(hi) >= demand:
            break
        hi = lo + 2 * (hi - lo)
    else:
        raise RuntimeError("could not bracket the equilibrium time")
    if free:
        hi = min(hi, T_free)

    def tol():
        return max(TIME_TOLERANCE_DAYS, TIME_TOLERANCE_REL * abs(hi))

    iterations = 0
    while hi - lo > tol() and iterations < MAX_ITERATIONS:
        mid = (lo + hi) / 2
        if assigned(mid) < demand:
            lo = mid
        else:
            hi = mid
        iterations += 1

    raw = [_flow_at(links[i], hi, k) for i in congested]
    # Remove the tiny overshoot of the bracket from the links BELOW their cap only;
    # links at their cap stay exactly at it.
    at_cap = [x >= links[i].cap_flow - 1e-12 for i, x in zip(congested, raw)]
    free_sum = sum(x for x, c in zip(raw, at_cap) if not c)
    fixed_sum = sum(x for x, c in zip(raw, at_cap) if c)
    scale = (demand - fixed_sum) / free_sum if free_sum > 0 else 0.0
    for i, x, c in zip(congested, raw, at_cap):
        flows[i] = x if c else x * scale
    return {"flows": flows, "level": hi, "iterations": iterations,
            "converged": hi - lo <= tol(), "method": method, "excess_demand": 0.0, "saturated": False}


def is_equilibrium(links, flows, tol=1e-6):
    """Check Wardrop's first principle, with capacity caps where the links have them.

    - used links below their cap share one time T;
    - links at their cap may be faster than T (t_i <= T), never slower;
    - unused links are not faster than T (t_i(0) >= T).
    """
    def at_cap(l, x):
        return x >= l.cap_flow - 1e-9

    free_times = [travel_time(l, x) for l, x in zip(links, flows) if l.usable and x > 1e-12 and not at_cap(l, x)]
    capped_times = [travel_time(l, x) for l, x in zip(links, flows) if l.usable and x > 1e-12 and at_cap(l, x)]
    if not free_times and not capped_times:
        return True
    if free_times:
        T = max(free_times)
        if min(free_times) < T - tol:
            return False
        if any(t > T + tol for t in capped_times):
            return False
    else:
        T = max(capped_times)  # every used link is full (saturated): no common time to compare
    return all(travel_time(l, 0) >= T - tol for l, x in zip(links, flows)
               if l.usable and x <= 1e-12 and l.cap_flow > 0)
