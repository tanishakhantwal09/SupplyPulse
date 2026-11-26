"""Number-and-wording check: a number must come from the code AND be described correctly."""
from experiments.llm_number_check import check_text

PROMPT = """Port disruption: Port of Shanghai (severity CRITICAL), 350 ships affected

SPLIT PLAN (this is the recommendation: ships are shared across several ports):
- Port of Busan: 109 ships, BPR delay 1.26 d, rerouting $3,966,837
- Ship-weighted BPR delay of the split plan: 3.03 days

SPLIT PLAN COST, six parts (USD):
- Rerouting: 30,385,340
- TOTAL: 9,117,711,732

SINGLE-PORT OPTIONS (what-if only, NOT the plan: ALL 350 ships sent to ONE port):
- Min Cost: Port of Busan, cost $12,737,550, delay 2.46 d, CO2 9,353 t
"""


def test_correct_text_passes():
    text = ("**COST ASSESSMENT**\nThe split plan totals $9,117,711,732, with rerouting about $30 million.\n"
            "**TRADE-OFF**\nAs a single-port option, sending all 350 ships to Busan costs $12,737,550 "
            "with a 2.46-day delay, versus 3.03 days for the split plan.")
    r = check_text(PROMPT, text)
    assert r["ok"], r
    assert r["numbers"] >= 6


def test_number_not_in_prompt_is_flagged():
    r = check_text(PROMPT, "The split plan saves $5,000,000.")
    assert [x["number"] for x in r["not_from_code"]] == ["$5,000,000"]
    assert not r["ok"]


def test_single_port_figure_described_as_the_plan_is_flagged():
    # This is what the 26 Nov 2026 Groq run did with Busan's 2.46 days.
    r = check_text(PROMPT, "Busan keeps the cost low at $12,737,550 and reduces the delay to 2.46 days.")
    assert {x["number"] for x in r["mislabelled"]} == {"$12,737,550", "2.46"}


def test_split_figure_described_as_single_port_is_flagged():
    r = check_text(PROMPT, "The single-port option has a delay of 1.26 days.")
    assert [x["number"] for x in r["mislabelled"]] == ["1.26"]


def test_list_markers_are_ignored():
    r = check_text(PROMPT, "1. The split plan total is $9,117,711,732.\n2. Done.")
    assert r["ok"] and r["numbers"] == 1
