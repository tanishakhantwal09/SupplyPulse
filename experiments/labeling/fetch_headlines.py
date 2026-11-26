import re
import time
import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def fetch_title(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code != 200:
            return "DEAD_LINK"
        match = TITLE_RE.search(resp.text)
        if not match:
            return "DEAD_LINK"
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        return title if title else "DEAD_LINK"
    except Exception:
        return "DEAD_LINK"


def main():
    df = pd.read_csv("experiments/labeling/labels_targeted.csv")
    headlines = []
    for i, url in enumerate(df["source_url"]):
        title = fetch_title(url)
        headlines.append(title)
        print(f"  [{i+1}/{len(df)}] {'DEAD_LINK' if title == 'DEAD_LINK' else 'OK'} — {url}")
        time.sleep(0.3)

    df["headline"] = headlines
    dead = sum(1 for h in headlines if h == "DEAD_LINK")
    ok = len(headlines) - dead
    print(f"\nFetched: {ok} successful, {dead} DEAD_LINK (of {len(headlines)})")

    df.to_csv("experiments/labeling/labels_targeted_with_headlines.csv", index=False)
    print("Saved experiments/labeling/labels_targeted_with_headlines.csv")


if __name__ == "__main__":
    main()
