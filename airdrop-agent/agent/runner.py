"""The Claude tool-use loop for one task."""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Awaitable, Callable

import anthropic

from .config import Config
from .tools import TOOLS, ToolExecutor

log = logging.getLogger(__name__)

# $ per million tokens: input, output, 5-min cache write, cache read
PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20),
    "claude-haiku-4-5": (1.0, 5.0, 1.25, 0.10),
}
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
EFFORT_MODELS_EXCLUDED = {"claude-haiku-4-5"}


class TaskRunner:
    def __init__(self, cfg: Config, executor: ToolExecutor, system_prompt: str,
                 notify: Callable[[str], Awaitable[None]]):
        self.cfg = cfg
        self.executor = executor
        self.system_prompt = system_prompt
        self.notify = notify
        self.client = anthropic.AsyncAnthropic(max_retries=5)
        self.step = 0
        self.last_action = ""
        self.usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}

    def cost_usd(self) -> float:
        p = PRICES.get(self.cfg.model)
        if not p:
            return 0.0
        u = self.usage
        return (u["input"] * p[0] + u["output"] * p[1] + u["cache_write"] * p[2] + u["cache_read"] * p[3]) / 1e6

    def _request_kwargs(self) -> dict:
        kw: dict = {
            "model": self.cfg.model,
            "max_tokens": 16000,
            # frozen system prompt + fixed tool order -> cacheable prefix
            "system": [{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
            "tools": TOOLS,
            "cache_control": {"type": "ephemeral"},  # also cache the growing conversation
            # server-side context editing drops old snapshots/screenshots; the
            # transcript we send stays append-only
            "context_management": {"edits": [{
                "type": "clear_tool_uses_20250919",
                "trigger": {"type": "input_tokens", "value": 60000},
                "keep": {"type": "tool_uses", "value": 4},
                "exclude_tools": ["ask_human", "finish_task"],
            }]},
        }
        betas = ["context-management-2025-06-27"]
        if self.cfg.model not in EFFORT_MODELS_EXCLUDED:
            kw["output_config"] = {"effort": self.cfg.effort}
        if self.cfg.model in FALLBACK_MODELS:
            # if a safety classifier declines a turn, the API retries on a fallback model
            betas.append("server-side-fallback-2026-07-01")
            kw["fallbacks"] = "default"
        kw["betas"] = betas
        return kw

    async def run(self, task_id: str, task_text: str) -> dict:
        log_path = self.cfg.data_dir / "logs" / f"{task_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        today = dt.date.today().isoformat()
        messages: list[dict] = [{"role": "user", "content": f"Today is {today}.\n\nTASK:\n{task_text}"}]
        kwargs = self._request_kwargs()
        nudged = False

        for self.step in range(1, self.cfg.max_steps + 1):
            resp = await self.client.beta.messages.create(messages=messages, **kwargs)
            u = resp.usage
            self.usage["input"] += u.input_tokens or 0
            self.usage["output"] += u.output_tokens or 0
            self.usage["cache_write"] += u.cache_creation_input_tokens or 0
            self.usage["cache_read"] += u.cache_read_input_tokens or 0

            if resp.stop_reason == "refusal":
                return {"status": "failed", "summary": "The model declined this task (safety refusal)."}

            messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            said = " ".join(b.text for b in resp.content if b.type == "text").strip()

            if not tool_uses:
                if resp.stop_reason == "pause_turn":
                    continue
                if nudged:
                    return {"status": "partial", "summary": said or "Agent stopped without a summary."}
                nudged = True
                messages.append({"role": "user", "content": "If the task is done or stuck, call finish_task with a summary. Otherwise continue with the next tool call."})
                continue

            results = []
            finished = None
            for tu in tool_uses:
                self.last_action = f"{tu.name} {json.dumps(tu.input)[:120]}"
                outcome = await self.executor.run(tu.name, dict(tu.input))
                _write_log(log_path, {"step": self.step, "tool": tu.name, "input": tu.input,
                                      "error": outcome.is_error,
                                      "result": next((c.get("text", "")[:500] for c in outcome.content if c["type"] == "text"), "<image>")})
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": outcome.content,
                    **({"is_error": True} if outcome.is_error else {}),
                })
                if outcome.finished:
                    finished = outcome.finished
            # all results go back in ONE user message
            messages.append({"role": "user", "content": results})
            if finished:
                return finished

        return {"status": "failed", "summary": f"Hit the step limit ({self.cfg.max_steps}). Last action: {self.last_action}"}


def _write_log(path: Path, entry: dict) -> None:
    entry["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with path.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
