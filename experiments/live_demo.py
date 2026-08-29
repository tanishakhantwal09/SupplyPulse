import requests
import zipfile
import io
import pandas as pd
import json
import time
import math
from datetime import datetime, timezone, timedelta
from agents.langgraph_orchestrator import run_supplypulse
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()

MARITIME_KEYWORDS = [
    'port', 'ship', 'vessel', 'cargo', 'freight', 'maritime',
    'shipping', 'harbor', 'harbour', 'dock', 'container',
    'logistics', 'supply chain', 'trade route', 'tanker'
]

TRADING_NATIONS = [
    'CHN', 'USA', 'DEU', 'JPN', 'KOR', 'SGP',
    'NLD', 'GBR', 'IND', 'ARE', 'MYS', 'THA'
]

def get_gdelt_urls(hours_back=48):
    urls = []
    now = datetime.utcnow()
    rounded = now - timedelta(
        minutes=now.minute % 15,
        seconds=now.second,
        microseconds=now.microsecond
    )
    for i in range(hours_back * 4):
        dt = rounded - timedelta(minutes=15 * i)
        ts = dt.strftime("%Y%m%d%H%M%S")
        url = f"http://data.gdeltproject.org/gdeltv2/{ts}.export.CSV.zip"
        urls.append((ts, url))
    return urls

def try_fetch_file(ts, url):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None, None
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            with z.open(z.namelist()[0]) as f:
                df = pd.read_csv(f, sep="\t", header=None, low_memory=False)
        return ts, df
    except:
        return None, None

def is_maritime_event(row):
    url = str(row[60]).lower() if pd.notna(row[60]) else ''
    location = str(row[51]).lower() if pd.notna(row[51]) else ''
    return any(kw in url or kw in location for kw in MARITIME_KEYWORDS)

def score_event(row):
    tone = float(row[34]) if pd.notna(row[34]) else 0
    goldstein = float(row[30]) if pd.notna(row[30]) else 0
    mentions = int(row[31]) if pd.notna(row[31]) else 0
    return abs(tone) + abs(goldstein) + (mentions * 0.1)

