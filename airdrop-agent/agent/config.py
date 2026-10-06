"""All settings come from environment variables (see .env.example)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


# chainId -> (name, rpc url, native symbol, explorer)
DEFAULT_CHAINS: dict[int, dict] = {
    1: {"name": "Ethereum", "rpc": "https://ethereum-rpc.publicnode.com", "symbol": "ETH", "explorer": "https://etherscan.io"},
    8453: {"name": "Base", "rpc": "https://mainnet.base.org", "symbol": "ETH", "explorer": "https://basescan.org"},
    42161: {"name": "Arbitrum One", "rpc": "https://arb1.arbitrum.io/rpc", "symbol": "ETH", "explorer": "https://arbiscan.io"},
    10: {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "symbol": "ETH", "explorer": "https://optimistic.etherscan.io"},
    137: {"name": "Polygon", "rpc": "https://polygon-rpc.com", "symbol": "POL", "explorer": "https://polygonscan.com"},
    56: {"name": "BNB Chain", "rpc": "https://bsc-dataseed.binance.org", "symbol": "BNB", "explorer": "https://bscscan.com"},
}


@dataclass
class Config:
    # Claude
    model: str = field(default_factory=lambda: os.getenv("AGENT_MODEL", "claude-opus-5-5"))
    effort: str = field(default_factory=lambda: os.getenv("AGENT_EFFORT", "medium"))
    max_steps: int = field(default_factory=lambda: _int("MAX_STEPS_PER_TASK", 80))

    # Telegram
    telegram_token: str = field(default_factory=lambda: os.environ["TELEGRAM_BOT_TOKEN"])
    telegram_owner_id: int = field(default_factory=lambda: int(os.environ["TELEGRAM_OWNER_ID"]))

    # Paths
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "/data")))

    # Wallet
    private_key: str | None = field(default_factory=lambda: os.getenv("BURNER_PRIVATE_KEY") or None)
    default_chain_id: int = field(default_factory=lambda: _int("DEFAULT_CHAIN_ID", 1))
    require_tx_approval: bool = field(default_factory=lambda: _bool("REQUIRE_TX_APPROVAL", True))
    auto_approve_login_signatures: bool = field(default_factory=lambda: _bool("AUTO_APPROVE_LOGIN_SIGNATURES", True))
    max_tx_value_eth: float = field(default_factory=lambda: _float("MAX_TX_VALUE_ETH", 0.01))
    daily_spend_cap_eth: float = field(default_factory=lambda: _float("DAILY_SPEND_CAP_ETH", 0.05))
    approval_timeout_s: int = field(default_factory=lambda: _int("APPROVAL_TIMEOUT_SECONDS", 900))

    # Browser
    blocked_url_patterns: list[str] = field(default_factory=lambda: [
        p.strip() for p in os.getenv(
            "BLOCKED_URL_PATTERNS",
            "myaccount.google.com,accounts.google.com/signout,x.com/settings,twitter.com/settings,"
            "discord.com/channels/@me/settings,mail.google.com/mail/u/0/#settings",
        ).split(",") if p.strip()
    ])

    chains: dict[int, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chains = {k: dict(v) for k, v in DEFAULT_CHAINS.items()}
        # Extra/override chains: EXTRA_CHAINS_JSON='{"46630": {"name": "Robinhood Chain", "rpc": "https://...", "symbol": "ETH", "explorer": "https://..."}}'
        extra = os.getenv("EXTRA_CHAINS_JSON")
        if extra:
            for cid, info in json.loads(extra).items():
                self.chains[int(cid)] = info
        # Per-chain RPC override, e.g. RPC_1=https://eth-mainnet.g.alchemy.com/v2/KEY
        for cid in list(self.chains):
            override = os.getenv(f"RPC_{cid}")
            if override:
                self.chains[cid]["rpc"] = override
        if self.default_chain_id not in self.chains:
            raise ValueError(f"DEFAULT_CHAIN_ID {self.default_chain_id} is not in the chain list")

    @property
    def browser_profile_dir(self) -> Path:
        return self.data_dir / "browser-profile"

    @property
    def profile_file(self) -> Path:
        return Path(os.getenv("PROFILE_FILE", str(self.data_dir / "profile.yaml")))

    @property
    def tasks_file(self) -> Path:
        return Path(os.getenv("TASKS_FILE", str(self.data_dir / "tasks.yaml")))
