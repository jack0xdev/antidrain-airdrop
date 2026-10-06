"""Burner wallet with a hard-coded safety policy.

The model never sees the private key and cannot sign anything directly: every
request from a web page (via wallet_inject.js) or from the agent's contract
tools lands in `Wallet.handle()`, which enforces the rules below in code.

Rules (enforced here, not in the prompt, so a malicious page can't talk the
agent out of them):
  * eth_sign (raw hash signing) is always refused.
  * Typed-data signatures that can move assets (ERC-20 Permit, Permit2,
    Seaport listings, Safe txs, delegations) are always refused.
  * Transactions calling approve / setApprovalForAll / increaseAllowance /
    transfer / transferFrom / safeTransferFrom / permit are always refused.
  * Per-transaction and daily native-coin spending caps.
  * Every transaction and every non-login signature needs your Telegram tap
    (unless REQUIRE_TX_APPROVAL=false for txs inside the caps).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
from eth_abi import decode as abi_decode
from eth_abi import encode as abi_encode
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import function_signature_to_4byte_selector, to_checksum_address

from .config import Config

log = logging.getLogger(__name__)

Approver = Callable[[str], Awaitable[bool]]
Notifier = Callable[[str], Awaitable[None]]

RISKY_SELECTORS = {
    "0x095ea7b3": "approve(address,uint256) - lets a contract spend your tokens",
    "0xa22cb465": "setApprovalForAll(address,bool) - hands over ALL your NFTs",
    "0x39509351": "increaseAllowance(address,uint256)",
    "0xd73dd623": "increaseApproval(address,uint256)",
    "0xa9059cbb": "transfer(address,uint256) - sends tokens away",
    "0x23b872dd": "transferFrom(address,address,uint256) - moves tokens/NFTs",
    "0x42842e0e": "safeTransferFrom(address,address,uint256) - moves an NFT",
    "0xb88d4fde": "safeTransferFrom(address,address,uint256,bytes) - moves an NFT",
    "0xf242432a": "safeTransferFrom(address,address,uint256,uint256,bytes) - moves ERC-1155",
    "0x2eb2c2d6": "safeBatchTransferFrom(...) - moves ERC-1155 batch",
    "0xd505accf": "permit(...) - gasless token approval",
    "0x87517c45": "Permit2 approve(...)",
    "0x2b67b570": "Permit2 permit(...)",
    "0x4000aea0": "transferAndCall(address,uint256,bytes) - sends tokens away",
    "0x9bd9bbc6": "ERC-777 send(address,uint256,bytes) - sends tokens away",
    "0xfad8b32a": "ERC-777 authorizeOperator(address) - hands over tokens",
    "0xac9650d8": "multicall(bytes[]) - can hide approvals inside",
    "0x5ae401dc": "multicall(uint256,bytes[]) - can hide approvals inside",
}

BLOCKED_TYPED_DATA = {
    "Permit", "PermitSingle", "PermitBatch", "PermitTransferFrom",
    "PermitBatchTransferFrom", "PermitWitnessTransferFrom",
    "PermitBatchWitnessTransferFrom", "OrderComponents", "BulkOrder", "Order",
    "SafeTx", "Delegation", "Delegate",
}

READ_METHODS = {
    "eth_blockNumber", "eth_call", "eth_estimateGas", "eth_feeHistory",
    "eth_gasPrice", "eth_getBalance", "eth_getBlockByHash", "eth_getBlockByNumber",
    "eth_getCode", "eth_getLogs", "eth_getStorageAt", "eth_getTransactionByHash",
    "eth_getTransactionCount", "eth_getTransactionReceipt", "eth_maxPriorityFeePerGas",
    "net_version", "eth_syncing",
}


class WalletError(Exception):
    def __init__(self, message: str, code: int = 4001):
        super().__init__(message)
        self.code = code


def _hex(n: int) -> str:
    return hex(n)


def _to_int(v: Any, default: int = 0) -> int:
    if v is None or v == "":
        return default
    if isinstance(v, int):
        return v
    s = str(v)
    return int(s, 16) if s.startswith("0x") else int(s)


def _raw_hex(raw: Any) -> str:
    h = raw.hex() if hasattr(raw, "hex") else str(raw)
    return h if h.startswith("0x") else "0x" + h


class Wallet:
    def __init__(self, cfg: Config, approve: Approver, notify: Notifier):
        if not cfg.private_key:
            raise ValueError("BURNER_PRIVATE_KEY is not set")
        self.cfg = cfg
        self._account = Account.from_key(cfg.private_key)
        self.address: str = self._account.address
        self.chain_id: int = cfg.default_chain_id
        self._approve = approve
        self._notify = notify
        self._http = httpx.AsyncClient(timeout=30)
        self._spend_file: Path = cfg.data_dir / "spend.json"
        self._audit_file: Path = cfg.data_dir / "wallet-audit.jsonl"
        # set by the browser so pages hear about chain switches
        self.on_chain_changed: Callable[[str], Awaitable[None]] | None = None

    # ------------------------------------------------------------------ RPC
    async def rpc(self, method: str, params: list | None = None, chain_id: int | None = None) -> Any:
        chain = self.cfg.chains[chain_id or self.chain_id]
        r = await self._http.post(chain["rpc"], json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []})
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            err = body["error"]
            raise WalletError(err.get("message", "RPC error"), err.get("code", -32603))
        return body["result"]

    # -------------------------------------------------------------- helpers
    def _audit(self, entry: dict) -> None:
        entry["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
        with self._audit_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _spent_today(self, symbol: str) -> int:
        today = dt.date.today().isoformat()
        try:
            data = json.loads(self._spend_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return 0
        return int(data.get(today, {}).get(symbol, 0))

    def _add_spend(self, symbol: str, wei: int) -> None:
        today = dt.date.today().isoformat()
        try:
            data = json.loads(self._spend_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data = {today: data.get(today, {})}  # keep only today
        data[today][symbol] = int(data[today].get(symbol, 0)) + wei
        self._spend_file.write_text(json.dumps(data))

    def _chain_label(self, cid: int | None = None) -> str:
        cid = cid or self.chain_id
        c = self.cfg.chains.get(cid, {})
        return f"{c.get('name', 'Unknown')} ({cid})"

    async def _set_chain(self, cid: int) -> None:
        if cid == self.chain_id:
            return
        self.chain_id = cid
        if self.on_chain_changed:
            await self.on_chain_changed(_hex(cid))

    # ------------------------------------------------------------ entrypoint
    async def handle(self, origin: str, method: str, params: list) -> Any:
        """Handle one EIP-1193 request. Raises WalletError on refusal."""
        try:
            result = await self._dispatch(origin, method, params)
            if method not in READ_METHODS and method not in ("eth_chainId", "eth_accounts"):
                self._audit({"origin": origin, "method": method, "ok": True})
            return result
        except WalletError as e:
            self._audit({"origin": origin, "method": method, "ok": False, "error": str(e)})
            raise

    async def _dispatch(self, origin: str, method: str, params: list) -> Any:
        if method in ("eth_requestAccounts", "eth_accounts"):
            return [self.address]
        if method == "eth_coinbase":
            return self.address
        if method == "eth_chainId":
            return _hex(self.chain_id)
        if method == "net_version":
            return str(self.chain_id)
        if method == "web3_clientVersion":
            return "AgentWallet/1.0"
        if method in ("wallet_getPermissions", "wallet_requestPermissions"):
            return [{"parentCapability": "eth_accounts", "caveats": [{"type": "restrictReturnedAccounts", "value": [self.address]}]}]
        if method == "wallet_revokePermissions":
            return None
        if method == "wallet_watchAsset":
            return True
        if method == "wallet_switchEthereumChain":
            cid = _to_int(params[0]["chainId"])
            if cid not in self.cfg.chains:
                raise WalletError(f"Unrecognized chain {cid}", 4902)
            await self._set_chain(cid)
            return None
        if method == "wallet_addEthereumChain":
            return await self._add_chain(origin, params[0])
        if method == "eth_sign":
            raise WalletError("eth_sign (blind hash signing) is disabled - classic drainer trick")
        if method == "personal_sign":
            return await self._personal_sign(origin, params)
        if method in ("eth_signTypedData_v4", "eth_signTypedData_v3", "eth_signTypedData"):
            return await self._sign_typed(origin, params)
        if method == "eth_sendTransaction":
            return await self.send_transaction(origin, params[0])
        if method in READ_METHODS:
            return await self.rpc(method, params)
        raise WalletError(f"Method {method} not supported", 4200)

    # -------------------------------------------------------------- chains
    async def _add_chain(self, origin: str, p: dict) -> None:
        cid = _to_int(p["chainId"])
        if cid in self.cfg.chains:
            await self._set_chain(cid)
            return None
        rpc = (p.get("rpcUrls") or [None])[0]
        name = p.get("chainName", f"chain {cid}")
        if not rpc or not rpc.startswith("https://"):
            raise WalletError("Chain needs an https RPC URL")
        ok = await self._approve(
            f"🔗 <b>Add new network?</b>\nSite: {origin}\nName: {name}\nChain ID: {cid}\nRPC: {rpc}"
        )
        if not ok:
            raise WalletError("User rejected adding the network")
        self.cfg.chains[cid] = {
            "name": name, "rpc": rpc,
            "symbol": (p.get("nativeCurrency") or {}).get("symbol", "ETH"),
            "explorer": (p.get("blockExplorerUrls") or [""])[0],
        }
        await self._set_chain(cid)
        return None

    # ------------------------------------------------------------ signatures
    async def _personal_sign(self, origin: str, params: list) -> str:
        a, b = params[0], params[1] if len(params) > 1 else self.address
        # spec order is (message, address); some dApps send it reversed
        msg = b if isinstance(a, str) and a.lower() == self.address.lower() else a
        if isinstance(msg, str) and msg.startswith("0x"):
            raw = bytes.fromhex(msg[2:])
        else:
            raw = str(msg).encode()
        try:
            text = raw.decode("utf-8")
            readable = text.isprintable() or all(ch.isprintable() or ch in "\n\r\t" for ch in text)
        except UnicodeDecodeError:
            text, readable = raw.hex(), False

        if readable and self.cfg.auto_approve_login_signatures:
            await self._notify(f"✍️ Auto-signed a login message for {origin}:\n<pre>{_esc(text[:600])}</pre>")
        else:
            ok = await self._approve(
                f"✍️ <b>Signature request</b>\nSite: {origin}\nChain: {self._chain_label()}\n"
                f"Message:\n<pre>{_esc(text[:1500])}</pre>"
            )
            if not ok:
                raise WalletError("User rejected the signature")
        signed = self._account.sign_message(encode_defunct(primitive=raw))
        return _raw_hex(signed.signature)

    async def _sign_typed(self, origin: str, params: list) -> str:
        data = params[1] if isinstance(params[0], str) and params[0].lower() == self.address.lower() else params[0]
        if isinstance(data, str):
            data = json.loads(data)
        primary = data.get("primaryType", "")
        domain = data.get("domain", {})
        if primary in BLOCKED_TYPED_DATA:
            await self._notify(
                f"🛑 Blocked a <b>{_esc(primary)}</b> signature from {origin}. "
                "This type of signature can hand over your tokens/NFTs."
            )
            raise WalletError(f"{primary} signatures are blocked by policy")
        ok = await self._approve(
            f"✍️ <b>Typed-data signature</b>\nSite: {origin}\nType: {_esc(primary)}\n"
            f"Domain: {_esc(json.dumps(domain)[:400])}\n"
            f"Message:\n<pre>{_esc(json.dumps(data.get('message', {}), indent=1)[:1500])}</pre>"
        )
        if not ok:
            raise WalletError("User rejected the signature")
        signed = self._account.sign_typed_data(full_message=data)
        return _raw_hex(signed.signature)

    # ---------------------------------------------------------- transactions
    async def send_transaction(self, origin: str, tx: dict, chain_id: int | None = None) -> str:
        if chain_id and chain_id != self.chain_id:
            await self._set_chain(chain_id)
        cid = self.chain_id
        chain = self.cfg.chains[cid]
        symbol = chain.get("symbol", "ETH")

        frm = tx.get("from")
        if frm and frm.lower() != self.address.lower():
            raise WalletError("Transaction 'from' is not this wallet")
        to = tx.get("to")
        if not to:
            raise WalletError("Contract deployment is disabled")
        to = to_checksum_address(to)
        value = _to_int(tx.get("value"))
        data = tx.get("data") or tx.get("input") or "0x"
        selector = data[:10].lower() if len(data) >= 10 else ""

        if selector in RISKY_SELECTORS:
            await self._notify(
                f"🛑 Blocked a transaction from {origin}: <b>{_esc(RISKY_SELECTORS[selector])}</b> to {to}"
            )
            raise WalletError(f"Blocked by policy: {RISKY_SELECTORS[selector]}")

        max_wei = int(self.cfg.max_tx_value_eth * 10**18)
        if value > max_wei:
            raise WalletError(f"Value {value / 1e18} {symbol} is above MAX_TX_VALUE_ETH={self.cfg.max_tx_value_eth}")
        cap_wei = int(self.cfg.daily_spend_cap_eth * 10**18)
        if self._spent_today(symbol) + value > cap_wei:
            raise WalletError(f"Daily spend cap of {self.cfg.daily_spend_cap_eth} {symbol} reached")

        base = {"from": self.address, "to": to, "value": _hex(value), "data": data}
        try:
            gas = _to_int(tx.get("gas")) or int(_to_int(await self.rpc("eth_estimateGas", [base])) * 1.25)
        except WalletError as e:
            raise WalletError(f"Transaction would fail (gas estimation reverted): {e}") from e

        block = await self.rpc("eth_getBlockByNumber", ["latest", False])
        base_fee = _to_int(block.get("baseFeePerGas"))
        fee_fields: dict[str, int]
        if block.get("baseFeePerGas") is not None:
            try:
                prio = _to_int(await self.rpc("eth_maxPriorityFeePerGas"))
            except WalletError:
                prio = 10**9
            max_fee = _to_int(tx.get("maxFeePerGas")) or (2 * base_fee + prio)
            prio = min(_to_int(tx.get("maxPriorityFeePerGas")) or prio, max_fee)
            fee_fields = {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": prio}
            worst_fee = gas * max_fee
        else:
            gas_price = _to_int(tx.get("gasPrice")) or _to_int(await self.rpc("eth_gasPrice"))
            fee_fields = {"gasPrice": gas_price}
            worst_fee = gas * gas_price

        balance = _to_int(await self.rpc("eth_getBalance", [self.address, "latest"]))
        if balance < value + worst_fee:
            raise WalletError(
                f"Not enough {symbol}: have {balance / 1e18:.6f}, need up to {(value + worst_fee) / 1e18:.6f}"
            )

        summary = (
            f"💸 <b>Transaction request</b>\nSite: {_esc(origin)}\nChain: {self._chain_label()}\n"
            f"To: <code>{to}</code>\nValue: {value / 1e18:.6f} {symbol}\n"
            f"Function: <code>{selector or '(plain transfer)'}</code>\n"
            f"Max gas cost: {worst_fee / 1e18:.6f} {symbol}\n"
            f"Explorer: {chain.get('explorer', '')}/address/{to}"
        )
        if self.cfg.require_tx_approval:
            if not await self._approve(summary):
                raise WalletError("User rejected the transaction")
        else:
            await self._notify(summary + "\n(auto-approved: inside caps)")

        nonce = _to_int(await self.rpc("eth_getTransactionCount", [self.address, "pending"]))
        to_sign = {"chainId": cid, "nonce": nonce, "to": to, "value": value, "data": data, "gas": gas, **fee_fields}
        if "maxFeePerGas" in fee_fields:
            to_sign["type"] = 2
        signed = self._account.sign_transaction(to_sign)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = await self.rpc("eth_sendRawTransaction", [_raw_hex(raw)])
        self._add_spend(symbol, value)
        self._audit({"origin": origin, "method": "sent", "to": to, "value": value, "hash": tx_hash, "chain": cid})
        await self._notify(f"✅ Sent: {chain.get('explorer', '')}/tx/{tx_hash}")
        return tx_hash

    # -------------------------------------------------- tools for the agent
    async def status(self) -> str:
        lines = [f"Address: {self.address}", f"Current chain: {self._chain_label()}"]
        for cid in sorted({self.chain_id, self.cfg.default_chain_id}):
            try:
                bal = _to_int(await self.rpc("eth_getBalance", [self.address, "latest"], cid))
                lines.append(f"Balance on {self._chain_label(cid)}: {bal / 1e18:.6f} {self.cfg.chains[cid].get('symbol')}")
            except Exception as e:  # noqa: BLE001
                lines.append(f"Balance on {self._chain_label(cid)}: error {e}")
        lines.append(f"Known chains: {', '.join(self._chain_label(c) for c in self.cfg.chains)}")
        return "\n".join(lines)

    async def contract_write(self, chain_id: int, to: str, signature: str, args: list, value_eth: str) -> str:
        if chain_id not in self.cfg.chains:
            raise WalletError(f"Unknown chain {chain_id}")
        data = encode_call(signature, args)
        value = int(float(value_eth or "0") * 10**18)
        return await self.send_transaction("agent:contract_write", {"to": to, "value": _hex(value), "data": data}, chain_id)

    async def contract_read(self, chain_id: int, to: str, signature: str, args: list, returns: str) -> str:
        if chain_id not in self.cfg.chains:
            raise WalletError(f"Unknown chain {chain_id}")
        data = encode_call(signature, args)
        out = await self.rpc("eth_call", [{"to": to_checksum_address(to), "data": data}, "latest"], chain_id)
        if not returns:
            return out
        types = split_types(returns.strip()[1:-1] if returns.strip().startswith("(") else returns)
        decoded = abi_decode(types, bytes.fromhex(out[2:]))
        return json.dumps([_jsonable(v) for v in decoded])

    async def close(self) -> None:
        await self._http.aclose()


# ---------------------------------------------------------------- ABI utils
def split_types(s: str) -> list[str]:
    """Split 'uint256,(address,uint8)[],bytes' at top-level commas."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _coerce(typ: str, val: Any) -> Any:
    if typ.endswith("]"):
        inner = typ[: typ.rindex("[")]
        return [_coerce(inner, v) for v in val]
    if typ.startswith("("):
        return tuple(_coerce(t, v) for t, v in zip(split_types(typ[1:-1]), val))
    if typ.startswith(("uint", "int")):
        return _to_int(val)
    if typ == "address":
        return to_checksum_address(val)
    if typ == "bool":
        return val if isinstance(val, bool) else str(val).lower() == "true"
    if typ.startswith("bytes"):
        return bytes.fromhex(val[2:] if str(val).startswith("0x") else val)
    return val


def encode_call(signature: str, args: list) -> str:
    m = re.fullmatch(r"\s*(\w+)\((.*)\)\s*", signature)
    if not m:
        raise WalletError(f"Bad function signature: {signature}")
    types = split_types(m.group(2))
    if len(types) != len(args):
        raise WalletError(f"{signature} expects {len(types)} args, got {len(args)}")
    canonical = f"{m.group(1)}({','.join(types)})"
    selector = function_signature_to_4byte_selector(canonical)
    encoded = abi_encode(types, [_coerce(t, a) for t, a in zip(types, args)])
    return "0x" + (selector + encoded).hex()


def _jsonable(v: Any) -> Any:
    if isinstance(v, bytes):
        return "0x" + v.hex()
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return v


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
