"""Gap 1 ablation (no LLM, development set only).

Strategies compared for every event:
  A  nearest      : all ships to the nearest usable alternate port (Haversine distance)
  B  score_no_bpr : all ships to the best-scoring port, scored with RAW sailing delay (no congestion)
  C  supplypulse  : SupplyPulse: ships split by free capacity, BPR-adjusted delays (the real pipeline maths)
  D  bpr_no_split : extra ablation: all ships to the best-scoring port, scored with BPR delay
                    for all ships (shows what the split itself adds)

Judged by:
  - over-capacity share : share of ships sent to a port whose daily load exceeds its capacity (V/C > 1)
  - BPR delay           : ship-weighted BPR-adjusted sailing time (days)
  - M/G/1 waiting time  : Pollaczek-Khinchine mean wait in queue at the receiving port, per ship
                          (application to ports: Rauca et al. 2025, see BUILD_PLAN section 4a)
  - CO2 and EU ETS cost : agents/carbon.py
Plus the signal-gate outcome counts by severity.

The routing result depends only on (port, severity, vessels, duration, year) when utilisation
is static, so each distinct case is computed once and weighted by its number of events.

Run:  python3 -m experiments.gap_ablation --gate enforce|off [--sample N] [--out-dir DIR]
"""
import argparse
import math
import os

from agents import carbon, confidence
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
# ASSUMPTION: canals/straits/bypass routes (port_type chokepoint / alternate_route) are treated the same way.

COLUMNS = ["event_id", "event_date", "severity", "nearest_port_id", "vessels_affected", "duration_hours",
           "num_mentions", "goldstein_scale", "avg_tone"]
STRATEGIES = ["nearest", "score_no_bpr", "supplypulse", "bpr_no_split"]


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


def _single_port_allocation(alts, idx, vessels):
    return [vessels if i == idx else 0 for i in range(len(alts))]


def allocations(alts, vessels, duration_hours):
    """Ships per alternate (same order as alts) for each strategy."""
    per_day = route.ships_per_day(vessels, duration_hours)
    max_cost = max(a["estimated_cost_usd"] for a in alts) or 1

    def score(a, delay, max_delay):
        return (route.SCORE_WEIGHTS["risk"] * a["risk_score"]
                + route.SCORE_WEIGHTS["delay"] * delay / (max_delay or 1)
                + route.SCORE_WEIGHTS["cost"] * a["estimated_cost_usd"] / max_cost)

    raw = [a["estimated_delay_days"] for a in alts]
    bpr_all = [route.bpr_congestion_penalty(a["estimated_delay_days"], per_day, a["port_capacity"],
                                            a["port_utilization"])[0] for a in alts]
    nearest = min(range(len(alts)), key=lambda i: alts[i]["distance_nm"])
    best_raw = min(range(len(alts)), key=lambda i: score(alts[i], raw[i], max(raw)))
    best_bpr = min(range(len(alts)), key=lambda i: score(alts[i], bpr_all[i], max(bpr_all)))
    return {
        "nearest": _single_port_allocation(alts, nearest, vessels),
        "score_no_bpr": _single_port_allocation(alts, best_raw, vessels),
        "supplypulse": [a["vessels_diverted_here"] for a in alts],
        "bpr_no_split": _single_port_allocation(alts, best_bpr, vessels),
    }


def evaluate_allocation(alts, ships, vessels, duration_hours, origin_cc, year):
    """Metrics for one allocation of ships over the alternates."""
    days = max(float(duration_hours) / 24.0, route.MIN_EVENT_DAYS)
    total = sum(ships) or 1
    over, delay_w, wait_w, unstable, co2, ets = 0, 0.0, 0.0, 0, 0.0, 0.0
    finite_wait_ships = 0
    for a, n in zip(alts, ships):
        if n <= 0:
            continue
        per_day = n / days
        delay, load, vc, _ = route.bpr_congestion_penalty(a["estimated_delay_days"], per_day,
                                                          a["port_capacity"], a["port_utilization"])
        wq = mg1_wait_days(load + per_day, a["port_capacity"])
        over += n if vc > 1 else 0
        delay_w += delay * n
        if math.isinf(wq):
            unstable += n
        else:
            wait_w += wq * n
            finite_wait_ships += n
        c = carbon.calculate_carbon(a["distance_nm"], n, origin_cc, a.get("country_code"), year)
        co2 += c["total_co2_tonnes"]
        ets += c["carbon_cost_usd"]
    return {
        "over_capacity_share": over / total,
        "bpr_delay_days": delay_w / total,
        "unstable_queue_share": unstable / total,
        "mg1_wait_days_stable_ports": (wait_w / finite_wait_ships) if finite_wait_ships else None,
        "co2_tonnes": co2,
        "ets_cost_usd": ets,
        "ports_used": sum(1 for n in ships if n > 0),
    }


def evaluate_case(port_id, severity, vessels, duration_hours, year):
    alts = route.get_alternate_ports(port_id, severity, int(vessels), float(duration_hours))
    origin_cc = (port_by_id(port_id) or {}).get("country_code")
    out = {}
    for name, ships in allocations(alts, int(vessels), duration_hours).items():
        out[name] = evaluate_allocation(alts, ships, int(vessels), duration_hours, origin_cc, year)
        out[name]["ports"] = {a["name"]: n for a, n in zip(alts, ships) if n > 0}
    return out


def _weighted_mean(rows, strategy, key):
    pairs = [(r["events"], r[strategy][key]) for r in rows if r[strategy][key] is not None]
    total = sum(w for w, _ in pairs)
    return sum(w * v for w, v in pairs) / total if total else None


def summarise(rows):
    summary = {}
    for s in STRATEGIES:
        summary[s] = {k: _weighted_mean(rows, s, k) for k in
                      ["over_capacity_share", "bpr_delay_days", "unstable_queue_share",
                       "mg1_wait_days_stable_ports", "co2_tonnes", "ets_cost_usd", "ports_used"]}
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
        "strategies": STRATEGIES,
    }, out_dir=args.out_dir)
    print(f"events in {results['events_in']:,}, evaluated {results['events_evaluated']:,}, "
          f"skipped {results['events_skipped']:,}, distinct cases {results['distinct_cases']}")
    for s, m in results["summary_event_weighted"].items():
        wait = m["mg1_wait_days_stable_ports"]
        print(f"  {s:<13} over-capacity {m['over_capacity_share']:.3f}  BPR delay {m['bpr_delay_days']:.2f} d  "
              f"unstable {m['unstable_queue_share']:.3f}  M/G/1 wait {('%.3f d' % wait) if wait is not None else 'n/a'}  "
              f"CO2 {m['co2_tonnes']:,.0f} t  ETS ${m['ets_cost_usd']:,.0f}")
    print(f"written: {path}")
    return results


if __name__ == "__main__":
    main()
