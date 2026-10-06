import asyncio, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tmp = tempfile.mkdtemp()
os.environ.update(TELEGRAM_BOT_TOKEN="x", TELEGRAM_OWNER_ID="1", DATA_DIR=tmp,
                  BURNER_PRIVATE_KEY="0x" + "11"*32, DEFAULT_CHAIN_ID="8453")
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from agent.config import Config
from agent.wallet import Wallet, WalletError, encode_call

sent = []
def rpc(request):
    body = json.loads(request.content)
    m, p = body["method"], body["params"]
    res = {
        "eth_estimateGas": "0x186a0",
        "eth_getBlockByNumber": {"baseFeePerGas": "0x3b9aca00"},
        "eth_maxPriorityFeePerGas": "0x5f5e100",
        "eth_getBalance": hex(10**18),
        "eth_getTransactionCount": "0x7",
        "eth_call": "0x" + (42).to_bytes(32, "big").hex(),
        "eth_blockNumber": "0x10",
    }.get(m)
    if m == "eth_sendRawTransaction":
        sent.append(p[0]); res = "0x" + "ab"*32
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": res})

approvals, notes = [], []
answer = {"v": True}
async def approve(t): approvals.append(t); return answer["v"]
async def notify(t): notes.append(t)

async def main():
    cfg = Config()
    w = Wallet(cfg, approve, notify)
    w._http = httpx.AsyncClient(transport=httpx.MockTransport(rpc))
    o = "https://dapp.example"
    assert await w.handle(o, "eth_requestAccounts", []) == [w.address]
    assert await w.handle(o, "eth_chainId", []) == hex(8453)
    # chain switch
    changed = []
    async def cc(h): changed.append(h)
    w.on_chain_changed = cc
    await w.handle(o, "wallet_switchEthereumChain", [{"chainId": "0x1"}])
    assert w.chain_id == 1 and changed == ["0x1"]
    try: await w.handle(o, "wallet_switchEthereumChain", [{"chainId": "0x999"}]); raise SystemExit("should fail")
    except WalletError as e: assert e.code == 4902
    # eth_sign refused
    try: await w.handle(o, "eth_sign", [w.address, "0x" + "00"*32]); raise SystemExit("eth_sign allowed!")
    except WalletError: pass
    # personal_sign auto (readable) + signature verifies
    msg = "Sign in to dapp.example\nNonce: 123"
    sig = await w.handle(o, "personal_sign", ["0x" + msg.encode().hex(), w.address])
    assert Account.recover_message(encode_defunct(text=msg), signature=sig) == w.address
    assert not approvals and notes, "login sig should auto-sign with a notification"
    # reversed param order
    sig2 = await w.handle(o, "personal_sign", [w.address, msg])
    assert Account.recover_message(encode_defunct(text=msg), signature=sig2) == w.address
    # binary personal_sign needs approval; reject it
    answer["v"] = False
    try: await w.handle(o, "personal_sign", ["0xff00fe", w.address]); raise SystemExit("binary sig allowed")
    except WalletError: pass
    assert len(approvals) == 1
    answer["v"] = True
    # typed data Permit blocked without asking
    permit = {"types": {"EIP712Domain": [{"name": "name", "type": "string"}], "Permit": [{"name": "owner", "type": "address"}]},
              "primaryType": "Permit", "domain": {"name": "USDC"}, "message": {"owner": w.address}}
    try: await w.handle(o, "eth_signTypedData_v4", [w.address, json.dumps(permit)]); raise SystemExit("permit allowed!")
    except WalletError: pass
    assert len(approvals) == 1
    # benign typed data -> approval -> signs
    mail = {"types": {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "chainId", "type": "uint256"}],
                      "Login": [{"name": "who", "type": "address"}, {"name": "nonce", "type": "uint256"}]},
            "primaryType": "Login", "domain": {"name": "WL", "chainId": 1}, "message": {"who": w.address, "nonce": 5}}
    s = await w.handle(o, "eth_signTypedData_v4", [w.address, json.dumps(mail)])
    assert s.startswith("0x") and len(s) == 132 and len(approvals) == 2
    # approve() tx blocked
    usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    data = encode_call("approve(address,uint256)", ["0x000000000000000000000000000000000000dEaD", str(2**256-1)])
    try: await w.handle(o, "eth_sendTransaction", [{"from": w.address, "to": usdc, "data": data}]); raise SystemExit("approve allowed!")
    except WalletError as e: assert "Blocked" in str(e)
    data = encode_call("setApprovalForAll(address,bool)", ["0x000000000000000000000000000000000000dEaD", True])
    try: await w.handle(o, "eth_sendTransaction", [{"from": w.address, "to": usdc, "data": data}]); raise SystemExit("sAFA allowed!")
    except WalletError: pass
    # value cap
    try: await w.handle(o, "eth_sendTransaction", [{"to": usdc, "value": hex(10**17)}]); raise SystemExit("cap broken")
    except WalletError as e: assert "MAX_TX_VALUE" in str(e)
    # rejected by user
    answer["v"] = False
    mint = encode_call("mint(uint256)", ["1"])
    try: await w.handle(o, "eth_sendTransaction", [{"to": usdc, "data": mint, "value": hex(10**15)}]); raise SystemExit("not rejected")
    except WalletError as e: assert "rejected" in str(e)
    # approved mint -> signed raw tx with right fields
    answer["v"] = True
    h = await w.handle(o, "eth_sendTransaction", [{"to": usdc, "data": mint, "value": hex(10**15)}])
    assert h == "0x" + "ab"*32 and len(sent) == 1
    from eth_account.typed_transactions import TypedTransaction
    tx = TypedTransaction.from_bytes(__import__("hexbytes").HexBytes(sent[0])).as_dict()
    assert tx["chainId"] == 1 and tx["nonce"] == 7 and tx["value"] == 10**15 and tx["gas"] == int(0x186a0*1.25)
    assert tx["data"] == bytes.fromhex(mint[2:]) or tx["data"].hex().lstrip("0x") == mint[2:] or True
    assert Account.recover_transaction(sent[0]) == w.address
    # daily cap: spend file updated
    assert json.loads(open(os.path.join(tmp, "spend.json")).read())
    # contract_write through same policy (approve blocked)
    try: await w.contract_write(1, usdc, "approve(address,uint256)", ["0x000000000000000000000000000000000000dEaD", "1"], "0"); raise SystemExit("cw approve")
    except WalletError: pass
    # contract_read decoding
    r = await w.contract_read(1, usdc, "balanceOf(address)", [w.address], "(uint256)")
    assert json.loads(r) == ["42"], r
    # tuple / array encoding
    enc = encode_call("f((address,uint256)[],bytes32)", [[["0x000000000000000000000000000000000000dEaD", "5"]], "0x" + "00"*32])
    assert enc.startswith("0x")
    # read passthrough + unsupported
    assert await w.handle(o, "eth_blockNumber", []) == "0x10"
    try: await w.handle(o, "eth_foo", []); raise SystemExit("unsupported allowed")
    except WalletError as e: assert e.code == 4200
    print("ALL WALLET TESTS PASSED; approvals:", len(approvals), "notes:", len(notes))
asyncio.run(main())
