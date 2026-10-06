import asyncio, json, os, sys, tempfile, threading, http.server, functools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp()
os.environ.update(TELEGRAM_BOT_TOKEN="x", TELEGRAM_OWNER_ID="1", DATA_DIR=tmp, ANTHROPIC_API_KEY="sk-test",
                  BURNER_PRIVATE_KEY="0x" + "22"*32)
SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8766), functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE))
threading.Thread(target=srv.serve_forever, daemon=True).start()
import httpx2, anthropic
from anthropic import DefaultAsyncHttpxClient
from agent.config import Config
from agent.browser import BrowserSession
from agent.tools import ToolExecutor
from agent.runner import TaskRunner
from agent.prompts import SYSTEM_TEMPLATE

requests = []
script = [
    [{"type": "text", "text": "Opening the page."},
     {"type": "tool_use", "id": "tu_1", "name": "navigate", "input": {"url": "http://127.0.0.1:8766/index.html"}}],
    [{"type": "tool_use", "id": "tu_2", "name": "screenshot", "input": {}},
     {"type": "tool_use", "id": "tu_3", "name": "type_text", "input": {"element_id": 6, "text": "@jack", "press_enter": False}}],
    [{"type": "tool_use", "id": "tu_4", "name": "finish_task", "input": {"status": "success", "summary": "Applied. Pending: results."}}],
]
def handler(request):
    body = json.loads(request.content)
    requests.append({"body": body, "headers": dict(request.headers), "url": str(request.url)})
    content = script[len(requests) - 1]
    return httpx2.Response(200, json={
        "id": f"msg_{len(requests)}", "type": "message", "role": "assistant", "model": body["model"],
        "content": content, "stop_reason": "tool_use", "stop_sequence": None,
        "usage": {"input_tokens": 1000, "output_tokens": 100, "cache_creation_input_tokens": 500, "cache_read_input_tokens": 2000},
    })

async def main():
    cfg = Config()
    b = BrowserSession(cfg, None)
    await b.start()
    class H:
        async def ask(self, q, i): return "ok"
    notes = []
    async def notify(t): notes.append(t)
    r = TaskRunner(cfg, ToolExecutor(b, None, H()), SYSTEM_TEMPLATE.format(profile="name: Jack"), notify)
    r.client = anthropic.AsyncAnthropic(api_key="sk-test", http_client=DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)))
    res = await r.run("t1", "Apply at http://127.0.0.1:8766/index.html")
    await b.shutdown()
    assert res == {"status": "success", "summary": "Applied. Pending: results."}, res
    assert len(requests) == 3
    req0 = requests[0]
    assert req0["url"].endswith("/v1/messages?beta=true"), req0["url"]
    betas = req0["headers"].get("anthropic-beta", "")
    assert "context-management-2025-06-27" in betas and "server-side-fallback-2026-07-01" in betas, betas
    body = req0["body"]
    assert body["model"] == "claude-opus-5-5" and body["fallbacks"] == "default"
    print("output_config:", body.get("output_config")); assert body["output_config"]["effort"] == "medium"
    assert body["context_management"]["edits"][0]["type"] == "clear_tool_uses_20250919"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"} and body["cache_control"] == {"type": "ephemeral"}
    assert all(t["strict"] and t["input_schema"]["additionalProperties"] is False for t in body["tools"])
    assert "thinking" not in body and "budget_tokens" not in json.dumps(body)
    # append-only: request N's messages are a prefix of request N+1's
    for a, b2 in zip(requests, requests[1:]):
        assert b2["body"]["messages"][: len(a["body"]["messages"])] == a["body"]["messages"], "history was edited"
    m3 = requests[2]["body"]["messages"]
    last_user = m3[-1]
    assert last_user["role"] == "user" and [c["tool_use_id"] for c in last_user["content"]] == ["tu_2", "tu_3"]
    assert last_user["content"][0]["content"][0]["type"] == "image"
    assert 'value="@jack"' in last_user["content"][1]["content"][0]["text"]
    assert "Opened http://127.0.0.1:8766/index.html" in m3[2]["content"][0]["content"][0]["text"]
    assert abs(r.cost_usd() - 3 * (1000*4 + 100*20 + 500*5 + 2000*0.2) / 1e6) < 1e-9
    print("RUNNER TEST PASSED; cost", round(r.cost_usd(), 4), "steps", r.step)
asyncio.run(main())
srv.shutdown()
