"""Tool definitions the model sees, and the code that runs them."""
from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from .browser import BrowserSession
from .wallet import Wallet, WalletError


class HumanIO(Protocol):
    async def ask(self, question: str, image: bytes | None) -> str: ...


def _tool(name: str, description: str, props: dict[str, Any]) -> dict:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": list(props),
            "additionalProperties": False,
        },
    }


INT = {"type": "integer"}
STR = {"type": "string"}
BOOL = {"type": "boolean"}

# Order is fixed so the tools prefix stays cacheable.
TOOLS: list[dict] = [
    _tool("navigate", "Open a URL in the active tab. Returns a page snapshot.", {"url": STR}),
    _tool("page_snapshot", "List the interactive elements ([id] + label) and visible text of the active tab.", {}),
    _tool("screenshot", "Take a screenshot of the active tab (use for visual layouts, modals, captchas).", {}),
    _tool("click", "Click an element by its [id] from the latest snapshot. Returns a new snapshot.", {"element_id": INT}),
    _tool(
        "type_text",
        "Replace the content of an input/textarea/editor [id] with text. press_enter submits after typing.",
        {"element_id": INT, "text": STR, "press_enter": BOOL},
    ),
    _tool("select_option", "Choose an option (by visible label or value) in a <select> [id].", {"element_id": INT, "option": STR}),
    _tool("press_key", "Press a keyboard key or combo in the active tab, e.g. Enter, Escape, Tab, Control+Enter.", {"key": STR}),
    _tool("scroll", "Scroll the active tab.", {"direction": {"type": "string", "enum": ["up", "down"]}}),
    _tool("wait", "Wait for the page (or the owner's wallet approval) for N seconds, max 60. Returns a snapshot.", {"seconds": INT}),
    _tool("go_back", "Browser back button.", {}),
    _tool("list_tabs", "List open tabs with their index.", {}),
    _tool("switch_tab", "Make tab [index] the active tab.", {"index": INT}),
    _tool(
        "ask_human",
        "Ask the owner on Telegram and wait for their reply (captcha, SMS code, missing info, decisions). "
        "attach_screenshot sends what you currently see.",
        {"question": STR, "attach_screenshot": BOOL},
    ),
    _tool("wallet_status", "Burner wallet address, current chain and balances.", {}),
    _tool(
        "contract_read",
        "Call a view function. function_signature like 'balanceOf(address)'; args_json is a JSON array; "
        "returns like '(uint256)' (or empty string for raw hex).",
        {"chain_id": INT, "contract": STR, "function_signature": STR, "args_json": STR, "returns": STR},
    ),
    _tool(
        "contract_write",
        "Send a transaction calling a contract function directly (e.g. a mint when the website UI is broken). "
        "Goes through the wallet policy and the owner's Telegram approval. value_eth is the native coin to send, '0' for none.",
        {"chain_id": INT, "contract": STR, "function_signature": STR, "args_json": STR, "value_eth": STR},
    ),
    _tool(
        "finish_task",
        "End the current task with an honest report for the owner.",
        {"status": {"type": "string", "enum": ["success", "partial", "failed"]}, "summary": STR},
    ),
]

SNAPSHOT_AFTER = {"navigate", "click", "type_text", "select_option", "press_key", "scroll", "wait", "go_back", "switch_tab"}


@dataclass
class ToolOutcome:
    content: list[dict]
    is_error: bool = False
    finished: dict | None = None


def _text(s: str) -> dict:
    return {"type": "text", "text": s}


def _image(jpeg: bytes) -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(jpeg).decode()},
    }


class ToolExecutor:
    def __init__(self, browser: BrowserSession, wallet: Wallet | None, human: HumanIO,
                 progress: Callable[[str], Awaitable[None]] | None = None):
        self.browser = browser
        self.wallet = wallet
        self.human = human
        self.progress = progress

    async def run(self, name: str, args: dict) -> ToolOutcome:
        try:
            out = await self._run(name, args)
        except WalletError as e:
            return ToolOutcome([_text(f"Wallet refused: {e}")], is_error=True)
        except Exception as e:  # noqa: BLE001
            msg = f"{type(e).__name__}: {e}"
            if name in SNAPSHOT_AFTER or name == "page_snapshot":
                try:
                    msg += "\n\n" + await self.browser.snapshot()
                except Exception:  # noqa: BLE001
                    pass
            return ToolOutcome([_text(msg[:20000])], is_error=True)
        events = self.browser.pop_events()
        if events:
            if out.content and out.content[0]["type"] == "text":
                out.content[0]["text"] = f"[browser events]\n{events}\n\n" + out.content[0]["text"]
            else:
                out.content.insert(0, _text(f"[browser events]\n{events}"))
        return out

    async def _run(self, name: str, a: dict) -> ToolOutcome:
        b = self.browser
        if name == "finish_task":
            return ToolOutcome([_text("Task closed.")], finished={"status": a["status"], "summary": a["summary"]})
        if name == "page_snapshot":
            return ToolOutcome([_text(await b.snapshot())])
        if name == "screenshot":
            return ToolOutcome([_image(await b.screenshot())])
        if name == "list_tabs":
            return ToolOutcome([_text(await b.list_tabs())])
        if name == "ask_human":
            img = await b.screenshot() if a["attach_screenshot"] else None
            if self.progress:
                await self.progress("❓ waiting for your reply")
            answer = await self.human.ask(a["question"], img)
            return ToolOutcome([_text(f"Owner replied: {answer}")])
        if name == "wallet_status":
            if not self.wallet:
                return ToolOutcome([_text("No wallet configured (BURNER_PRIVATE_KEY empty).")], is_error=True)
            return ToolOutcome([_text(await self.wallet.status())])
        if name in ("contract_read", "contract_write"):
            if not self.wallet:
                return ToolOutcome([_text("No wallet configured.")], is_error=True)
            args = json.loads(a["args_json"] or "[]")
            if name == "contract_read":
                res = await self.wallet.contract_read(a["chain_id"], a["contract"], a["function_signature"], args, a["returns"])
                return ToolOutcome([_text(res)])
            tx = await self.wallet.contract_write(a["chain_id"], a["contract"], a["function_signature"], args, a["value_eth"])
            return ToolOutcome([_text(f"Transaction sent: {tx}")])

        # browser actions that return a fresh snapshot
        if name == "navigate":
            result = await b.navigate(a["url"])
        elif name == "click":
            result = await b.click(a["element_id"])
        elif name == "type_text":
            result = await b.type_text(a["element_id"], a["text"], a["press_enter"])
        elif name == "select_option":
            result = await b.select_option(a["element_id"], a["option"])
        elif name == "press_key":
            result = await b.press_key(a["key"])
        elif name == "scroll":
            result = await b.scroll(a["direction"])
        elif name == "wait":
            secs = max(1, min(60, int(a["seconds"])))
            await asyncio.sleep(secs)
            result = f"Waited {secs}s"
        elif name == "go_back":
            result = await b.go_back()
        elif name == "switch_tab":
            result = await b.switch_tab(a["index"])
        else:
            return ToolOutcome([_text(f"Unknown tool {name}")], is_error=True)
        return ToolOutcome([_text(f"{result}\n\n{await b.snapshot()}")])
