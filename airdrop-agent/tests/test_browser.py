import asyncio, json, os, re, sys, tempfile, threading, http.server, functools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp()
os.environ.update(TELEGRAM_BOT_TOKEN="x", TELEGRAM_OWNER_ID="1", DATA_DIR=tmp,
                  BURNER_PRIVATE_KEY="0x" + "22"*32, DEFAULT_CHAIN_ID="8453")
SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE))
threading.Thread(target=srv.serve_forever, daemon=True).start()

import httpx
from agent.config import Config
from agent.wallet import Wallet
from agent.browser import BrowserSession
from agent.tools import ToolExecutor

def rpc(request):
    b = json.loads(request.content); m = b["method"]
    res = {"eth_estimateGas": "0x5208", "eth_getBlockByNumber": {"baseFeePerGas": "0x10"}, "eth_maxPriorityFeePerGas": "0x1",
           "eth_getBalance": hex(10**18), "eth_getTransactionCount": "0x0", "eth_sendRawTransaction": "0x" + "cd"*32}.get(m)
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": res})

approvals, notes = [], []
async def approve(t): approvals.append(t); return True
async def notify(t): notes.append(t)
class Human:
    async def ask(self, q, img): return "ok"

def find(snap, pattern):
    for line in snap.splitlines():
        if re.search(pattern, line):
            return int(re.match(r"\[(\d+)\]", line).group(1))
    raise AssertionError(f"{pattern} not in snapshot:\n{snap}")

async def main():
    cfg = Config()
    w = Wallet(cfg, approve, notify)
    w._http = httpx.AsyncClient(transport=httpx.MockTransport(rpc))
    b = BrowserSession(cfg, w)
    await b.start()
    ex = ToolExecutor(b, w, Human())
    r = await ex.run("navigate", {"url": "http://127.0.0.1:8765/index.html"})
    snap = r.content[0]["text"]
    assert "[Agent Wallet]" in snap, snap[:300]  # EIP-6963 discovered
    print(snap[:1500]); print("....")
    snap = (await ex.run("click", {"element_id": find(snap, r'button "Connect Wallet"')})).content[0]["text"]
    assert w.address in snap and "0x2105" in snap, "connect failed"
    snap = (await ex.run("click", {"element_id": find(snap, r'button "Sign in"')})).content[0]["text"]
    assert re.search(r"Sign in 0x[0-9a-f]{10}", snap), "sign failed: " + snap[-600:]
    snap = (await ex.run("click", {"element_id": find(snap, r'button "Claim bonus"')})).content[0]["text"]
    assert "refused:4001" in snap, "drain not refused"
    snap = (await ex.run("click", {"element_id": find(snap, r'button "Mint"')})).content[0]["text"]
    assert "minted:0xcdcdcdcd" in snap, "mint failed"
    assert len(approvals) == 1, approvals  # only the mint asked
    snap = (await ex.run("type_text", {"element_id": find(snap, r'placeholder="@handle"'), "text": "@jack", "press_enter": False})).content[0]["text"]
    snap = (await ex.run("type_text", {"element_id": find(snap, r'textarea "Why should'), "text": "builder, not a farmer lol", "press_enter": False})).content[0]["text"]
    snap = (await ex.run("select_option", {"element_id": find(snap, r'select'), "option": "Developer"})).content[0]["text"]
    snap = (await ex.run("click", {"element_id": find(snap, r'checkbox')})).content[0]["text"]
    snap = (await ex.run("type_text", {"element_id": find(snap, r'editable "Post text"'), "text": "gm from the agent 🚀", "press_enter": False})).content[0]["text"]
    assert 'value="gm from the agent' in snap, "contenteditable typing failed"
    snap = (await ex.run("click", {"element_id": find(snap, r'button\[submit\] "Submit application"')})).content[0]["text"]
    assert 'SUBMITTED:{"telegram":"@jack","why":"builder, not a farmer lol","role":"dev","agree":"on"}' in snap, snap
    # iframe element
    snap = (await ex.run("click", {"element_id": find(snap, r'button "Inside frame"')})).content[0]["text"]
    assert "frame clicked" in snap, "iframe click failed"
    # popup flow
    r = await ex.run("click", {"element_id": find(snap, r'a "Verify with X"')})
    snap = r.content[0]["text"]
    assert "new tab/popup opened" in snap and "Authorize app" in snap, snap[:600]
    r = await ex.run("click", {"element_id": find(snap, r'button "Authorize app"')})
    snap = r.content[0]["text"]
    assert "active tab closed" in snap, snap[:600]
    snap = (await ex.run("page_snapshot", {})).content[0]["text"]
    assert "XVERIFIED" in snap, snap
    # blocked url
    r = await ex.run("navigate", {"url": "https://x.com/settings/password"})
    assert "Refused" in r.content[0]["text"]
    # screenshot
    r = await ex.run("screenshot", {})
    assert r.content[0]["type"] == "image" and len(r.content[0]["source"]["data"]) > 1000
    # chain switch propagates to page
    await w.handle("test", "wallet_switchEthereumChain", [{"chainId": "0x1"}])
    ch = await b.page.evaluate("window.ethereum.chainId")
    assert ch == "0x1", ch
    # bad id
    r = await ex.run("click", {"element_id": 99999})
    assert r.is_error
    await b.shutdown()
    print("ALL BROWSER TESTS PASSED. approvals:", len(approvals), "notes:", [n[:40] for n in notes])
asyncio.run(main())
srv.shutdown()
