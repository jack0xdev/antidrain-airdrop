#!/usr/bin/env python3
"""Build the platform withdrawal-address list from the public eth-labels dataset.

Usage:
    git clone --depth 1 https://github.com/dawsbot/eth-labels /tmp/eth-labels
    python3 research/build_withdrawal_list.py /tmp/eth-labels/data/csv/accounts.csv

Keeps only exchange-owned name tags ("<Name> 14", "<Name>: Hot Wallet 2") and drops
cold wallets, deposit funders, deposit addresses, deployers, exploiters and tokens.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

CHAINS = {
    "1": "Ethereum", "56": "BSC", "8453": "Base", "42161": "Arbitrum", "10": "Optimism",
    "43114": "Avalanche", "480": "World Chain", "42220": "Celo", "100": "Gnosis",
}

# platform -> (name-tag regex, directory entries it covers)
PLATFORMS = {
    "Binance":    (r"Binance",      "Binance P2P"),
    "OKX":        (r"OKX|OKEx",     "OKX P2P"),
    "Bybit":      (r"Bybit|ByBit",  "Bybit P2P, Bybit Card"),
    "KuCoin":     (r"KuCoin",       "KuCoin P2P"),
    "Bitget":     (r"Bitget",       "Bitget exchange (Bitget Wallet Card: unconfirmed)"),
    "Crypto.com": (r"Crypto\.com",  "Crypto.com Card"),
    "Nexo":       (r"Nexo",         "Nexo Card"),
    "ChangeNOW":  (r"ChangeNOW",    "ChangeNOW"),
    "SimpleSwap": (r"SimpleSwap",   "SimpleSwap"),
    "Remitano":   (r"Remitano",     "Remitano"),
    "Wirex":      (r"Wirex",        "Wirex"),
    "Paxful":     (r"Paxful",       "Paxful"),
    "BitPay":     (r"BitPay",       "BitPay"),
}

NOT_FOUND = [
    "ChangeHero", "StealthEX", "Exolix", "Godex", "Trocuro", "SWFT",
    "RedotPay", "CWallet", "SwapSpace (aggregator, routes to partners)",
]

SOURCE = "https://github.com/dawsbot/eth-labels"


def collect(accounts_csv):
    rows = list(csv.DictReader(open(accounts_csv, newline="")))
    out = {}
    for name, (pattern, _) in PLATFORMS.items():
        rx = re.compile(rf"^(?:{pattern})(?: \d+|: Hot Wallet(?: \d+)?)$", re.I)
        by_addr = defaultdict(lambda: {"tags": set(), "chains": set()})
        for r in rows:
            tag = r["nameTag"].strip()
            if rx.match(tag):
                a = by_addr[r["address"].lower()]
                a["tags"].add(tag)
                a["chains"].add(CHAINS.get(r["chainId"], r["chainId"]))
        out[name] = by_addr
    return out


def tag_sort_key(item):
    tag = sorted(item[1]["tags"])[0]
    hot = 0 if "hot wallet" in tag.lower() else 1
    num = re.search(r"(\d+)$", tag)
    return (hot, int(num.group(1)) if num else 0, tag)


def write_csv(data, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["platform", "covers", "address", "name_tag", "chains_tagged", "source"])
        for name, by_addr in data.items():
            for addr, info in sorted(by_addr.items(), key=tag_sort_key):
                w.writerow([name, PLATFORMS[name][1], addr, " / ".join(sorted(info["tags"])),
                            ";".join(sorted(info["chains"])), SOURCE])


def write_md(data, path, dataset_commit):
    total = sum(len(v) for v in data.values())
    lines = [
        "# Platform withdrawal (hot wallet) addresses — EVM",
        "",
        f"Source: [{SOURCE}]({SOURCE}) (Etherscan-family name tags), dataset commit `{dataset_commit}`.",
        f"{total} unique addresses across {len(data)} platforms. Full list: `platform-withdrawal-addresses.csv`.",
        "",
        "**Not verified as currently active.** Run `check_last_activity.py` with an Etherscan API key",
        "to get each address's last outgoing transaction date before relying on it.",
        "Numbered tags (e.g. `Binance 14`) mean exchange-owned; some are cold/treasury wallets, not withdrawal senders.",
        "\"Chains tagged\" = explorers where the dataset carries the tag. Etherscan-family explorers share labels,",
        "so a chain listed there does not prove the address sends on that chain — check with `--chains`.",
        "",
        "## Summary",
        "",
        "| Platform | Covers directory entries | Addresses | Explicit `Hot Wallet` tags |",
        "|---|---|---|---|",
    ]
    for name, by_addr in data.items():
        hot = sum(1 for i in by_addr.values() if any("hot wallet" in t.lower() for t in i["tags"]))
        lines.append(f"| {name} | {PLATFORMS[name][1]} | {len(by_addr)} | {hot} |")
    lines += [
        "",
        "## No labeled withdrawal wallet found",
        "",
        "Not in the dataset (no public label): " + ", ".join(NOT_FOUND) + ".",
        "",
        "## No withdrawal address exists",
        "",
        "DEX, aggregators, bridges, lending, staking, perps, multi-send, NFT and on-chain launchpads pay out",
        "from their smart contracts, not from a wallet. Explorers/analytics/tax tools and self-custody wallet",
        "apps hold no funds. Binance Launchpad pays out through Binance (see Binance).",
        "",
        "## Not covered",
        "",
        "Tron, Solana, Bitcoin and Polygon are not in this dataset. Look these up on Tronscan / Solscan /",
        "Arkham entity pages by hand.",
        "",
    ]
    for name, by_addr in data.items():
        lines += [f"## {name}", "", "| Address | Tag | Chains tagged |", "|---|---|---|"]
        for addr, info in sorted(by_addr.items(), key=tag_sort_key):
            lines.append(f"| `{addr}` | {' / '.join(sorted(info['tags']))} | {', '.join(sorted(info['chains']))} |")
        lines.append("")
    Path(path).write_text("\n".join(lines))


if __name__ == "__main__":
    accounts_csv = sys.argv[1]
    commit = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    here = Path(__file__).parent
    data = collect(accounts_csv)
    write_csv(data, here / "platform-withdrawal-addresses.csv")
    write_md(data, here / "platform-withdrawal-addresses.md", commit)
    print({k: len(v) for k, v in data.items()})
