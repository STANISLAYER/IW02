#!/usr/bin/env python3
"""
currency_exchange_rate.py

CLI tool to query the provided PHP Currency Exchange service (running via Docker at http://localhost:8080),
save successful responses as JSON under ../data/, and log errors to ../error.log.

Service contract (from the bundle's README / code):
- Method: POST required with form field "key" (API key, must match server env API_KEY).
- Query params (GET): "from", "to", optional "date" (YYYY-MM-DD). If date absent, latest is used.
- URL: http://localhost:8080/?from=USD&to=EUR&date=2025-06-01
- Response JSON: {"error": "<empty on success or message>", "data": {"from": "...", "to": "...", "rate": <float>, "date": "YYYY-MM-DD"}}
- Valid dates: 2025-01-01 .. 2025-09-15 (based on provided data.json)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

import requests

# Project root is the parent of this script's directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ERROR_LOG = PROJECT_ROOT / "error.log"

# Logging: log to file + console
DATA_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ERROR_LOG, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query the bundled currency exchange PHP service and save JSON outputs.")
    p.add_argument("--from", dest="from_cur", help="Currency to convert FROM (e.g., USD, EUR, RON, RUS, UAH)", type=str)
    p.add_argument("--to", dest="to_cur", help="Currency to convert TO (e.g., USD, EUR, RON, RUS, UAH)", type=str)
    p.add_argument("--date", help="Date in YYYY-MM-DD", type=str)

    # Batch mode (equal intervals)
    p.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    p.add_argument("--num-dates", type=int, help="Number of evenly spaced dates (>=2)")

    # Service config
    p.add_argument("--base-url", default=os.environ.get("API_BASE_URL", "http://localhost:8080"),
                   help="Service base URL (default http://localhost:8080 or env API_BASE_URL)")
    p.add_argument("--api-key", default=os.environ.get("API_KEY", "EXAMPLE_API_KEY"),
                   help="API key sent as form field 'key' (default from env API_KEY or 'EXAMPLE_API_KEY')")

    p.add_argument("--warn-outside-range", action="store_true",
                   help="Warn when date is outside 2025-01-01..2025-09-15")
    return p.parse_args()


def validate_currency(code: str, field: str) -> str:
    if not code:
        raise SystemExit(f"{field} currency is required.")
    code = code.strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise SystemExit(f"{field} must be a 3-letter code (got '{code}').")
    return code


def parse_date(date_str: str, field: str = "date") -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        raise SystemExit(f"{field} must be in YYYY-MM-DD format (got '{date_str}').")


def evenly_spaced_dates(start: datetime, end: datetime, n: int) -> List[datetime]:
    if n < 2:
        raise SystemExit("num-dates must be >= 2")
    delta_days = (end - start).days
    if delta_days < 0:
        raise SystemExit("end-date must be on or after start-date")
    if n == 2:
        return [start, end]
    step = delta_days / (n - 1)
    ds = []
    for i in range(n):
        d = start + timedelta(days=round(i * step))
        ds.append(d)
    ds[0] = start
    ds[-1] = end
    # Deduplicate by date
    seen = set()
    out = []
    for d in ds:
        if d.date() not in seen:
            out.append(d)
            seen.add(d.date())
    return out


def warn_if_out_of_range(d: datetime, enabled: bool) -> None:
    if not enabled:
        return
    if not (datetime(2025,1,1) <= d <= datetime(2025,9,15)):
        print(f"⚠️  {d.date()} is outside the suggested test range 2025-01-01..2025-09-15")


def build_url(base_url: str, from_cur: str, to_cur: str, date_str: str | None) -> str:
    q = f"?from={from_cur}&to={to_cur}"
    if date_str:
        q += f"&date={date_str}"
    return base_url.rstrip("/") + "/" + q.lstrip("/")


def call_service(url: str, api_key: str) -> Dict[str, Any]:
    try:
        resp = requests.post(url, data={"key": api_key}, timeout=15)
    except requests.RequestException as e:
        logger.error("Network error for %s: %s", url, e)
        raise SystemExit(f"Network error: {e}")
    if not resp.ok:
        logger.error("HTTP error %s for %s: %s", resp.status_code, url, resp.text.strip())
        raise SystemExit(f"HTTP error {resp.status_code}. Details: {resp.text.strip() or 'No details.'}")
    try:
        payload = resp.json()
    except ValueError:
        logger.error("Invalid JSON from %s: %r", url, resp.text[:400])
        raise SystemExit("Invalid JSON response from service.")
    # The service wraps result as {"error":"", "data": {...}}
    if not isinstance(payload, dict):
        logger.error("Unexpected payload structure: %r", payload)
        raise SystemExit("Unexpected payload structure.")
    err = payload.get("error")
    if err:
        logger.error("Service error for %s: %s", url, err)
        raise SystemExit(f"Service error: {err}")
    return payload


def save_json(payload: Dict[str, Any], from_cur: str, to_cur: str, date_str: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    fname = f"{from_cur}_{to_cur}_{date_str}.json"
    path = DATA_DIR / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def run_one(from_cur: str, to_cur: str, date_str: str, base_url: str, api_key: str, warn_range: bool) -> None:
    f = validate_currency(from_cur, "From")
    t = validate_currency(to_cur, "To")
    d = parse_date(date_str)
    warn_if_out_of_range(d, warn_range)

    url = build_url(base_url, f, t, date_str)
    print(f"→ Requesting: {url}")
    payload = call_service(url, api_key)
    save_path = save_json(payload, f, t, date_str)
    print(f"✅ Saved to {save_path}")


def main() -> None:
    args = parse_args()
    # Batch vs single
    if args.start_date or args.end_date or args.num_dates:
        if not (args.from_cur and args.to_cur and args.start_date and args.end_date and args.num_dates):
            raise SystemExit("For batch mode provide --from, --to, --start-date, --end-date, --num-dates")
        s = parse_date(args.start_date, "start-date")
        e = parse_date(args.end_date, "end-date")
        dates = evenly_spaced_dates(s, e, args.num_dates)
        print(f"Batch: {args.from_cur}/{args.to_cur} {s.date()}..{e.date()} in {len(dates)} steps")
        for d in dates:
            try:
                run_one(args.from_cur, args.to_cur, d.strftime("%Y-%m-%d"), args.base_url, args.api_key, args.warn_outside_range)
            except SystemExit as ex:
                print(f"❌ {d.date()}: {ex}")
    else:
        if not (args.from_cur and args.to_cur and args.date):
            raise SystemExit("Provide --from, --to, and --date (YYYY-MM-DD)")
        run_one(args.from_cur, args.to_cur, args.date, args.base_url, args.api_key, args.warn_outside_range)


if __name__ == "__main__":
    main()