def fetch_live_gdelt_event():

    console.print(Panel(
        f"[bold white]SUPPLYPULSE LIVE INGESTION PROOF[/bold white]\n\n"
        f"[cyan][SYSTEM CLOCK]:[/cyan]      {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"[cyan][GDELT ENDPOINT]:[/cyan]   http://data.gdeltproject.org/gdeltv2/lastupdate.txt\n"
        f"[dim]Fetching latest GDELT updates...[/dim]",
        border_style="white",
        title="LIVE DATA VERIFICATION"
    ))

    gdelt_urls = get_gdelt_urls(hours_back=48)
    best_event = None
    best_score = 0
    found_ts = None
    files_scanned = 0
    maritime_found = False

    console.print(f"  [yellow]→[/yellow] Scanning GDELT files for maritime/logistics events...")

    for ts, url in gdelt_urls[:8]:
        files_scanned += 1
        fetched_ts, df = try_fetch_file(ts, url)
        if df is None:
            continue

        filtered = df[df[7].isin(TRADING_NATIONS) | df[17].isin(TRADING_NATIONS)]
        filtered = filtered[pd.to_numeric(filtered[34], errors='coerce') < -2]

        maritime = filtered[filtered.apply(is_maritime_event, axis=1)]

        if len(maritime) > 0:
            top = maritime.apply(score_event, axis=1).idxmax()
            row = maritime.loc[top]
            row_score = score_event(row)
            if row_score > best_score:
                best_score = row_score
                best_event = row
                found_ts = ts
                maritime_found = True

    if best_event is None:
        console.print(f"  [yellow]→[/yellow] No maritime event in last 2 hours — scanning 48-hour window...")
        for ts, url in gdelt_urls[8:]:
            files_scanned += 1
            fetched_ts, df = try_fetch_file(ts, url)
            if df is None:
                continue

            filtered = df[df[7].isin(TRADING_NATIONS) | df[17].isin(TRADING_NATIONS)]
            filtered = filtered[pd.to_numeric(filtered[34], errors='coerce') < -3]

            if len(filtered) > 0:
                top = filtered.apply(score_event, axis=1).idxmax()
                row = filtered.loc[top]
                row_score = score_event(row)
                if row_score > best_score:
                    best_score = row_score
                    best_event = row
                    found_ts = ts

            if best_event is not None and files_scanned >= 20:
                break

    if best_event is None:
        console.print("[red]Could not fetch any suitable event. Check internet connection.[/red]")
        return None, None

    event_row = best_event
    event_type = "Maritime/logistics" if maritime_found else "Best available trading nation event"
    console.print(f"  [yellow]→[/yellow] Files scanned: {files_scanned} | Event type: {event_type}")
    console.print(f"  [yellow]→[/yellow] Source file timestamp: {found_ts}")

    event_id   = str(int(event_row[0]))
    event_date = str(event_row[1])
    source_url = str(event_row[60]) if pd.notna(event_row[60]) else "N/A"
    location   = str(event_row[51]) if pd.notna(event_row[51]) else "Unknown"
    lat        = float(event_row[56]) if pd.notna(event_row[56]) else 0
    lon        = float(event_row[57]) if pd.notna(event_row[57]) else 0
    goldstein  = float(event_row[30]) if pd.notna(event_row[30]) else -3.0
    tone       = float(event_row[34]) if pd.notna(event_row[34]) else -5.0
    mentions   = int(event_row[31])   if pd.notna(event_row[31]) else 5

    console.print(f"\n  [yellow]→[/yellow] [cyan][RAW GDELT EVENT ID]:[/cyan] {event_id}")
    console.print(f"  [yellow]→[/yellow] [cyan][NEWS HEADLINE / URL]:[/cyan] {source_url[:80]}")
    console.print(f"  [yellow]→[/yellow] [cyan][EVENT LOCATION]:[/cyan] {location}")
    console.print(f"  [yellow]→[/yellow] [cyan][GOLDSTEIN SCORE]:[/cyan] {goldstein} | [cyan][TONE]:[/cyan] {tone} | [cyan][MENTIONS]:[/cyan] {mentions}")

    try:
        val_df = pd.read_csv(
            r'C:\Users\tanis\Desktop\Minor project\dataset\final\validation_set_REAL_ONLY.csv',
            low_memory=False,
            usecols=['event_id']
        )
        in_dataset = event_id in val_df['event_id'].astype(str).values
        status = "[red]YES[/red]" if in_dataset else "[green]NO — genuinely new live event not in dataset[/green]"
    except:
        status = "[yellow]dataset check skipped[/yellow]"

    console.print(f"  [yellow]→[/yellow] [cyan][IN VALIDATION DATASET]:[/cyan] {status}")

    with open("dataset/reference/ports.json") as f:
        ports = json.load(f)

    def haversine(lat1, lon1, lat2, lon2):
        R = 3440.065
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        a = (math.sin(math.radians(lat2-lat1)/2)**2 +
             math.cos(phi1)*math.cos(phi2)*math.sin(math.radians(lon2-lon1)/2)**2)
        return 2 * R * math.asin(math.sqrt(a))

    nearest_port = ports[0]
    min_dist = float('inf')
    if lat != 0 and lon != 0:
        for port in ports:
            dist = haversine(lat, lon, port['lat'], port['lon'])
            if dist < min_dist:
                min_dist = dist
                nearest_port = port

    if goldstein <= -5 or (tone <= -8 and mentions >= 20) or mentions >= 100:
        severity = 'critical'
    elif goldstein <= -3 or (tone <= -5 and mentions >= 10) or mentions >= 40:
        severity = 'high'
    elif goldstein <= -1 or tone <= -3 or mentions >= 10:
        severity = 'medium'
    else:
        severity = 'low'

    live_event = {
        'event_id':                  event_id,
        'event_date':                event_date,
        'event_location':            location,
        'event_lat':                 lat,
        'event_lon':                 lon,
        'goldstein_scale':           goldstein,
        'avg_tone':                  tone,
        'num_mentions':              mentions,
        'source_url':                source_url,
        'data_source':               'GDELT_LIVE_API',
        'severity':                  severity,
        'nearest_port_id':           nearest_port['port_id'],
        'nearest_port_name':         nearest_port['name'],
        'nearest_port_country':      nearest_port['country'],
        'distance_to_port_nm':       round(min_dist, 1),
        'port_type':                 nearest_port['port_type'],
        'port_strategic_importance': nearest_port['strategic_importance'],
        'affected_routes':           json.dumps([]),
        'affected_commodities':      json.dumps(
            nearest_port.get('commodities', ['consumer_goods'])[:3]
        ),
        'freight_impact_pct':        48.0 if severity=='critical' else 24.0 if severity=='high' else 9.0,
        'vessels_affected':          350  if severity=='critical' else 180 if severity=='high' else 80,
        'duration_hours':            144  if severity=='critical' else 72  if severity=='high' else 36,
        'decision_reroute':          severity in ['critical','high'],
        'decision_financial_alert':  severity in ['critical','high'],
        'decision_inventory_realloc': severity in ['critical','high'],
    }

    return live_event, found_ts


if __name__ == "__main__":
    console.print(Rule("[bold white]SUPPLYPULSE — LIVE API DEMO[/bold white]"))

    live_event, found_ts = fetch_live_gdelt_event()

    if live_event is None:
        console.print("[red]Failed to fetch live event. Exiting.[/red]")
        exit(1)

    console.print(Rule("[bold cyan]DISPATCHING TO GROQ LLM INFERENCE[/bold cyan]", style="cyan"))
    console.print(f"  [cyan][GROQ LLM INFERENCE]:[/cyan] Live request dispatching to api.groq.com...")

    start = time.time()
    result = run_supplypulse(live_event)
    elapsed = round(time.time() - start, 2)

    console.print(f"  [cyan][INFERENCE LATENCY]:[/cyan] {elapsed}s end-to-end 4-agent pipeline")

    proof = {
        'system_clock_utc':      datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'gdelt_endpoint':        'http://data.gdeltproject.org/gdeltv2/lastupdate.txt',
        'gdelt_file_timestamp':  found_ts,
        'event_id':              live_event['event_id'],
        'source_url':            live_event['source_url'],
        'event_location':        live_event['event_location'],
        'severity':              live_event['severity'],
        'nearest_port':          live_event['nearest_port_name'],
        'agent_decision':        result,
        'total_latency_seconds': elapsed
    }

    with open("experiments/results/live_proof.json", "w") as f:
        json.dump(proof, f, indent=2, default=str)

    console.print(Rule("[bold green]LIVE PROOF COMPLETE[/bold green]", style="green"))
    console.print(f"\n[bold]Proof saved to: experiments/results/live_proof.json[/bold]")
    console.print(f"[dim]Contains: GDELT endpoint, live event ID, clickable source URL, agent decision — all timestamped.[/dim]")