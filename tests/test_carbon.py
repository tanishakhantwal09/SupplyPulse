"""Gap 7: EU ETS coverage and phase-in (Directive (EU) 2023/959)."""
import pytest

from agents import carbon


def test_eua_price_is_one_named_constant():
    assert carbon.EUA_PRICE_EUR == 65.0


@pytest.mark.parametrize("origin,dest,share", [
    ("NLD", "DEU", 1.0),   # intra-EU
    ("NOR", "NLD", 1.0),   # EEA counts as EU for the maritime ETS
    ("NLD", "GBR", 0.5),   # leaves the EU
    ("CHN", "NLD", 0.5),   # enters the EU
    ("CHN", "KOR", 0.0),   # no EU port
    ("INT", "ESP", 0.5),   # canal/strait is not an EU port of call
    (None, None, 0.0),
])
def test_coverage(origin, dest, share):
    assert carbon.coverage_share(origin, dest) == share


@pytest.mark.parametrize("year,share", [(2023, 0.0), (2024, 0.4), (2025, 0.7), (2026, 1.0), (2030, 1.0)])
def test_phase_in(year, share):
    assert carbon.phase_in_share(year) == share


def test_non_eu_voyage_costs_nothing_but_still_emits():
    c = carbon.calculate_carbon(449.3, 100, "CHN", "KOR", 2026)
    assert c["carbon_cost_usd"] == 0
    assert c["total_co2_tonnes"] > 0


def test_carbon_cost_formula():
    c = carbon.calculate_carbon(300, 10, "NLD", "DEU", 2025)
    co2 = 300 * carbon.FUEL_TONNE_PER_NM * carbon.CO2_PER_TONNE_FUEL * 10
    assert c["total_co2_tonnes"] == pytest.approx(co2, abs=0.01)
    assert c["carbon_cost_usd"] == pytest.approx(co2 * 1.0 * 0.7 * 65.0 * 1.08, abs=0.05)


def test_berth_emissions_flagged_as_not_modelled():
    assert carbon.calculate_carbon(1, 1, "NLD", "DEU", 2026)["berth_emissions_modelled"] is False
