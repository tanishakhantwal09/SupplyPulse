"""Inventory reallocation ports depend on where the disruption is (rule of 28 Nov 2026)."""
from agents.inventory_agent import port_handles, reallocation_ports
from agents.reference_data import commodities, port_by_id
from agents.route_optimization_agent import route_optimization_agent

MUNDRA = {"nearest_port_id": "P015", "nearest_port_name": "Port of Mundra", "severity": "critical",
          "vessels_affected": 180, "duration_hours": 144, "affected_routes": []}


def _commodity(name):
    return next(c for c in commodities() if c["name"] == name)


def _mundra_plan():
    return route_optimization_agent(MUNDRA)


def test_mundra_chemicals_stay_in_the_region():
    # Old static list sent Mundra chemicals to Los Angeles / New York-New Jersey.
    got = reallocation_ports(_commodity("Chemicals and Pharmaceuticals"), "P015", _mundra_plan())
    names = [g["port"] for g in got]
    assert names[0] == "Port of Mumbai (JNPT)"
    assert "Port of Los Angeles" not in names and "Port of New York-New Jersey" not in names


def test_mundra_raw_materials_no_longer_go_to_shanghai():
    names = [g["port"] for g in reallocation_ports(_commodity("Raw Materials and Minerals"), "P015", _mundra_plan())]
    assert "Port of Shanghai" not in names and "Port of Ningbo-Zhoushan" not in names


def test_route_plan_ports_come_first_then_nearest():
    plan = _mundra_plan()
    receiving = [a["name"] for a in plan["alternate_ports_analyzed"] if a["vessels_diverted_here"] > 0]
    for c in commodities():
        got = reallocation_ports(c, "P015", plan)
        bases = [g["basis"] for g in got]
        assert bases == sorted(bases, key=lambda b: b != "receives ships in the route plan")
        for g in got:
            if g["basis"] == "receives ships in the route plan":
                assert g["port"] in receiving
        nearest = [g["distance_nm"] for g in got if g["basis"] == "nearest port that handles it"]
        assert nearest == sorted(nearest)


def test_never_the_disrupted_port_or_a_canal_or_bypass():
    for c in commodities():
        for g in reallocation_ports(c, "P015", _mundra_plan()):
            p = next(p for p in [port_by_id(f"P{i:03d}") for i in range(1, 51)] if p and p["name"] == g["port"])
            assert p["port_id"] != "P015"
            assert p["port_type"] not in ("chokepoint", "alternate_route")
            assert port_handles(p, c)


def test_at_most_two_ports_and_no_duplicates():
    for c in commodities():
        names = [g["port"] for g in reallocation_ports(c, "P015", _mundra_plan())]
        assert len(names) <= 2 and len(names) == len(set(names))


def test_unknown_disrupted_port_gives_no_ports():
    assert reallocation_ports(_commodity("Chemicals and Pharmaceuticals"), "P999") == []
