"""Gap 1 ablation (no LLM, development set only).

Strategies compared for every event (ships per day = vessels / max(duration_days, 1)):
  nearest             : all ships to the nearest usable alternate (Haversine distance)
  score_no_bpr        : all ships to the best port by the 0.40/0.35/0.25 score, using sailing time only
  free_capacity_split : the old split, in proportion to free daily capacity (ignores distance)
  user_equilibrium    : SupplyPulse: Wardrop (1952) user equilibrium (agents/wardrop.py)
  system_optimal      : Wardrop system optimum (minimum total time of all ships at the ports)
  bpr_no_split        : all ships to the best port by the score, using travel time with all ships there

Same metric definitions for every strategy, weighted by diverted ships:
  - over-capacity share : share of ships sent to a congested link with V/C > 1
  - travel time         : sailing time + BPR port time (days)
  - port time           : BPR port time p_i * (1 + 0.15 * (V/C)^4) (days); 0 on open-ocean bypasses
  - system total time   : ship-days per day of ALL ships at the receiving links (diverted + existing)
  - M/G/1 waiting time  : Pollaczek-Khinchine mean wait at congested links (application to ports:
                          Rauca et al. 2025); unstable-queue share; open-ocean bypasses have no queue
  - CO2 and EU ETS cost : agents/carbon.py
Plus the signal-gate outcome counts by severity.

The routing result depends only on (port, severity, vessels, duration, year) when utilisation
is static, so each distinct case is computed once and weighted by its number of events.

Run:  python3 -m experiments.gap_ablation --gate enforce|off [--sample N] [--out-dir DIR]
"""
import argparse
import math
import os

from agents import carbon, confidence, wardrop
from agents import route_optimization_agent as route
from agents.reference_data import port_by_id
from experiments import common

# ── M/G/1 (Pollaczek-Khinchine) ──────────────────────────────────────────────
# Wq = lambda * E[S^2] / (2 * (1 - rho)),  E[S^2] = (1 + cs^2) * E[S]^2,  rho = lambda * E[S].
# Pollaczek (1930), Khinchine (1932); textbook form: Kleinrock (1975), Queueing Systems Vol. 1.
SERVICE_TIME_SCV = 1.0  # ASSUMPTION: squared coefficient of variation of service time (1.0 = exponential,
                        # i.e. the M/M/1 special case). To be replaced from Rauca et al. (2025) once the PDF is in.
# ASSUMPTION: each receiving port is modelled as ONE server whose service rate equals its daily
# vessel_capacity from ports.json; arrivals = current daily load + diverted ships per day.
# ASSUMPTION: canals and straits (port_type chokepoint) are treated the same way; open-ocean
# bypass routes (port_type alternate_route) are uncongested and have no queue.

COLUMNS = ["event_id", "event_date", "severity", "nearest_port_id", "vessels_affected", "duration_hours",
           "num_mentions", "goldstein_scale", "avg_tone"]
STRATEGIES = ["nearest", "score_no_bpr", "free_capacity_split", "user_equilibrium", "system_optimal",
              "bpr_no_split"]
METRICS = ["over_capacity_share", "travel_time_days", "port_time_days", "system_total_time",
           "unstable_queue_share", "mg1_wait_days_stable_ports", "co2_tonnes", "ets_cost_usd", "ports_used"]


def mg1_wait_days(arrivals_per_day, capacity_per_day, scv=SERVICE_TIME_SCV):
    """Mean waiting time in queue (days). Infinite when the queue is unstable (rho >= 1)."""
    if capacity_per_day <= 0:
        return math.inf
    es = 1.0 / capacity_per_day
    rho = arrivals_per_day * es
    if rho >= 1:
        return math.inf
    es2 = (1 + scv) * es ** 2
    return arrivals_per_day * es2 / (2 * (1 - rho))


def _single(alts, idx, per_day):
    return [per_day if i == idx else 0.0 for i in range(len(alts))]


