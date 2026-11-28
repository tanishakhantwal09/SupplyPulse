"""Number-and-wording check for LLM explanations (Gap 3 faithfulness).

For every number in an agent's LLM text, two things must hold:
  1. SOURCE:  the number appears in the prompt the code gave that agent
              (within a small rounding tolerance, so "$30 million" matches 30,385,340).
  2. WORDING: the number is described as the right thing. The prompt is split into
              sections by its CAPITALISED headings. A number that only appears under
              a "SINGLE-PORT OPTIONS" heading must be called a single-port option
              (or "all ships to one port") in its sentence; a number that only appears
              under "SPLIT PLAN" must not be called a single-port option.

Usage:
    python3 -m experiments.llm_number_check path/to/run.json
where run.json holds {"prompts": {agent: text}, "texts": {agent: text}}.
"""
import json
import re
import sys

ROUNDING_TOLERANCE = 0.02  # ASSUMPTION: 2% covers rounding such as "$2.57 billion" or "about $30 million".

SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6,
         "b": 1e9, "bn": 1e9, "billion": 1e9}
NUM = re.compile(r"(?<![\w.])\$?(-?\d[\d,]*(?:\.\d+)?)\s*(%|k|thousand|mn|million|m|bn|billion|b)?(?![\w])",
                 re.IGNORECASE)
HEADING = re.compile(r"^\s*([A-Z][A-Z0-9\-]+(?: [A-Z0-9\-]+)*)\b")
SINGLE_WORDS = re.compile(r"single[\s\-]port|all \d[\d,]* ships|all ships|what[\s\-]if", re.IGNORECASE)
# LLMs often write Unicode hyphens and spaces ("single\u2011port", "90\u202f%"); normalise them first.
_UNICODE_HYPHENS = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")
_UNICODE_SPACES = dict.fromkeys(map(ord, "\u00a0\u2007\u202f\u2009"), " ")


def normalise(text):
    return str(text).translate(_UNICODE_HYPHENS).translate(_UNICODE_SPACES)
SPLIT_WORDS = re.compile(r"split|shared|\bplan\b", re.IGNORECASE)


def find_numbers(text):
    """[(shown, value, is_percent, position)] for every number in text."""
    out = []
    for m in NUM.finditer(text):
        unit = (m.group(2) or "").lower()
        try:
            value = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        out.append((m.group(0).strip(), value * SCALE.get(unit, 1), unit == "%", m.start()))
    return out


def section_kind(heading):
    h = (heading or "").upper()
    if "SINGLE-PORT" in h:
        return "single"
    if "SPLIT PLAN" in h:
        return "split"
    return "other"


def prompt_references(prompt):
    """[(value, kind)] for every number in the prompt, tagged by the section it sits in."""
    refs, kind = [], "other"
    for line in prompt.splitlines():
        m = HEADING.match(line)
        if m and len(m.group(1)) >= 4 and m.group(1).replace("-", "").replace(" ", "").isupper():
            kind = section_kind(line)
        refs += [(v, kind) for _, v, _, _ in find_numbers(line)]
    return refs


def _close(a, b):
    return a == b or (b != 0 and abs(a - b) / abs(b) <= ROUNDING_TOLERANCE)


def _sentence(text, pos):
    start = max(text.rfind(". ", 0, pos), text.rfind("\n", 0, pos)) + 1
    ends = [i for i in (text.find(". ", pos), text.find("\n", pos)) if i != -1]
    return text[start:min(ends) if ends else len(text)]


REFERS_BACK = re.compile(r"^\W*(?:(?:however|also|but|and|still|yet)\W+)?(it|this|that|these|those|its)\b",
                         re.IGNORECASE)


def _context(text, pos):
    """The sentence holding the number, plus the previous sentence when this one starts by
    referring back ("It also offers...", "This option exceeds..."), so the label carries over."""
    sentence = _sentence(text, pos).strip()
    current, cursor = sentence, pos
    for _ in range(3):                    # follow a chain of referring sentences, at most 3 back
        if not REFERS_BACK.match(current):
            break
        start = max(text.rfind(". ", 0, cursor), text.rfind("\n", 0, cursor))
        if start <= 0:
            break
        current = _sentence(text, start - 1).strip()
        sentence = current + ". " + sentence
        cursor = start - 1
    return sentence


def _is_list_marker(text, shown, pos):
    line_start = text.rfind("\n", 0, pos) + 1
    return text[line_start:pos].strip() in ("", "*", "-", "**") and re.fullmatch(r"\d\.?", shown) is not None


def check_text(prompt, text):
    prompt, text = normalise(prompt), normalise(text)
    refs = prompt_references(prompt)
    report = {"numbers": 0, "not_from_code": [], "mislabelled": []}
    for shown, value, is_pct, pos in find_numbers(text):
        if _is_list_marker(text, shown, pos):
            continue
        report["numbers"] += 1
        candidates = [value] + ([value / 100] if is_pct else [])
        kinds = {k for v, k in refs for c in candidates if _close(c, v)}
        sentence = _context(text, pos)
        if not kinds:
            report["not_from_code"].append({"number": shown, "sentence": sentence})
            continue
        says_single = bool(SINGLE_WORDS.search(sentence))
        says_split = bool(SPLIT_WORDS.search(sentence))
        if kinds == {"single"} and not says_single:
            report["mislabelled"].append({"number": shown, "is": "single-port option", "sentence": sentence})
        elif kinds == {"split"} and says_single and not says_split:
            report["mislabelled"].append({"number": shown, "is": "split plan", "sentence": sentence})
    report["ok"] = not report["not_from_code"] and not report["mislabelled"]
    return report


def check_run(prompts, texts):
    return {agent: check_text(prompts[agent], texts[agent]) for agent in texts if agent in prompts}


def main(path):
    data = json.load(open(path))
    results = check_run(data["prompts"], data["texts"])
    for agent, r in results.items():
        print(f"{agent:<20} numbers: {r['numbers']:>2}  not from code: {len(r['not_from_code'])}  "
              f"mislabelled: {len(r['mislabelled'])}  {'OK' if r['ok'] else 'PROBLEM'}")
        for item in r["not_from_code"] + r["mislabelled"]:
            print("    ", item)
    return all(r["ok"] for r in results.values())


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1]) else 1)
