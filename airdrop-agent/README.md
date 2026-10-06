# Airdrop Agent 🤖

Ei agent ta VPS-e 24/7 chole. Tumi Telegram-e ekta link pathale baki kaj agent nije kore: whitelist/waitlist form fill, wallet connect, X/Discord verify, follow/repost/post, free mint. Kaj shesh hole Telegram-e report pathay.

```
Telegram (tumi)  ──►  Agent (Claude)  ──►  Chromium (tomar X / Discord / Gmail logged in)
      ▲                                        │
      └──── approve / reject buttons  ◄── Burner wallet (policy-guarded)
```

## Ki ki pare

- Link pathale page pore bujhe ki korte hobe, tarpor form fill kore submit kore
- "Verify with X / Discord" OAuth popup handle kore
- Wallet connect kore (MetaMask / Injected / RainbowKit / Web3Modal, shob jaygay **Agent Wallet** hisebe dekhay)
- Email verification code Gmail theke pore niye ashe
- Project-er jonno notun kore humanized answer likhe, tomar `profile.yaml` theke. Nijer theke kono fact banay na
- X post kore (280 char-er moddhe), post-er link form-e boshay
- Free mint kore (website UI diye, UI bhanga thakle sorasori contract call kore)
- `/runall` dile list-er shob task ekta por ekta kore
- Captcha, SMS code ba ajana prosno ashle Telegram-e screenshot shoho tomake jiggesh kore. Tumi VNC-te solve kore **Done** chapo

## Safety: eta age poro ⚠️

Wallet-er niyom gulo **code-e** lekha, AI-er prompt-e na. Tai kono drainer site AI-ke bhuliye egulo bypass korate parbe na:

| Ki | Ki hoy |
|---|---|
| `eth_sign` (blind signing) | Shob shomoy block |
| Permit / Permit2 / Seaport listing / SafeTx signature | Shob shomoy block |
| `approve`, `setApprovalForAll`, `transfer`, `transferFrom`, `multicall`… | Shob shomoy block |
| Prottek transaction | Telegram-e **Approve / Reject** button ashe, 15 min-e uttor na dile auto reject |
| Tx value | `MAX_TX_VALUE_ETH` (default 0.01) ar `DAILY_SPEND_CAP_ETH` (0.05) er beshi hole block |
| Login signature ("Sign in with Ethereum" text) | Auto sign hoy, Telegram-e janiye dey |
| Onno typed-data signature | Tomar approval lage |

Aro kichu niyom:
- **Main wallet KOKHONO diba na.** Notun burner wallet banao, shudhu gas-er taka rakho. Whitelist-e oi burner address-i jabe, mint-o oi wallet-e hobe.
- Password tomake dite hobe na. VNC screen-e tumi nije ekbar login koro, cookie VPS-e save thake.
- Account settings-er page (Google account, X settings) agent kholte pare na.
- Web page-er lekha AI-er kache shudhu "data". "ignore previous instructions" type kono lekha thakle agent sheta follow kore na, report kore.
- **ToS risk:** X ar Discord automation pochondo kore na. Account ban-er risk ache, tai main account-e chalale nijer risk-e chalao. Ekta account-ei use koro. Multi-account / sybil farming-er jonno ei tool na.

## Khoroch

- **VPS:** 2 vCPU / 4 GB RAM (~$5–10/month, Hetzner / Contabo / DigitalOcean)
- **Claude API:** Opus 5.5 diye ekta task-e mote-mote $0.5–2 lage (page boro hole ba step beshi hole beshi). `.env`-e `AGENT_MODEL=claude-sonnet-5-5` dile khoroch prai ordhek. Prottek task-er sheshe Telegram-e approximate cost dekhay.

## Setup (Ubuntu VPS, ~15 minute)

### 1. Docker install
```bash
curl -fsSL https://get.docker.com | sh
```

### 2. Code namao
```bash
git clone https://github.com/jack0xdev/antidrain-airdrop.git
cd antidrain-airdrop
git checkout claude/compassionate-ritchie-as9zq5   # main-e merge hole eta lagbe na
cd airdrop-agent
mkdir -p data && chown 1000:1000 data
cp .env.example .env && chmod 600 .env
```