def allocations(alts, vessels, duration_hours):
    """Ships PER DAY per alternate (same order as alts) for each strategy."""
    per_day = route.ships_per_day(vessels, duration_hours)
    max_cost = max(a["estimated_cost_usd"] for a in alts) or 1

    def score(a, t, max_t):
        return (route.SCORE_WEIGHTS["risk"] * a["risk_score"]
                + route.SCORE_WEIGHTS["delay"] * t / (max_t or 1)
                + route.SCORE_WEIGHTS["cost"] * a["estimated_cost_usd"] / max_cost)

    sail = [a["sailing_time_days"] for a in alts]
    t_all = [route.link_times(a, per_day)["travel_time_days"] for a in alts]
    links = [route.to_link(a) for a in alts]
    return {
        "nearest": _single(alts, min(range(len(alts)), key=lambda i: alts[i]["distance_nm"]), per_day),
        "score_no_bpr": _single(alts, min(range(len(alts)), key=lambda i: score(alts[i], sail[i], max(sail))), per_day),
        "free_capacity_split": route.free_capacity_flows(alts, per_day),
        "user_equilibrium": wardrop.solve(links, per_day, wardrop.UE)["flows"],
        "system_optimal": wardrop.solve(links, per_day, wardrop.SO)["flows"],
        "bpr_no_split": _single(alts, min(range(len(alts)), key=lambda i: score(alts[i], t_all[i], max(t_all))), per_day),
    }


def evaluate_allocation(alts, flows, vessels, origin_cc, year):
    """Metrics for one allocation (flows = diverted ships per day per alternate)."""
    total = sum(flows) or 1.0
    ships = route.split_vessels(vessels, flows)
    over = travel = port = wait_w = unstable = finite = 0.0
    co2 = ets = 0.0
    for a, x, n in zip(alts, flows, ships):
        if x <= 0:
            continue
        t = route.link_times(a, x)
        travel += t["travel_time_days"] * x
        port += t["port_time_days"] * x
        if a["congested"]:
            over += x if t["volume_ratio"] > 1 else 0
            load = a["port_capacity"] * a["port_utilization"]
            wq = mg1_wait_days(load + x, a["port_capacity"])
        else:
            wq = 0.0  # open-ocean bypass: no queue
        if math.isinf(wq):
            unstable += x
        else:
            wait_w += wq * x
            finite += x
        c = carbon.calculate_carbon(a["distance_nm"], n, origin_cc, a.get("country_code"), year)
        co2 += c["total_co2_tonnes"]
        ets += c["carbon_cost_usd"]
    return {
        "over_capacity_share": over / total,
        "travel_time_days": travel / total,
        "port_time_days": port / total,
        "system_total_time": wardrop.system_total_time([route.to_link(a) for a in alts], flows),
        "unstable_queue_share": unstable / total,
        "mg1_wait_days_stable_ports": (wait_w / finite) if finite else None,
        "co2_tonnes": co2,
        "ets_cost_usd": ets,
        "ports_used": sum(1 for n in ships if n > 0),
        "ports": {a["name"]: n for a, n in zip(alts, ships) if n > 0},
    }


def evaluate_case(port_id, severity, vessels, duration_hours, year):
    alts = route.get_alternate_ports(port_id, severity, int(vessels), float(duration_hours))
    origin_cc = (port_by_id(port_id) or {}).get("country_code")
    out = {}
    for name, flows in allocations(alts, int(vessels), duration_hours).items():
        out[name] = evaluate_allocation(alts, flows, int(vessels), origin_cc, year)
    return out


def _weighted_mean(rows, strategy, key):
    pairs = [(r["events"], r[strategy][key]) for r in rows if r[strategy][key] is not None]
    total = sum(w for w, _ in pairs)
    return sum(w * v for w, v in pairs) / total if total else None


def summarise(rows):
    summary = {}
    for s in STRATEGIES:
        summary[s] = {k: _weighted_mean(rows, s, k) for k in METRICS}
    return summary


