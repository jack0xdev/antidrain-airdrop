"""Entry point: Telegram control bot + task worker.

Telegram commands (only your TELEGRAM_OWNER_ID can use the bot):
  /run <url or instructions>  queue one task (plain text messages work too)
  /runall                     queue every task in tasks.yaml
  /queue  /status  /stop  /clear
  /screenshot                 what the browser shows right now
  /wallet                     burner address + balances
  /login [url]  /logindone    log in to X / Discord / Gmail yourself via VNC
  /results                    last results
"""
from __future__ import annotations

import asyncio
import datetime as dt
import html
import itertools
import json
import logging
import uuid
from dataclasses import dataclass, field

import yaml
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .browser import BrowserSession
from .config import Config
from .prompts import SYSTEM_TEMPLATE
from .runner import TaskRunner
from .tools import ToolExecutor
from .wallet import Wallet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("agent")

TG_LIMIT = 3900


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


@dataclass
class Task:
    title: str
    text: str
    id: str = field(default_factory=lambda: dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4])


class TelegramUI:
    """Approvals, questions and notifications over Telegram."""

    def __init__(self, cfg: Config, app: Application):
        self.cfg = cfg
        self.app = app
        self.chat_id = cfg.telegram_owner_id
        self._approvals: dict[str, asyncio.Future] = {}
        self._question: asyncio.Future | None = None
        self._ids = itertools.count(1)

    async def notify(self, text: str) -> None:
        try:
            await self.app.bot.send_message(self.chat_id, text[:TG_LIMIT], parse_mode="HTML", disable_web_page_preview=True)
        except Exception:  # noqa: BLE001  (bad HTML from a page shouldn't kill a task)
            await self.app.bot.send_message(self.chat_id, text[:TG_LIMIT], disable_web_page_preview=True)

    async def approve(self, text: str) -> bool:
        key = str(next(self._ids))
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._approvals[key] = fut
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"ap:{key}:y"),
            InlineKeyboardButton("❌ Reject", callback_data=f"ap:{key}:n"),
        ]])
        msg = await self.app.bot.send_message(self.chat_id, text[:TG_LIMIT], parse_mode="HTML",
                                              reply_markup=kb, disable_web_page_preview=True)
        try:
            return await asyncio.wait_for(fut, timeout=self.cfg.approval_timeout_s)
        except asyncio.TimeoutError:
            await msg.edit_text(text[:TG_LIMIT] + "\n\n⏱ <i>timed out → rejected</i>", parse_mode="HTML")
            return False
        finally:
            self._approvals.pop(key, None)

    async def ask(self, question: str, image: bytes | None) -> str:
        loop = asyncio.get_running_loop()
        self._question = loop.create_future()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done (solved on VNC)", callback_data="q:done")]])
        body = f"🙋 <b>Agent needs you</b>\n{esc(question)}\n\n<i>Reply with a message, or tap Done.</i>"
        if image:
            await self.app.bot.send_photo(self.chat_id, photo=image, caption=body[:1000], parse_mode="HTML", reply_markup=kb)
        else:
            await self.app.bot.send_message(self.chat_id, body[:TG_LIMIT], parse_mode="HTML", reply_markup=kb)
        try:
            return await asyncio.wait_for(self._question, timeout=60 * 30)
        except asyncio.TimeoutError:
            return "(no reply within 30 minutes - skip this step or finish the task as partial)"
        finally:
            self._question = None

    # --- handlers -----------------------------------------------------------
    async def on_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        if not update.effective_user or update.effective_user.id != self.cfg.telegram_owner_id:
            await q.answer("Not yours.")
            return
        await q.answer()
        data = q.data or ""
        if data.startswith("ap:"):
            _, key, ans = data.split(":")
            fut = self._approvals.get(key)
            if fut and not fut.done():
                fut.set_result(ans == "y")
                verdict = "✅ approved" if ans == "y" else "❌ rejected"
                await q.edit_message_text((q.message.text_html or "")[:TG_LIMIT] + f"\n\n<b>{verdict}</b>", parse_mode="HTML")
        elif data == "q:done":
            if self._question and not self._question.done():
                self._question.set_result("Done - I handled it on the VNC screen. Re-check the page.")
                await q.edit_message_reply_markup(None)

    def answer_pending_question(self, text: str) -> bool:
        if self._question and not self._question.done():
            self._question.set_result(text)
            return True
        return False


