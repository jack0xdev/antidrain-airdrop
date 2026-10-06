import asyncio, os, sys, tempfile
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.update(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_OWNER_ID="42", DATA_DIR=tempfile.mkdtemp(),
                  BURNER_PRIVATE_KEY="0x" + "22"*32, APPROVAL_TIMEOUT_SECONDS="2")
from agent.config import Config
from agent.main import TelegramUI, Orchestrator

sent = []
class Msg:
    def __init__(self, text, markup): self.text_html, self.reply_markup = text, markup
    async def edit_text(self, t, **k): sent.append(("edit", t))
class Bot:
    async def send_message(self, chat, text, **k): sent.append(("msg", chat, text, k.get("reply_markup"))); return Msg(text, k.get("reply_markup"))
    async def send_photo(self, chat, photo, caption=None, **k): sent.append(("photo", chat, caption)); return Msg(caption, None)

def cb(data, user=42):
    async def answer(*a): pass
    async def edit_message_text(t, **k): sent.append(("edited", t))
    async def edit_message_reply_markup(m): pass
    q = NS(data=data, answer=answer, edit_message_text=edit_message_text, edit_message_reply_markup=edit_message_reply_markup,
           message=NS(text_html="orig"))
    return NS(callback_query=q, effective_user=NS(id=user))

async def main():
    cfg = Config()
    ui = TelegramUI(cfg, NS(bot=Bot()))
    # approve
    t = asyncio.create_task(ui.approve("tx?"))
    await asyncio.sleep(0.05)
    key = sent[-1][3].inline_keyboard[0][0].callback_data
    assert key.startswith("ap:") and key.endswith(":y")
    await ui.on_callback(cb(key.replace(":y", ":n"), user=999), None)  # stranger ignored
    assert not t.done()
    await ui.on_callback(cb(key), None)
    assert await t is True
    # reject
    t = asyncio.create_task(ui.approve("tx2?")); await asyncio.sleep(0.05)
    key = sent[-1][3].inline_keyboard[0][1].callback_data
    await ui.on_callback(cb(key), None)
    assert await t is False
    # timeout -> False
    assert await ui.approve("slow") is False and sent[-1][0] == "edit"
    # ask by text reply
    t = asyncio.create_task(ui.ask("captcha pls", b"\xff\xd8jpeg")); await asyncio.sleep(0.05)
    assert sent[-1][0] == "photo"
    assert ui.answer_pending_question("solved it")
    assert await t == "solved it"
    assert not ui.answer_pending_question("random text")  # no pending question -> becomes a task
    # ask by Done button
    t = asyncio.create_task(ui.ask("q", None)); await asyncio.sleep(0.05)
    await ui.on_callback(cb("q:done"), None)
    assert "Done" in await t
    # orchestrator wiring builds without network
    o = Orchestrator(cfg)
    assert o.wallet and o.browser.wallet is o.wallet
    print("TELEGRAM UI TESTS PASSED")
asyncio.run(main())
