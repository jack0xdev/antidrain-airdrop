"""Persistent Chromium session the agent drives through Playwright.

The profile directory keeps your X / Discord / Gmail logins between runs, so
the agent never needs your passwords: you log in once yourself through the
VNC screen (/login in Telegram) and the cookies stay on the VPS.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Frame, Page, Playwright, async_playwright

from .config import Config
from .wallet import Wallet, WalletError

log = logging.getLogger(__name__)

INJECT_JS = (Path(__file__).parent / "wallet_inject.js").read_text()

# Tags every visible interactive element with data-agent-id and returns a
# compact description of each, plus the visible text of the frame.
SNAPSHOT_JS = r"""
([startId, maxText]) => {
  const SEL = [
    'a[href]', 'button', 'input:not([type=hidden])', 'textarea', 'select', 'summary',
    '[role=button]', '[role=link]', '[role=checkbox]', '[role=radio]', '[role=switch]',
    '[role=tab]', '[role=menuitem]', '[role=menuitemcheckbox]', '[role=option]',
    '[role=combobox]', '[role=textbox]', '[contenteditable=""]', '[contenteditable=true]',
    'label', '[onclick]', '[tabindex]:not([tabindex="-1"])'
  ].join(',');
  document.querySelectorAll('[data-agent-id]').forEach(e => e.removeAttribute('data-agent-id'));
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const visible = el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity || '1') > 0.05;
  };
  const out = [];
  let id = startId;
  const seen = new Set();
  for (const el of document.querySelectorAll(SEL)) {
    if (!visible(el)) continue;
    // skip a label that just wraps an input we'll list anyway
    if (el.tagName === 'LABEL' && el.querySelector('input,select,textarea')) continue;
    if (seen.has(el)) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role') || '';
    const type = el.getAttribute('type') || '';
    let label = el.getAttribute('aria-label') || '';
    if (!label && el.labels && el.labels[0]) label = el.labels[0].innerText;
    if (!label) label = el.innerText || el.getAttribute('title') || el.getAttribute('alt') || '';
    if (!label) { const img = el.querySelector('img[alt]'); if (img) label = img.alt; }
    let value = '';
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      value = type === 'password' ? (el.value ? '********' : '') : (el.value || '');
    } else if (el.isContentEditable) {
      value = el.innerText || '';
    }
    const checked = (type === 'checkbox' || type === 'radio') ? el.checked
      : (el.getAttribute('aria-checked') ?? el.getAttribute('aria-selected') ?? null);
    el.setAttribute('data-agent-id', String(id));
    out.push({
      id, tag, role, type,
      label: clean(label).slice(0, 120),
      placeholder: clean(el.getAttribute('placeholder')).slice(0, 80),
      name: el.getAttribute('name') || '',
      href: tag === 'a' ? (el.getAttribute('href') || '').slice(0, 120) : '',
      value: clean(value).slice(0, 120),
      checked,
      disabled: !!(el.disabled || el.getAttribute('aria-disabled') === 'true'),
      editable: el.isContentEditable,
      inView: r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth,
    });
    id++;
  }
  const text = clean(document.body ? document.body.innerText : '').slice(0, maxText);
  return { elements: out, text, nextId: id };
}
"""

MAX_ELEMENTS = 250


class BrowserSession:
    def __init__(self, cfg: Config, wallet: Wallet | None):
        self.cfg = cfg
        self.wallet = wallet
        self._pw: Playwright | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._id_frames: dict[int, Frame] = {}
        self._events: list[str] = []
        self._login_proc: subprocess.Popen | None = None

    # ------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        if self._pw is None:
            self._pw = await async_playwright().start()
        self.cfg.browser_profile_dir.mkdir(parents=True, exist_ok=True)
        self.context = await self._pw.chromium.launch_persistent_context(
            str(self.cfg.browser_profile_dir),
            executable_path=os.getenv("CHROMIUM_PATH") or None,
            headless=False,
            viewport={"width": 1366, "height": 850},
            locale="en-US",
            args=["--no-first-run", "--no-default-browser-check", "--disable-dev-shm-usage"],
        )
        if self.wallet:
            await self.context.expose_binding("__agentWalletRequest", self._wallet_binding)
            await self.context.add_init_script(
                script=INJECT_JS.replace("__CHAIN_ID_HEX__", hex(self.wallet.chain_id))
            )
            self.wallet.on_chain_changed = self._broadcast_chain
        self.context.on("page", self._on_new_page)
        for p in self.context.pages:
            self._watch_page(p)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def stop(self) -> None:
        if self.context:
            try:
                await self.context.close()
            except Exception:  # noqa: BLE001
                pass
        self.context = None
        self.page = None

    async def shutdown(self) -> None:
        await self.stop()
        if self._pw:
            await self._pw.stop()
            self._pw = None

    # ------------------------------------------- manual login (no automation)
    async def start_manual_login(self, url: str = "https://x.com/login") -> None:
        """Close the automated browser and open a plain Chromium window on the
        same profile, so you can log in to X / Discord / Gmail through VNC."""
        await self.stop()
        if self._pw is None:
            self._pw = await async_playwright().start()
        exe = os.getenv("CHROMIUM_PATH") or self._pw.chromium.executable_path
        # --no-sandbox matches what Playwright passes; containers can't use Chrome's sandbox
        self._login_proc = subprocess.Popen(
            [exe, f"--user-data-dir={self.cfg.browser_profile_dir}", "--no-first-run",
             "--no-default-browser-check", "--disable-dev-shm-usage", "--no-sandbox", url],
            env={**os.environ},
        )
        await asyncio.sleep(2)
        if self._login_proc.poll() is not None:
            self._login_proc = None
            await self.start()
            raise RuntimeError("Chromium for login exited immediately - check the container logs")

    async def finish_manual_login(self) -> None:
        if self._login_proc and self._login_proc.poll() is None:
            self._login_proc.send_signal(signal.SIGTERM)  # lets Chromium flush cookies
            try:
                await asyncio.to_thread(self._login_proc.wait, 20)
            except subprocess.TimeoutExpired:
                self._login_proc.kill()
        self._login_proc = None
        await self.start()

    @property
    def in_login_mode(self) -> bool:
        return self._login_proc is not None

    # ------------------------------------------------------------- plumbing
    def _watch_page(self, page: Page) -> None:
        page.on("close", lambda p: self._on_close(p))
        page.on("dialog", lambda d: asyncio.ensure_future(self._on_dialog(d)))

    def _on_new_page(self, page: Page) -> None:
        self._watch_page(page)
        self.page = page
        self._events.append(f"A new tab/popup opened and is now active: {page.url}")

    def _on_close(self, page: Page) -> None:
        if self.page is page and self.context:
            remaining = [p for p in self.context.pages if not p.is_closed() and p is not page]
            self.page = remaining[-1] if remaining else None
            self._events.append(
                f"The active tab closed; switched to {self.page.url if self.page else 'nothing'}"
            )

    async def _on_dialog(self, dialog) -> None:
        self._events.append(f"Browser dialog ({dialog.type}) auto-accepted: {dialog.message[:200]}")
        try:
            await dialog.accept()
        except Exception:  # noqa: BLE001
            pass

    def pop_events(self) -> str:
        ev, self._events = self._events, []
        return "\n".join(ev)

    async def _wallet_binding(self, source: dict, payload: str) -> str:
        req = json.loads(payload)
        frame = source.get("frame")
        url = frame.url if frame else ""
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
        try:
            result = await self.wallet.handle(origin, req.get("method", ""), req.get("params") or [])
            self._events.append(f"Wallet: {req.get('method')} from {origin} -> ok")
            return json.dumps({"result": result})
        except WalletError as e:
            self._events.append(f"Wallet: {req.get('method')} from {origin} -> refused: {e}")
            return json.dumps({"error": {"code": e.code, "message": str(e)}})
        except Exception as e:  # noqa: BLE001
            log.exception("wallet binding failed")
            return json.dumps({"error": {"code": -32603, "message": str(e)}})

    async def _broadcast_chain(self, chain_hex: str) -> None:
        if not self.context:
            return
        hint = f"window.__agentWalletEmit && window.__agentWalletEmit('chainChanged', '{chain_hex}');"
        await self.context.add_init_script(script=hint)
        for p in self.context.pages:
            for f in p.frames:
                try:
                    await f.evaluate(
                        "h => window.__agentWalletEmit && window.__agentWalletEmit('chainChanged', h)", chain_hex
                    )
                except Exception:  # noqa: BLE001
                    pass

    async def _ensure_page(self) -> Page:
        if self.context is None:
            await self.start()
        if self.page is None or self.page.is_closed():
            open_pages = [p for p in self.context.pages if not p.is_closed()]
            self.page = open_pages[-1] if open_pages else await self.context.new_page()
        return self.page

    async def ensure_alive(self) -> None:
        """Restart Chromium if it crashed or someone closed it on the VNC screen."""
        try:
            page = await self._ensure_page()
            await page.evaluate("1")
        except Exception:  # noqa: BLE001
            log.warning("browser not responding - restarting")
            await self.stop()
            await self.start()

    async def _settle(self) -> None:
        page = await self._ensure_page()
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(1.2)

    def _locator(self, element_id: int):
        frame = self._id_frames.get(element_id)
        if frame is None or frame.is_detached():
            raise ValueError(f"Element [{element_id}] is unknown or gone - call page_snapshot again")
        return frame.locator(f'[data-agent-id="{element_id}"]').first

    # -------------------------------------------------------------- actions
    async def navigate(self, url: str) -> str:
        lowered = url.lower()
        for pat in self.cfg.blocked_url_patterns:
            if pat.lower() in lowered:
                return f"Refused: {url} matches a blocked pattern ({pat}). Account settings are off-limits."
        if not urlparse(url).scheme:
            url = "https://" + url
        page = await self._ensure_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:  # noqa: BLE001
            return f"Navigation problem: {e}"
        await asyncio.sleep(1.5)
        return f"Opened {page.url}"

    async def click(self, element_id: int) -> str:
        loc = self._locator(element_id)
        frame = self._id_frames[element_id]

        def gone() -> bool:  # e.g. an OAuth popup that closes itself on "Authorize"
            return frame.is_detached() or frame.page.is_closed()

        try:
            await loc.click(timeout=6000)
        except Exception:  # noqa: BLE001
            if not gone():
                try:
                    await loc.click(timeout=3000, force=True)
                except Exception:  # noqa: BLE001
                    if not gone():
                        await loc.evaluate("e => e.click()")
        await self._settle()
        return f"Clicked [{element_id}]"

    async def type_text(self, element_id: int, text: str, press_enter: bool) -> str:
        loc = self._locator(element_id)
        info = await loc.evaluate("e => ({tag: e.tagName.toLowerCase(), editable: e.isContentEditable})")
        page = await self._ensure_page()
        if info["tag"] in ("input", "textarea") and not info["editable"]:
            await loc.fill(text, timeout=6000)
        else:
            # rich editors (X composer, Discord box) need real key events
            await loc.click(timeout=6000)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await page.keyboard.type(text, delay=12)
        if press_enter:
            await page.keyboard.press("Enter")
            await self._settle()
        return f"Typed {len(text)} chars into [{element_id}]" + (" and pressed Enter" if press_enter else "")

    async def select_option(self, element_id: int, option: str) -> str:
        loc = self._locator(element_id)
        try:
            await loc.select_option(label=option, timeout=5000)
        except Exception:  # noqa: BLE001
            await loc.select_option(value=option, timeout=5000)
        await asyncio.sleep(0.5)
        return f"Selected '{option}' in [{element_id}]"

    async def press_key(self, key: str) -> str:
        page = await self._ensure_page()
        await page.keyboard.press(key)
        await self._settle()
        return f"Pressed {key}"

    async def scroll(self, direction: str) -> str:
        page = await self._ensure_page()
        await page.mouse.move(683, 425)
        await page.mouse.wheel(0, 700 if direction == "down" else -700)
        await asyncio.sleep(0.8)
        return f"Scrolled {direction}"

    async def go_back(self) -> str:
        page = await self._ensure_page()
        await page.go_back(wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1)
        return f"Went back to {page.url}"

    async def list_tabs(self) -> str:
        if not self.context:
            return "No browser"
        lines = []
        for i, p in enumerate(self.context.pages):
            mark = " (active)" if p is self.page else ""
            try:
                title = await p.title()
            except Exception:  # noqa: BLE001
                title = ""
            lines.append(f"{i}: {title[:60]} - {p.url}{mark}")
        return "\n".join(lines)

    async def switch_tab(self, index: int) -> str:
        pages = self.context.pages if self.context else []
        if not 0 <= index < len(pages):
            return f"No tab {index}"
        self.page = pages[index]
        await self.page.bring_to_front()
        return f"Switched to tab {index}: {self.page.url}"

    async def screenshot(self) -> bytes:
        page = await self._ensure_page()
        return await page.screenshot(type="jpeg", quality=70)

    async def snapshot(self) -> str:
        page = await self._ensure_page()
        self._id_frames.clear()
        next_id = 1
        blocks: list[str] = []
        elements: list[tuple[dict, Frame]] = []
        frames = [page.main_frame] + [f for f in page.frames if f is not page.main_frame][:8]
        for idx, frame in enumerate(frames):
            try:
                res = await frame.evaluate(SNAPSHOT_JS, [next_id, 5000 if idx == 0 else 1200])
            except Exception:  # noqa: BLE001
                continue
            next_id = res["nextId"]
            for el in res["elements"]:
                elements.append((el, frame))
            if res["text"]:
                where = "PAGE TEXT" if idx == 0 else f"IFRAME {frame.url[:80]} TEXT"
                blocks.append(f"--- {where} ---\n{res['text']}")

        if len(elements) > MAX_ELEMENTS:
            in_view = [e for e in elements if e[0]["inView"]]
            off = [e for e in elements if not e[0]["inView"]]
            elements = sorted(in_view + off[: max(0, MAX_ELEMENTS - len(in_view))], key=lambda e: e[0]["id"])

        lines = []
        for el, frame in elements:
            self._id_frames[el["id"]] = frame
            kind = el["tag"]
            if el["type"]:
                kind += f"[{el['type']}]"
            if el["role"]:
                kind += f" role={el['role']}"
            if el["editable"]:
                kind += " editable"
            parts = [f"[{el['id']}] {kind}"]
            if el["label"]:
                parts.append(f'"{el["label"]}"')
            if el["placeholder"]:
                parts.append(f'placeholder="{el["placeholder"]}"')
            if el["name"]:
                parts.append(f"name={el['name']}")
            if el["value"]:
                parts.append(f'value="{el["value"]}"')
            if el["checked"] not in (None, False, "false"):
                parts.append(f"checked={el['checked']}")
            if el["href"]:
                parts.append(f"href={el['href']}")
            if el["disabled"]:
                parts.append("DISABLED")
            if not el["inView"]:
                parts.append("(offscreen)")
            lines.append(" ".join(parts))

        try:
            title = await page.title()
        except Exception:  # noqa: BLE001
            title = ""
        header = f"URL: {page.url}\nTITLE: {title}\nOPEN TABS: {len(self.context.pages)}"
        return (
            f"{header}\n\n--- INTERACTIVE ELEMENTS (use the [id]) ---\n"
            + ("\n".join(lines) or "(none found - try screenshot or wait)")
            + "\n\n" + "\n\n".join(blocks)
        )