class Orchestrator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.app = Application.builder().token(cfg.telegram_token).build()
        self.ui = TelegramUI(cfg, self.app)
        self.wallet = Wallet(cfg, self.ui.approve, self.ui.notify) if cfg.private_key else None
        self.browser = BrowserSession(cfg, self.wallet)
        profile = cfg.profile_file.read_text() if cfg.profile_file.exists() else "(no profile.yaml found)"
        self.system_prompt = SYSTEM_TEMPLATE.format(profile=profile)
        self.queue: asyncio.Queue[Task] = asyncio.Queue()
        self.current: Task | None = None
        self.current_runner: TaskRunner | None = None
        self.current_job: asyncio.Task | None = None

    # --- worker ---------------------------------------------------------------
    async def worker(self) -> None:
        while True:
            task = await self.queue.get()
            if self.browser.in_login_mode:
                await self.ui.notify("⏸ Finish /logindone first; task stays queued.")
                await self.queue.put(task)
                await asyncio.sleep(30)
                continue
            self.current = task
            await self.browser.ensure_alive()
            executor = ToolExecutor(self.browser, self.wallet, self.ui, progress=None)
            runner = TaskRunner(self.cfg, executor, self.system_prompt, self.ui.notify)
            self.current_runner = runner
            await self.ui.notify(f"▶️ <b>Starting:</b> {esc(task.title)}")
            self.current_job = asyncio.create_task(runner.run(task.id, task.text))
            try:
                result = await self.current_job
            except asyncio.CancelledError:
                result = {"status": "failed", "summary": "Stopped by you (/stop)."}
            except Exception as e:  # noqa: BLE001
                log.exception("task crashed")
                result = {"status": "failed", "summary": f"Crashed: {type(e).__name__}: {e}"}
            icon = {"success": "✅", "partial": "🟡"}.get(result["status"], "❌")
            await self.ui.notify(
                f"{icon} <b>{esc(task.title)}</b> - {result['status']}\n\n{esc(result['summary'])}\n\n"
                f"<i>{runner.step} steps · ~${runner.cost_usd():.2f}</i>"
            )
            with (self.cfg.data_dir / "results.jsonl").open("a") as f:
                f.write(json.dumps({"id": task.id, "title": task.title, **result,
                                    "steps": runner.step, "cost_usd": round(runner.cost_usd(), 3),
                                    "ts": dt.datetime.now().isoformat()}) + "\n")
            self.current = self.current_runner = self.current_job = None

    # --- commands ---------------------------------------------------------------
    async def enqueue(self, title: str, text: str) -> None:
        await self.queue.put(Task(title=title[:80], text=text))

    async def cmd_help(self, update: Update, _) -> None:
        await update.message.reply_text(__doc__)

    async def cmd_run(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = " ".join(ctx.args).strip()
        if not text:
            await update.message.reply_text("Usage: /run <url> [extra instructions]")
            return
        await self.enqueue(text, f"{text}\n\nDo whatever this link needs (apply / join waitlist / whitelist / mint if free) using my profile.")
        await update.message.reply_text(f"Queued ({self.queue.qsize()} waiting).")

    async def cmd_runall(self, update: Update, _) -> None:
        if not self.cfg.tasks_file.exists():
            await update.message.reply_text(f"No tasks file at {self.cfg.tasks_file}")
            return
        spec = yaml.safe_load(self.cfg.tasks_file.read_text()) or {}
        defaults = spec.get("defaults", "")
        n = 0
        for t in spec.get("tasks", []):
            if t.get("enabled", True) is False:
                continue
            body = f"{t.get('name', '')}\nURL: {t['url']}\n\n{t.get('notes', '')}\n\nGeneral instructions:\n{defaults}"
            await self.enqueue(t.get("name") or t["url"], body)
            n += 1
        await update.message.reply_text(f"Queued {n} tasks.")

    async def cmd_queue(self, update: Update, _) -> None:
        items = list(self.queue._queue)  # noqa: SLF001 - read-only peek
        lines = [f"{i + 1}. {t.title}" for i, t in enumerate(items)] or ["(empty)"]
        now = f"Running: {self.current.title}\n\n" if self.current else ""
        await update.message.reply_text(now + "Queue:\n" + "\n".join(lines))

    async def cmd_status(self, update: Update, _) -> None:
        if not self.current or not self.current_runner:
            await update.message.reply_text(f"Idle. {self.queue.qsize()} queued.")
            return
        r = self.current_runner
        await update.message.reply_text(
            f"Running: {self.current.title}\nStep {r.step}/{self.cfg.max_steps}\nLast: {r.last_action}\nCost so far: ~${r.cost_usd():.2f}"
        )

    async def cmd_stop(self, update: Update, _) -> None:
        if self.current_job:
            self.current_job.cancel()
            await update.message.reply_text("Stopping current task…")
        else:
            await update.message.reply_text("Nothing running.")

    async def cmd_clear(self, update: Update, _) -> None:
        n = 0
        while not self.queue.empty():
            self.queue.get_nowait()
            n += 1
        await update.message.reply_text(f"Removed {n} queued tasks.")

    async def cmd_screenshot(self, update: Update, _) -> None:
        if self.browser.in_login_mode:
            await update.message.reply_text("In login mode - look at the VNC screen.")
            return
        img = await self.browser.screenshot()
        await update.message.reply_photo(photo=img, caption=self.browser.page.url[:200] if self.browser.page else "")

    async def cmd_wallet(self, update: Update, _) -> None:
        if not self.wallet:
            await update.message.reply_text("No wallet configured.")
            return
        await update.message.reply_text(await self.wallet.status())

    async def cmd_login(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if self.current:
            await update.message.reply_text("A task is running - /stop it first.")
            return
        url = ctx.args[0] if ctx.args else "https://x.com/login"
        try:
            await self.browser.start_manual_login(url)
        except RuntimeError as e:
            await update.message.reply_text(f"❌ {e}")
            return
        await update.message.reply_text(
            "🔓 Plain Chromium is open on the VNC screen.\n"
            "Open http://localhost:6080/vnc.html through your SSH tunnel, log in to X, Discord, Gmail "
            "(new tabs are fine), then send /logindone."
        )

    async def cmd_logindone(self, update: Update, _) -> None:
        if not self.browser.in_login_mode:
            await update.message.reply_text("Not in login mode.")
            return
        await self.browser.finish_manual_login()
        await update.message.reply_text("✅ Logins saved. Agent browser is back.")

    async def cmd_results(self, update: Update, _) -> None:
        path = self.cfg.data_dir / "results.jsonl"
        if not path.exists():
            await update.message.reply_text("No results yet.")
            return
        rows = [json.loads(line) for line in path.read_text().splitlines()[-10:]]
        text = "\n\n".join(f"{r['status'].upper()} · {r['title']}\n{r['summary'][:300]}" for r in rows)
        await update.message.reply_text(text[:TG_LIMIT])

    async def on_text(self, update: Update, _) -> None:
        text = (update.message.text or "").strip()
        if self.ui.answer_pending_question(text):
            await update.message.reply_text("👍 passed to the agent")
            return
        await self.enqueue(text, text)
        await update.message.reply_text(f"Queued as a task ({self.queue.qsize()} waiting).")

    # --- main -----------------------------------------------------------------
    async def run(self) -> None:
        self.cfg.data_dir.mkdir(parents=True, exist_ok=True)
        owner = filters.User(user_id=self.cfg.telegram_owner_id)
        for name, fn in [
            ("start", self.cmd_help), ("help", self.cmd_help), ("run", self.cmd_run), ("runall", self.cmd_runall),
            ("queue", self.cmd_queue), ("status", self.cmd_status), ("stop", self.cmd_stop), ("clear", self.cmd_clear),
            ("screenshot", self.cmd_screenshot), ("wallet", self.cmd_wallet), ("login", self.cmd_login),
            ("logindone", self.cmd_logindone), ("results", self.cmd_results),
        ]:
            self.app.add_handler(CommandHandler(name, fn, filters=owner))
        self.app.add_handler(CallbackQueryHandler(self.ui.on_callback))
        self.app.add_handler(MessageHandler(owner & filters.TEXT & ~filters.COMMAND, self.on_text))

        await self.browser.start()
        async with self.app:
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            addr = self.wallet.address if self.wallet else "no wallet"
            await self.ui.notify(f"🤖 Agent online.\nWallet: <code>{addr}</code>\nSend /help for commands.")
            try:
                await self.worker()
            finally:
                await self.app.updater.stop()
                await self.app.stop()
                await self.browser.shutdown()
                if self.wallet:
                    await self.wallet.close()


def main() -> None:
    asyncio.run(Orchestrator(Config()).run())


if __name__ == "__main__":
    main()
