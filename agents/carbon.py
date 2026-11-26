"""Gap 7: EU ETS carbon cost of a rerouting leg.

Legal basis: Directive 2003/87/EC as amended by Directive (EU) 2023/959
(maritime transport in the EU ETS).
  - Art. 3ga: 100% of emissions from voyages between two EU/EEA ports of call
    and from ships at berth in EU/EEA ports; 50% of emissions from voyages
    that depart from or arrive at an EU/EEA port from/to a non-EU port.
  - Art. 3gb: phase-in of the share of verified emissions to surrender:
    40% for 2024 emissions, 70% for 2025, 100% from 2026.
Method of combining fuel, CO2 factor and allowance price follows
Vaca-Cabrero et al. (2024) (BUILD_PLAN section 2, Gap 7).
"""

# ── Constants (replace the ASSUMPTION ones when a dated source is found) ─────
EUA_PRICE_EUR = 65.0  # ASSUMPTION: no dated EUA price source yet (BUILD_PLAN 5.2). Replace with a
                      # dated EU allowance settlement price and cite it here.
EUR_TO_USD = 1.08     # ASSUMPTION: no dated exchange-rate source yet.

FUEL_TONNE_PER_NM = 0.0191  # ASSUMPTION: one value for every ship size; no source yet.
CO2_PER_TONNE_FUEL = 3.114  # IMO Resolution MEPC.308(73) (2018), carbon factor Cf for heavy fuel oil.

# EU 27 member states + EEA (Norway, Iceland, Liechtenstein), ISO 3166-1 alpha-3.
# Directive (EU) 2023/959 applies the maritime ETS to EEA ports as well.
EU_EEA_COUNTRY_CODES = {
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC",
    "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK",
    "SVN", "ESP", "SWE", "NOR", "ISL", "LIE",
}

# Directive (EU) 2023/959, Art. 3ga.
COVERAGE_INTRA_EU = 1.0
COVERAGE_EXTRA_EU = 0.5
COVERAGE_NON_EU = 0.0

# Directive (EU) 2023/959, Art. 3gb (share of emissions for which allowances are surrendered).
PHASE_IN = {2024: 0.40, 2025: 0.70}
PHASE_IN_FULL_FROM = 2026

# ASSUMPTION: emissions AT BERTH in EU/EEA ports (100% covered by Art. 3ga) are NOT
# modelled, because SupplyPulse has no sourced fuel-use-at-berth figure or berth time.
# Only the sailing leg from the disrupted port to the alternate port is priced.
# ASSUMPTION: canals, straits and bypass routes (country code 'INT') are not ports of
# call, so a leg ending there counts as non-EU.
# ASSUMPTION: the UK ETS (GBR) is not modelled.


def is_eu_eea(country_code):
    return (country_code or "").upper() in EU_EEA_COUNTRY_CODES


def coverage_share(origin_country_code, destination_country_code):
    o, d = is_eu_eea(origin_country_code), is_eu_eea(destination_country_code)
    if o and d:
        return COVERAGE_INTRA_EU
    if o or d:
        return COVERAGE_EXTRA_EU
    return COVERAGE_NON_EU


def phase_in_share(year):
    year = int(year)
    if year >= PHASE_IN_FULL_FROM:
        return 1.0
    return PHASE_IN.get(year, 0.0)  # before 2024 shipping was not in the EU ETS


def eua_price_usd():
    return EUA_PRICE_EUR * EUR_TO_USD


def calculate_carbon(distance_nm, vessels, origin_country_code, destination_country_code, year):
    """CO2 and EU ETS cost for `vessels` ships sailing `distance_nm` each."""
    co2_per_vessel = distance_nm * FUEL_TONNE_PER_NM * CO2_PER_TONNE_FUEL
    total_co2 = co2_per_vessel * vessels
    coverage = coverage_share(origin_country_code, destination_country_code)
    phase = phase_in_share(year)
    covered_co2 = total_co2 * coverage * phase
    return {
        "distance_nm": distance_nm,
        "vessels": vessels,
        "co2_per_vessel_tonnes": round(co2_per_vessel, 2),
        "total_co2_tonnes": round(total_co2, 2),
        "ets_coverage_share": coverage,
        "ets_phase_in_share": phase,
        "ets_covered_co2_tonnes": round(covered_co2, 2),
        "eua_price_usd_per_tonne": round(eua_price_usd(), 2),
        "carbon_cost_usd": round(covered_co2 * eua_price_usd(), 2),
        "regulation": "EU ETS, Directive (EU) 2023/959 (Art. 3ga coverage, Art. 3gb phase-in)",
        "berth_emissions_modelled": False,
    }