### 3. Key gulo jogar koro
- **Anthropic API key:** https://console.anthropic.com → API Keys
- **Telegram bot:** Telegram-e `@BotFather` → `/newbot` → token copy koro
- **Tomar Telegram ID:** `@userinfobot`-ke message dao, number ta copy koro
- **Burner wallet:**
  ```bash
  docker compose build
  docker compose run --rm agent python -c "from eth_account import Account; a=Account.create(); print('address:', a.address); print('key:', a.key.hex())"
  ```
  Address-e gas pathao (jemon Base-e 0.002 ETH, Ethereum-e 0.005 ETH).

`.env` file-e boshao: `nano .env`

### 4. Chalu koro
```bash
docker compose up -d --build
docker compose logs -f        # Ctrl+C dile log dekha bondho hoy, agent cholte thake
```
Telegram-e "🤖 Agent online" message ashbe.

### 5. Ekbar nije login koro (X, Discord, Gmail)
VNC port shudhu VPS-er localhost-e khola. Nijer PC theke SSH tunnel diye dhuko:
```bash
ssh -L 6080:localhost:6080 root@YOUR_VPS_IP
```
Browser-e kholo `http://localhost:6080/vnc.html` → VNC password dao.

Telegram-e `/login` pathao → VNC-te Chromium khulbe → X-e login koro → new tab-e `discord.com/login` ar `mail.google.com`-e login koro → Telegram-e `/logindone` pathao.

### 6. Profile thik koro
```bash
nano data/profile.yaml     # telegram, discord, email, builds... (first start-e auto copy hoy)
nano data/tasks.yaml       # tomar WL list (10 ta link already deya)
docker compose restart
```

### 7. Kaj dao
- `/runall` dile `tasks.yaml`-er shob task cholbe
- Ba shudhu link paste koro: `https://ryft.fun/whitelist`
- Ba sadharon bhashay likho: `PaperDAO te apply koro, X post o koro`

## Telegram commands

| Command | Kaj |
|---|---|
| `/run <url> [extra]` | Ekta task queue-te dao (plain message pathaleo hobe) |
| `/runall` | `tasks.yaml`-er shob task |
| `/status` | Ekhon ki korche, koto step, koto khoroch |
| `/queue` · `/clear` | Queue dekho / khali koro |
| `/stop` | Choloman task bondho koro |
| `/screenshot` | Browser-e ekhon ki dekhache |
| `/wallet` | Burner address + balance |
| `/login [url]` · `/logindone` | Nije login korar mode |
| `/results` | Shesh 10 ta result |

Agent jodi tomake kichu jiggesh kore (captcha, code), tahole reply koro ba VNC-te solve kore **Done** chapo.

## Settings (.env)

| Variable | Default | Mane |
|---|---|---|
| `AGENT_MODEL` | `claude-opus-5-5` | `claude-sonnet-5-5` dile shosta |
| `AGENT_EFFORT` | `medium` | `low` / `medium` / `high` |
| `REQUIRE_TX_APPROVAL` | `true` | `false` dile cap-er moddhe tx auto jabe (full auto) |
| `MAX_TX_VALUE_ETH` | `0.01` | Ek tx-e max koto coin |
| `DAILY_SPEND_CAP_ETH` | `0.05` | Din-e max koto |
| `DEFAULT_CHAIN_ID` | `1` | Shuru-te kon chain |
| `RPC_<chainId>` | public RPC | Nijer Alchemy/Infura RPC |
| `EXTRA_CHAINS_JSON` | – | Notun chain add (jemon Robinhood Chain ashle) |

Log ar data `data/` folder-e thake: `results.jsonl`, `logs/<task>.jsonl` (prottek step), `wallet-audit.jsonl` (prottek wallet request).

## Limitation (shot kotha)

- Cloudflare / hCaptcha / Turnstile ashle tomake solve korte hobe. Agent bypass kore na.
- Kichu site-er wallet modal shudhu nirdishto extension chene (jemon shudhu "Phantom"). Shekhane agent fail korle report korbe.
- OpenSea-r UI ghon ghon bodlay. UI diye mint na hole agent sorasori contract-e `contract_write` diye mint korte pare (tomar approval lagbe).
- Ekshathe ektai task chole (ekta browser).

## Code structure

```
agent/
  main.py          Telegram bot + task queue
  runner.py        Claude tool-use loop (prompt caching, context editing, refusal fallback)
  tools.py         agent-er tool (navigate, click, type, ask_human, contract_write…)
  browser.py       Playwright persistent Chromium + popup/iframe handling
  wallet.py        burner wallet + safety policy
  wallet_inject.js page-e window.ethereum + EIP-6963 provider
  prompts.py       system prompt
examples/          profile + tasks template
```
