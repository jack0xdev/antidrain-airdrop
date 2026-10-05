#!/usr/bin/env python3
"""Check which listed addresses are still sending (last outgoing tx per chain).

Uses the Etherscan V2 multichain API (one key, `chainid` parameter).
Get a free key at https://etherscan.io/myapikey. Some chains may need a paid plan;
those rows get the API error message instead of a date.

Usage:
    ETHERSCAN_API_KEY=... python3 research/check_last_activity.py \
        --chains 1,56,8453,42161 --days 30 [--platform Binance]

Writes research/last-activity.csv.
"""
import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.etherscan.io/v2/api"
HERE = Path(__file__).parent


def fetch(params):
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def last_outgoing(address, chainid, apikey, get=fetch):
    """Newest timestamp of a normal or ERC-20 tx sent *from* address, or (None, error)."""
    newest = None
    for action in ("txlist", "tokentx"):
        data = get({"chainid": chainid, "module": "account", "action": action,
                    "address": address, "page": 1, "offset": 50, "sort": "desc",
                    "apikey": apikey})
        result = data.get("result")
        if data.get("status") != "1":
            if isinstance(result, list) or "No transactions found" in str(data.get("message")):
                continue
            return None, str(result or data.get("message"))
        for tx in result:
            if tx.get("from", "").lower() == address.lower():
                ts = int(tx["timeStamp"])
                newest = ts if newest is None else max(newest, ts)
                break
        time.sleep(0.35)  # stay under the free-tier rate limit
    return newest, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", default="1", help="comma-separated chain ids, e.g. 1,56,8453")
    ap.add_argument("--days", type=int, default=30, help="active = sent within this many days")
    ap.add_argument("--platform", help="only check this platform")
    ap.add_argument("--input", default="platform-withdrawal-addresses.csv",
                    help="address list in research/ to check")
    args = ap.parse_args()

    apikey = os.environ.get("ETHERSCAN_API_KEY")
    if not apikey:
        raise SystemExit("Set ETHERSCAN_API_KEY")

    rows = list(csv.DictReader(open(HERE / args.input, newline="")))
    if args.platform:
        rows = [r for r in rows if r["platform"].lower() == args.platform.lower()]

    now = time.time()
    out_path = HERE / "last-activity.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["platform", "address", "name_tag", "chain_id", "last_outgoing_utc", "active", "error"])
        for r in rows:
            for chainid in args.chains.split(","):
                ts, err = last_outgoing(r["address"], chainid.strip(), apikey)
                when = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else ""
                active = "yes" if ts and now - ts < args.days * 86400 else "no"
                w.writerow([r["platform"], r["address"], r["name_tag"], chainid, when, active, err])
                f.flush()
                print(f"{r['platform']:<11} {r['name_tag']:<28} chain {chainid:<6} {when or err or '-'}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