def run(df, enforce_gate):
    """Run the ablation on a dataframe of development events."""
    common.require_gate_setting(enforce_gate)
    gated = common.apply_gate(df, enforce_gate=False)  # scores for every event (for the gate split)
    gate_split = (gated.groupby(["severity", "gate_action"]).size().unstack(fill_value=0)
                  .to_dict(orient="index"))
    used = gated[gated["gate_action"] == confidence.PROCEED] if enforce_gate else gated
    used = used.assign(year=used["event_date"].astype(str).str[:4].astype(int))

    keys = ["nearest_port_id", "severity", "vessels_affected", "duration_hours", "year"]
    rows, skipped = [], []
    for case, count in used.groupby(keys).size().items():
        port_id, severity, vessels, duration, year = case
        try:
            metrics = evaluate_case(port_id, severity, vessels, duration, int(year))
        except (route.UnknownPortError, route.NoAlternatesError) as e:
            skipped.append({"case": dict(zip(keys, map(str, case))), "events": int(count), "reason": str(e)})
            continue
        rows.append({"port_id": port_id, "port": (port_by_id(port_id) or {}).get("name"),
                     "severity": severity, "vessels": int(vessels), "duration_hours": float(duration),
                     "year": int(year), "events": int(count), **metrics})
    return {
        "events_in": int(len(df)),
        "events_evaluated": int(sum(r["events"] for r in rows)),
        "events_skipped": int(sum(s["events"] for s in skipped)),
        "distinct_cases": len(rows),
        "summary_event_weighted": summarise(rows),
        "gate_split_by_severity": gate_split,
        "skipped": skipped,
        "cases": rows,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gate", choices=["enforce", "off"], required=True,
                   help="enforce: only events the gate says PROCEED to; off: all events")
    p.add_argument("--sample", type=int, default=None, help="seeded sample size (default: whole development set)")
    p.add_argument("--seed", type=int, default=common.SEED)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--name", default="gap_ablation")
    args = p.parse_args(argv)

    os.environ["SUPPLYPULSE_STATIC_UTIL"] = "1"  # reproducible: no live PortWatch values
    os.environ["SUPPLYPULSE_QUIET"] = "1"
    df = common.sample(common.load_dev(COLUMNS), args.sample, args.seed)
    enforce = args.gate == "enforce"
    results = run(df, enforce_gate=enforce)
    path = common.write_result(args.name, results, {
        "enforce_gate": enforce, "dataset_split": "development", "seed": args.seed,
        "sample_size": args.sample, "utilisation": "static (ports.json)",
        "mg1_service_time_scv": SERVICE_TIME_SCV, "mg1_scv_status": "ASSUMPTION until Rauca et al. (2025) PDF",
        "strategies": STRATEGIES, "supplypulse_strategy": "user_equilibrium",
        "port_free_flow_days": route.PORT_FREE_FLOW_DAYS, "canal_free_flow_days": route.CANAL_FREE_FLOW_DAYS,
        "free_flow_status": "ASSUMPTION (no source yet)",
        "capacities_status": "ASSUMPTION: vessel_capacity, current_utilization and chokepoint values in "
                             "ports.json are not yet calibrated (build_reference_databases.py, BUILD_PLAN 5)",
    }, out_dir=args.out_dir)
    print(f"events in {results['events_in']:,}, evaluated {results['events_evaluated']:,}, "
          f"skipped {results['events_skipped']:,}, distinct cases {results['distinct_cases']}")
    for s, m in results["summary_event_weighted"].items():
        wait = m["mg1_wait_days_stable_ports"]
        print(f"  {s:<20} over-capacity {m['over_capacity_share']:.3f}  travel {m['travel_time_days']:.2f} d  "
              f"port {m['port_time_days']:.2f} d  unstable {m['unstable_queue_share']:.3f}  "
              f"M/G/1 wait {('%.3f d' % wait) if wait is not None else 'n/a'}  CO2 {m['co2_tonnes']:,.0f} t")
    print(f"written: {path}")
    return results


if __name__ == "__main__":
    main()
