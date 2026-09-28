# PERPETUA: Production Website Build Prompt

> Copy everything below this line into your AI coding agent (Claude Code, Cursor, v0, Lovable, Bolt, etc.). Attach the existing bot source (`bulk-bot-mainnet-vps`) so the agent can reuse its trading engine.

---

## 0. Your role and the rules of this job

You are a senior full-stack engineer, security engineer and product designer. You will build **Perpetua**, a production-grade web platform where users connect their Solana wallet, authorize a trade-only agent key for their **BULK** (bulk.trade) perpetuals account, and let an automated engine generate trading volume with their own USDC. Later versions add Hyperliquid, Lighter and Arcus. Version 1 ships **BULK only**.

You are not starting from zero. A working Python trading engine already exists (the `bulk-bot-mainnet-vps` source). It is controlled today through a Telegram bot. Your job is to build a professional website and web control plane on top of that engine, raise its security to production level, and ship a full documentation site.

Work rules:

1. Read the whole existing source before writing any code. Write a short summary of how `bulkbot/` and `tgbot/` work and confirm it back before building.
2. Reuse the `bulkbot/` trading core (signing, REST, WebSocket, strategies, risk, trader, market hub). Do not rewrite trading logic unless a test proves a bug.
3. Never invent BULK API endpoints, fields or message formats. Take them from the existing code, the official `bulk-keychain` library and BULK's official docs. If something is unknown, stop and list it as an open question.
4. Every security rule in Section 3 is a hard requirement. If a feature cannot be built without breaking one, do not build it. Report the conflict.
5. Ship in the phases from Section 22. Each phase must pass its acceptance criteria before the next starts.
6. Write tests with every feature. No phase is done while tests fail.

---

## 1. Product summary

**Name:** Perpetua
**Tagline:** Volume, Perpetually.
**Domain:** perpetua.fi (app at `app.perpetua.fi`, docs at `docs.perpetua.fi`, status at `status.perpetua.fi`)
**Social handle:** @perpetua_fi

**What it does:** Perpetua is an automated perp volume service. A user:

1. Connects a Solana wallet (Phantom, Solflare, Backpack) and signs in with a signed message.
2. Deposits USDC into their own BULK account on bulk.trade. Perpetua never holds user funds.
3. Authorizes a Perpetua-generated **agent key** on BULK. That key can place and cancel orders for the user's account but can **never withdraw or transfer** funds.
4. Picks a strategy mode, pace, coin, leverage, entry size, take-profit target and max-loss limit.
5. Presses Start. The engine trades on BULK against real external liquidity and builds volume.
6. Watches volume, fills, fees, PnL, open position and alerts live on a dashboard. Can Stop at any time. Stop cancels all orders and closes the open position at market.
7. Can revoke the agent key at any time, from Perpetua or directly on BULK.

**Who it is for:** Traders and airdrop farmers who want steady, real trading activity on new perp DEXs without watching charts all day.

**What it is not:** It is not a custodial fund, not a yield product, and it does not promise profit or airdrop rewards. Copy on the site must never claim guaranteed returns, guaranteed points or guaranteed airdrops.

---

## 2. What the existing bot does (reuse this)

Map every current Telegram feature to a web feature. The engine behavior must stay the same.

**Exchange connection (`bulkbot/`)**
- Mainnet REST `https://mainnet-api1.bulk.trade/api/v1` and WebSocket `wss://mainnet-ws1.bulk.trade`. Testnet endpoints live in `bulkbot/config.py`.
- Public endpoints: `GET /exchangeInfo`, `GET /klines`, `POST /account` (fullAccount: margin, positions, open orders).
- Signed endpoint: `POST /order`, Ed25519 signatures via `bulk-keychain`, `high_frequency` nonces. Duplicate replays are rejected by the engine (`rejectedDuplicate`), so retrying a signed submit is safe.
- Agent mode: an agent key signs orders for the owner account (`prepare_order` + `sign_prepared`). The owner key registers the agent once (`agent_wallet_tx`).
- Leverage is set per symbol through `updateUserSettings`, signed by the agent for the owner account.

**Strategy modes (`bulkbot/strategy.py`, `trend.py`, `sweep.py`)**
- **Sweep** (default): liquidity-sweep reversal. Waits for price to pierce a swing high or low by a set ATR amount, then close back across it. Enters at market, stop beyond the sweep wick, fixed dollar take-profit, time stop.
- **Trend**: human-like trend trading. Multi-EMA bias (20/50/100/200) across 1m/5m/15m, order-block, fair-value-gap and market-structure-shift entries, randomized size and hold time.
- **Quote**: post-only (ALO) maker quotes on both sides of the book with inventory skew. Ported from Hummingbot's Pure Market Making (ping-pong, order refresh, filled-order delay, order optimization).
- **Churn**: alternating buy and sell market orders on a timer. Guaranteed volume but pays taker fee on every leg.

**Pace presets:** Normal, Faster, Aggressive. These control hold time, cooldown, signal delay, confluence count, SL/TP distance and size multiplier (`PACE_PRESETS` in `bulkbot/config.py`).

**User settings (from `tgbot/handlers.py`)**
- Coin: any tradable symbol from `exchangeInfo` (BTC-USD, ETH-USD, SOL-USD, ...).
- Leverage: 2x, 3x, 5x, 7x (default), 10x, 15x, 20x, 40x. Capped at each coin's maximum.
- Entry size: 10%, 25%, 50% (default), 75%, 100% of balance x leverage.
- Take-profit per trade: $0.25, $0.5, $0.75 (default), $1, $1.5, $2, or Trailing.
- Max loss: 5%, 10% (default), 15%, 20%, 30% of balance. Breach stops the engine.
- Minimum balance to start: $10 (configurable).

**Risk controls (`bulkbot/risk.py`)**
- Daily loss kill switch (cancel all and halt), minimum available balance floor, stale-feed timeout (pull quotes if market data goes silent), consecutive-error kill switch, cancel on shutdown, lost-submit cooldown, periodic REST reconciliation.
- Self-trades inside the same account tree are skipped by BULK and do not count as volume. All volume comes from external order flow. Keep it that way.

**Scale (`tgbot/manager.py`)**
- One shared market feed and candle cache per symbol (`MarketHub`). Each running user costs one account WebSocket plus light REST polling. Designed for 500 concurrent users on one host.
- Supervised engine restarts (max 5 crashes in 15 minutes), auto-resume after a server restart, heartbeat file for health checks.

**Alerts and stats**
- Trade opened card (side, size, entry, SL, TP), trade closed card (exit, PnL), take profit, stop loss, trailing, kill switch, stale feed, orphan position. Hourly summaries. Per-fill messages are not pushed.
- Stats per user: total volume, maker volume, taker volume, fills, maker fills, taker fills, fees paid.

**Languages:** Bangla (default), English, Hindi. Market terms (BTC-USD, SL, TP, ATR) stay in English in every language.

**Admin:** totals, ban and unban, broadcast, audit log.

---

## 3. Security requirements (non-negotiable)

The project name started as "antidrain". The whole platform must be built so that a compromise of Perpetua's servers can never lead to user funds leaving user accounts. Treat every rule below as a failing test if broken.

### 3.1 Private keys and wallet signing

1. **Never ask for, accept, store, log or transmit a user's wallet private key or seed phrase.** The current Telegram flow asks users to paste their wallet secret so the bot can register the agent. The website must **not** copy this. Owner signatures come only from the user's own wallet through the wallet adapter.
2. Agent registration is signed in the browser wallet. Build the `agentWallet` preimage server-side exactly as `bulk-keychain`'s `sign_agent_wallet` does. Add a test that proves your bytes match `bulk-keychain` byte-for-byte, like the existing `user_settings_preimage` test. The frontend asks the wallet to sign those bytes with `signMessage`, then the backend submits the signed envelope to `POST /order`.
3. Before building (2), verify against BULK's official docs and a testnet run that BULK accepts a raw Ed25519 `signMessage` signature for agent registration, and that Phantom, Solflare and Backpack will sign that binary payload. If any wallet refuses, show that wallet as unsupported for onboarding and offer the official bulk.trade flow for registering an agent, if BULK provides one. **Never fall back to asking for a secret key.**
4. Never request Solana token `Approve`, `SetAuthority`, `CloseAccount` or any delegate permission. Never ask the user to sign a transaction that moves tokens to a Perpetua address, except an optional billing transfer (Section 13) that shows the exact amount and recipient.
5. Every message the user signs is human-readable where the format allows. Sign-in messages follow Sign-In With Solana (SIWS): domain, address, statement, URI, version, chain, nonce, issued-at, expiration. The server rejects any signature whose domain is not exactly `app.perpetua.fi`.

### 3.2 Agent key custody

1. Agent keypairs are generated inside an isolated **Signer Service**, never in the web app or the browser.
2. Agent secrets are stored with envelope encryption: a random 256-bit data key per user encrypts the secret (AES-256-GCM or XSalsa20-Poly1305), and that data key is wrapped by a cloud KMS or HSM key (AWS KMS, GCP KMS or HashiCorp Vault Transit). The KMS key can be used only by the Signer Service's identity.
3. Plaintext agent secrets exist only in Signer Service memory. Never write them to disk, logs, crash dumps, analytics or error trackers.
4. **Replace the master PIN.** The Telegram build lets a master PIN decrypt any user's agent secret, and on Linux stores that PIN as a plain file. The website must have no master key that a person can type or read. Admins can stop engines, but no admin, database dump or backup can recover an agent secret without the KMS.
5. The Signer Service enforces a **signing policy** before it signs anything. It only signs `order`, `cancel`, `cancel_all` and `updateUserSettings`. It rejects any other action type. For orders it checks: symbol is on the allow-list, notional is within the user's configured cap plus a small buffer, leverage is within the user's setting and the platform cap, and limit price is within a price band (default ±2%) of BULK's mark price. The price band stops a stolen agent key from being used to dump a user's balance into an attacker's resting orders.
6. The Signer Service runs on a private network with no public ingress. The engine calls it over mTLS. It keeps its own append-only signing log (user, action type, symbol, size, price, decision).
7. Users can revoke. The Security page has a "Revoke agent" button that builds the `delete=true` agent transaction for the user to sign in their wallet, and a link to revoke on bulk.trade directly. After revocation, the agent secret is destroyed and the data key is scheduled for deletion.

### 3.3 Web application security

- HTTPS only, HSTS with preload, TLS 1.2+.
- Strict Content-Security-Policy with nonces. No inline scripts, no `unsafe-eval`, `frame-ancestors 'none'`, `connect-src` limited to Perpetua's API, BULK's public API and the wallet adapters' required endpoints.
- No third-party scripts on `app.perpetua.fi` (no chat widgets, no tag managers, no analytics beacons). Privacy-friendly, self-hosted analytics are allowed on the marketing site only.
- Subresource Integrity on any static asset loaded from a CDN.
- Session: server-side sessions in Redis, cookie `__Host-perpetua_session`, `HttpOnly`, `Secure`, `SameSite=Strict`, 12-hour absolute expiry, 30-minute idle expiry, rotated on sign-in.
- CSRF protection on every state-changing request (double-submit token plus SameSite).
- **Step-up signing** for sensitive actions: Start, raising leverage above 10x, raising max loss above 20%, registering or revoking an agent, deleting the account. The user signs a fresh human-readable action message (for example `Perpetua: start engine BTC-USD, 7x, entry 50%, max loss 10%. Nonce ...`). This replaces the Telegram PIN.
- Rate limits per IP and per wallet (Redis sliding window): sign-in 10/min, settings 30/min, start/stop 10/min. Lock step-up for 15 minutes after 5 failed signatures, matching the Telegram PIN lockout.
- Input validation with strict schemas (Zod on the frontend, Pydantic on the backend). Reject unknown fields.
- Clickjacking, MIME sniffing and referrer headers: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` with everything disabled that is not used.
- Output encoding everywhere. Never render user-provided HTML. Admin broadcast messages are plain text plus a small Markdown subset rendered by a sanitizer.
- Error responses never leak stack traces, SQL or internal hostnames.

### 3.4 Infrastructure and operations

- Everything as code (Terraform or Pulumi). Separate `staging` and `production` accounts or projects.
- Private subnets for the engine, Signer Service, database and Redis. Only the load balancer or edge is public.
- WAF and DDoS protection at the edge (Cloudflare or equivalent). Bot protection on sign-in.
- Secrets in a secrets manager, never in `.env` files committed to git, never in Docker images.
- Least-privilege IAM. The web API cannot call KMS. Only the Signer Service can.
- Database encrypted at rest, TLS in transit, automated backups with point-in-time recovery, restore tested monthly. Backups never contain plaintext secrets.
- Admin access through SSO with hardware-key or passkey MFA, from an IP allow-list or zero-trust proxy. No shared accounts.
- Domain security: registrar lock, DNSSEC, CAA records, SPF/DKIM/DMARC on the email domain, monitoring for look-alike phishing domains.
- `/.well-known/security.txt` with a contact and a public bug bounty policy.

### 3.5 Supply chain

- Lock files committed. Pin exact versions. Dependabot or Renovate with review.
- CI runs `npm audit`/`pnpm audit`, `pip-audit`, Semgrep, Gitleaks and a container scan (Trivy) on every pull request. High or critical findings fail the build.
- Only well-known wallet adapter packages from their official publishers. Verify package names to avoid typo-squats.
- Reproducible Docker builds from pinned base image digests. Sign images (cosign) and verify signatures at deploy.
- Protected `main` branch, required reviews, required checks, signed commits.

### 3.6 Trading safety

- Hard platform caps that users cannot exceed: max leverage per coin (the lower of BULK's max and a platform cap, default 20x; 40x only behind an extra risk acknowledgement), max notional per user, max open position count of 1 for Sweep and Trend modes.
- Global kill switch in the admin panel: stops every engine, cancels all orders, closes positions, and blocks new starts.
- Per-user kill switch triggers exactly as the current bot does, plus the Signer Service price band.
- No strategy may match Perpetua users against each other or trade between accounts the platform controls. No wash trading. Engines must respect BULK's Terms of Service.
- Graceful shutdown: on deploy or restart, engines cancel orders and close positions inside a 45-second grace period, then auto-resume. Log every orphaned order or position and alert the user.

---

## 4. Tech stack

**Frontend**
- Next.js 15 (App Router) with TypeScript in strict mode.
- Tailwind CSS plus shadcn/ui components, restyled to the Perpetua theme.
- `@solana/wallet-adapter-react` with Phantom, Solflare and Backpack adapters.
- TanStack Query for server state, Zustand for small UI state.
- Recharts or Lightweight Charts (TradingView open-source) for volume and price charts.
- next-intl for Bangla, English and Hindi.
- Framer Motion for small, calm animations only.

**Backend API**
- Python 3.12 with FastAPI, because the engine is already Python and `bulk-keychain` is a Python library.
- Pydantic v2 schemas, SQLAlchemy 2 with Alembic migrations.
- PostgreSQL 16 replaces SQLite. Redis 7 for sessions, rate limits, pub/sub and live updates.
- Server-Sent Events or WebSocket for live dashboard updates.

**Engine Service**
- The existing `bulkbot` core, driven by a new `EngineManager` adapted from `tgbot/manager.py`. Same shared `MarketHub`, same supervision and auto-resume. Reads settings from PostgreSQL. Publishes events to Redis instead of Telegram.

**Signer Service**
- A small, separate Python service that holds the only KMS permission, wraps `bulk-keychain`, and enforces the signing policy from 3.2.

**Notification Service**
- Keeps the existing aiogram Telegram bot, but only as an alert channel. Users link Telegram from the website with a one-time code. The Telegram bot no longer accepts secrets or starts engines.
- Optional email alerts through a transactional provider.

**Docs:** Nextra or Mintlify at `docs.perpetua.fi`.
**Status page:** a hosted status page at `status.perpetua.fi`.
**Observability:** OpenTelemetry, Prometheus, Grafana, Loki, Sentry (with secret scrubbing).
**Deploy:** Docker on a managed container platform (AWS ECS/Fargate, Fly.io or Kubernetes). The web frontend can deploy to Vercel only if CSP and headers are fully controlled.

---

## 5. System architecture

```
Browser (Next.js, wallet adapter)
   │  HTTPS, session cookie, CSRF token
   ▼
Edge (Cloudflare: WAF, DDoS, bot protection)
   ▼
API Service (FastAPI) ──────► PostgreSQL
   │    │                      ▲
   │    └──► Redis (sessions, rate limits, pub/sub)
   │                           ▲
   ▼                           │
Engine Service (bulkbot + EngineManager) ──► BULK REST / WS
   │  mTLS, private network
   ▼
Signer Service (KMS, policy, bulk-keychain) ──► KMS / HSM

Notification Service ◄── Redis events ──► Telegram / email
Admin Panel (separate origin, SSO + MFA) ──► API Service (admin routes)
```

Rules:
- The API never touches agent secrets. It asks the Engine Service to start or stop.
- The Engine Service never touches KMS. It sends unsigned order items to the Signer Service and receives signed envelopes back.
- The Signer Service never talks to the public internet except KMS.

---

## 6. Brand and design system

The look is **classical and premium**: Roman marble, gold leaf, engraved banknote detail, calm and trustworthy. Not neon, not cyberpunk.

**Colors (CSS variables)**
- `--navy-950: #070D1A` (page background, dark mode)
- `--navy-900: #0B1426` (surfaces)
- `--navy-800: #13203A` (cards)
- `--gold-500: #C9A45C` (primary accent, buttons, highlights)
- `--gold-300: #E3C98F` (hover, focus rings)
- `--ivory-100: #F2EBDD` (primary text on dark, background in light mode)
- `--stone-400: #9A9384` (secondary text)
- `--success: #4FA37A`, `--danger: #C8574D`, `--warning: #D9A441`
- Every text and background pair must pass WCAG 2.2 AA contrast.

**Typography**
- Headings: Cinzel (600/700), letter-spacing 0.04em, uppercase for H1 and section labels.
- Body: Cormorant Garamond for marketing prose, Inter for app UI.
- Numbers: Inter or JetBrains Mono with tabular figures, so prices and PnL never jump.

**Ornament**
- Thin gold hairline borders, laurel wreath marks, subtle guilloche patterns as SVG backgrounds at 4-6% opacity, faint marble texture on hero sections only.
- The ⚜️ fleur-de-lis is the small brand mark in favicons and bullets.
- Buttons: solid gold with navy text for primary, gold outline for secondary, 10px radius, 150ms transitions.
- Cards: navy-800 with a 1px gold border at 20% opacity, soft shadow.

**Motion:** fades and slides under 250ms. Respect `prefers-reduced-motion`.

**Modes:** dark by default, light mode available (ivory background, navy text, gold accents).

**Responsive:** mobile first. Breakpoints 360, 768, 1024, 1440. No horizontal scroll. Touch targets at least 44px.

---

## 7. Site map

**Marketing site (`perpetua.fi`)**
- `/` Home
- `/how-it-works`
- `/strategies`
- `/security`
- `/venues` (BULK live; Hyperliquid, Lighter, Arcus coming soon)
- `/pricing`
- `/faq`
- `/blog` (optional MDX)
- `/legal/terms`, `/legal/privacy`, `/legal/risk`, `/legal/cookies`

**App (`app.perpetua.fi`)**
- `/connect` wallet connect and sign-in
- `/onboarding` five-step wizard
- `/dashboard`
- `/engine` strategy and settings
- `/positions` live position and history
- `/activity` trade log and alerts
- `/stats` volume and fee analytics
- `/wallet` account, agent key, balance
- `/security` sessions, agent key, revoke, audit trail
- `/notifications` Telegram and email linking
- `/settings` language, theme, timezone, delete account

**Admin (`admin.perpetua.fi`, separate origin)**
- `/overview`, `/users`, `/engines`, `/risk`, `/broadcast`, `/audit`, `/system`

**Docs (`docs.perpetua.fi`)** described in Section 17.

---

## 8. Marketing pages, section by section

### Home
1. **Hero.** Headline "Volume, Perpetually." Subhead: "Automated perp volume on BULK, running from your own wallet with a trade-only key. Your funds never leave your account." Primary button "Launch App", secondary "Read the Docs". Background: dark marble hall with gold columns (use the brand cover image), soft gold light rays.
2. **Trust bar.** "Non-custodial", "Trade-only agent key", "Revoke anytime", "Real external liquidity". Each with a small gold line icon.
3. **How it works.** Five steps with numbered Roman numerals I to V: Connect wallet, Fund BULK account, Authorize agent, Choose strategy, Start and monitor.
4. **Strategies.** Four cards: Sweep, Trend, Quote, Churn. Each shows what it does, trade style, fee profile (maker or taker) and risk level.
5. **Live platform stats.** Total volume generated, active engines, total fills, uptime. Pulled from a public, cached API endpoint. Never show individual users.
6. **Security.** Short explanation of agent keys, the signing policy, KMS custody and no master key. Link to `/security`.
7. **Venues.** BULK "Live". Hyperliquid, Lighter, Arcus "Coming soon". Use text names and neutral badges, not the venues' logos, unless you have written permission.
8. **FAQ preview.** Six top questions.
9. **Final call to action.** "Start your engine" button.
10. **Footer.** Links to docs, legal, status, X (@perpetua_fi), Telegram channel, security.txt, and a risk line: "Trading perpetual futures with leverage carries a high risk of loss. Perpetua does not guarantee profit, points or airdrops."

### How it works
Diagram of the flow in Section 5, written for non-technical users. Explain what an agent key is, what it can and cannot do, and where the money stays.

### Strategies
One section per mode with plain-language explanation, when to use it, expected fee profile, settings it uses, and a small illustrative chart (clearly labelled as illustrative).

### Security
Full public version of Section 3, written for users. Include "What happens if Perpetua is hacked?" with an honest answer: attackers cannot withdraw funds; the price band and caps limit trading abuse; users can revoke the agent on BULK directly.

### Pricing
Show the model chosen in Section 13. If the beta is free, say so clearly. List BULK's own trading fees as paid to BULK, not Perpetua.

### FAQ
At least 20 questions, including: Do you hold my money? Can you withdraw my funds? What is an agent key? How do I revoke it? What is the minimum deposit? Which wallets work? Why does Stop close my position? Does self-trading count as volume? Will I get an airdrop? What happens during maintenance? Which countries are blocked? How are fees calculated?

---

## 9. Authentication (Sign-In With Solana)

1. User clicks Connect. Wallet adapter modal lists Phantom, Solflare, Backpack.
2. Frontend requests `POST /auth/nonce` with the public key. Server returns a single-use nonce (128-bit random, 5-minute TTL, stored in Redis).
3. Frontend builds the SIWS message and asks the wallet to sign it.
4. `POST /auth/verify` with public key, message and signature. Server checks the Ed25519 signature, the domain, the nonce (and deletes it), issued-at and expiration. On success it creates a session and sets the cookie.
5. `POST /auth/logout` destroys the session. `GET /auth/session` returns the current user.
6. Wallet change or disconnect in the adapter logs the user out.
7. Geoblocking check happens at sign-in (Section 19).

---

## 10. Onboarding wizard (five steps)

A progress bar with Roman numerals. Each step saves state so the user can come back.

**I. Rules.** Show the rules and risk disclosure (same content as the Telegram "Rules agree" step, rewritten for the web). Checkbox plus "I understand" button. Store the version and timestamp of the accepted terms.

**II. Fund BULK.** Show the user's BULK account address (their wallet public key; confirm with BULK docs that the BULK account is the Solana wallet address). Live balance read from `POST /account` every 10 seconds. Button "Deposit on bulk.trade" opens the official BULK app in a new tab (hardcode the verified official URL). Continue unlocks when balance is at least the minimum ($10).

**III. Authorize agent.**
- Backend asks the Signer Service to create an agent keypair for this user and returns only the agent public key.
- Show a clear panel: "Perpetua will be allowed to place and cancel orders on your BULK account. It will never be able to withdraw or transfer your funds. You can revoke it at any time."
- User clicks "Authorize in wallet". The wallet signs the agent registration payload. Backend submits it to BULK and confirms the `agentWallet` status in the response.
- If the account pubkey is already linked to another Perpetua user, refuse (same rule as the Telegram bot).

**IV. Configure.** Mode, pace, coin, leverage, entry %, take-profit, max loss. Show a live preview: "With a $X balance, 7x leverage and 50% entry, each trade is about $Y notional. A 10% max loss stops the engine if your balance drops by $Z." Leverage options above the coin's max are hidden, as in the bot. Warn when a trade would be below the coin's minimum order size.

**V. Start.** Summary card of every setting. "Start engine" requires a step-up signature. On success, redirect to the dashboard.

---

## 11. The app, page by page

### Dashboard
- **Engine status card:** Running, Stopped, Starting, Stopping, Halted (kill switch) or Error. Uptime. Big Start or Stop button. Stop asks for confirmation: "This cancels all open orders and closes your position at market."
- **KPIs (tabular numbers):** Total volume, today's volume, maker volume, taker volume, fills, fees paid, realized PnL, balance.
- **Volume chart:** daily bars for 30 days, with maker and taker stacked.
- **Current position card:** side, size, entry, mark, SL, TP, unrealized PnL, "Close now" button. Same data as the Telegram position card.
- **Recent alerts:** last 10 events (trade opened, closed, TP, SL, kill switch, stale feed).
- Live updates through SSE, reconnect with backoff, and show a "Live" or "Reconnecting" indicator.

### Engine
All settings from Section 2 with the same option values. Each mode has an info tooltip (reuse the text from `mode_info` in i18n). Changes while running are applied on the next trade, or require restart where the engine needs it; say which.

### Positions
Current position plus history table: time, symbol, side, size, entry, exit, PnL, fees, reason (TP, SL, trailing, time stop, manual, kill switch). Filters and CSV export.

### Activity
Full event log with filters. Includes admin actions on the user's account (for example "Engine stopped by admin: global kill switch"). Nothing an admin does to a user's engine is hidden from that user. This replaces the Telegram build's silent admin unlock.

### Stats
Volume by day, week, month. Maker and taker split. Fee total. Average trade size. Fill count. Everything exportable to CSV.

### Wallet
Account public key, agent public key, agent status (active or revoked, registered at), balance, available margin, link to the account on bulk.trade.

### Security
Active sessions (device, IP region, last seen) with "Sign out" per session. Agent key panel with Revoke. Personal audit trail (sign-ins, starts, stops, setting changes, step-up signatures).

### Notifications
Link Telegram (one-time 6-digit code, expires in 10 minutes, sent to the Perpetua bot with `/link CODE`). Choose which alerts go where. Hourly summary on or off. Email alerts optional.

### Settings
Language (Bangla, English, Hindi), theme, timezone, delete account (step-up signature; stops the engine, asks the user to revoke the agent, deletes personal data after the retention period).

---

## 12. Engine integration

- Port `tgbot/engine.py` and `tgbot/manager.py` into an `engine_service` package. Replace the Telegram `tg_id` with a UUID `user_id`. Keep `EngineHandle`, sizing (`balance x leverage x entry%`), `plan()` checks, supervised restarts and the shared `MarketHub`.
- Replace `AlertRouter` with a publisher to a Redis stream `events:{user_id}`. Keep the same event regex and card types. Per-fill events are aggregated, not pushed.
- The engine requests signatures from the Signer Service instead of holding a decrypted agent secret. Add a `RemoteSigner` class with the same interface as `TxSigner` so strategy code does not change. Batch requests where possible, and measure latency so quote mode stays fast.
- Commands from the API arrive on a Redis stream `engine:commands` (start, stop, close_now, apply_settings). Each command carries an idempotency key.
- Engine state lives in PostgreSQL (`engines` table). On boot, the manager resumes every engine with `running = true`, re-checks the balance against the minimum, and stops with a user alert if it is below.
- Stats are persisted every 60 seconds and on stop.
- Reconciliation with BULK every 30 seconds as today.

---

## 13. Billing (optional, feature flag)

Default for launch: free beta. Build the billing module behind a flag so it can be turned on later.

When on:
- Plans billed monthly in USDC on Solana. The user sends a plain SPL transfer of the exact amount to Perpetua's treasury address. The wallet shows the amount and recipient. No `Approve`, no delegate, no recurring pull.
- Backend verifies the transfer on chain (finalized commitment, correct mint, amount, recipient and memo reference) before activating the plan.
- Never auto-charge. Never ask for a signature that can move more than the displayed amount.

---

## 14. Notifications

- Alert types: trade opened, trade closed, take profit, stop loss, trailing exit, kill switch, stale feed, orphan position, engine crashed and restarted, engine stopped (with reason), low balance, agent revoked, admin broadcast.
- Hourly summary: volume, fills, fees and PnL for the last hour.
- Telegram is rate-limited to respect its 30 messages per second limit, with a per-user queue.
- All alert text uses the i18n files ported from `tgbot/i18n.py`.

---

## 15. Admin panel

- Separate origin, SSO with passkey or hardware key MFA, IP allow-list.
- **Roles:** Viewer (read only), Operator (stop engines, broadcast), Owner (global kill switch, bans, platform caps). Every action requires a reason field.
- **Overview:** active engines, users, volume today, errors, event-loop lag, BULK API latency, Signer rejections.
- **Users:** search by wallet, view status and settings, stop engine, ban or unban.
- **Risk:** global kill switch, platform leverage cap, per-coin allow-list, price band width, maintenance mode.
- **Broadcast:** send a message to all users (web banner plus Telegram), with preview and confirmation.
- **Audit:** immutable log of every admin action, exportable.
- **There is no function to view, export or decrypt an agent key.**

---

## 16. Data model (PostgreSQL)

- `users`: id (uuid), wallet_pubkey (unique), lang, theme, timezone, terms_version, terms_accepted_at, banned_at, created_at, deleted_at.
- `sessions` (Redis, not SQL): session id, user id, created, last seen, IP hash, user agent.
- `bulk_accounts`: id, user_id, account_pubkey (unique), network, created_at.
- `agent_keys`: id, user_id, agent_pubkey, kms_key_id, wrapped_dek, ciphertext, nonce, status (pending, active, revoked), registered_at, revoked_at. Ciphertext columns are unreadable by the API role.
- `engine_settings`: user_id, mode, pace, symbol, leverage, entry_pct, max_loss_pct, tp_profit_usd, trailing (bool), updated_at.
- `engines`: user_id, running, state, last_status, started_at, crash_count, updated_at.
- `trades`: id, user_id, symbol, side, size, entry_price, exit_price, pnl, fees, reason, opened_at, closed_at.
- `fills`: id, user_id, order_id, symbol, side, price, size, maker (bool), fee, ts. Partitioned by month.
- `stats_daily`: user_id, day, total_volume, maker_volume, taker_volume, fills, maker_fills, taker_fills, fees, pnl.
- `events`: id, user_id, type, payload (jsonb), created_at.
- `notification_links`: user_id, telegram_chat_id, email, preferences (jsonb).
- `audit_log`: id, actor_type (user, admin, system), actor_id, action, target_user_id, reason, ip_hash, created_at. Append-only (no update or delete grants).
- `admin_users`: id, email, role, mfa_enrolled, created_at.
- `billing_payments` (flagged): id, user_id, plan, amount, tx_signature, status, verified_at.

Use row-level ownership checks in every query. Add indexes on user_id and timestamps.

---

## 17. Documentation site (`docs.perpetua.fi`)

Structure:
1. **Getting Started:** What is Perpetua, Supported wallets, Five-minute quick start.
2. **Account Setup:** Connect and sign in, Fund your BULK account, Authorize the agent key, Revoke the agent key.
3. **Strategies:** Sweep, Trend, Quote, Churn, Pace presets, Choosing a mode.
4. **Settings:** Coin, Leverage, Entry size, Take-profit and trailing, Max loss, Minimum balance.
5. **Risk and Safety:** Kill switches, Stale feed protection, Stop and close behavior, Restarts and maintenance, Liquidation risk.
6. **Security:** Non-custodial design, Agent key custody, Signing policy and price band, What we never ask for, Reporting a vulnerability.
7. **Dashboard Guide:** every page with screenshots.
8. **Notifications:** Telegram linking, Email, Alert types.
9. **Fees and Billing:** BULK fees, Perpetua plans.
10. **Venues:** BULK (live), Roadmap for Hyperliquid, Lighter and Arcus.
11. **Troubleshooting:** Wallet will not sign, Balance not showing, Engine stopped, Orders not filling, Agent registration failed.
12. **Legal:** Terms, Privacy, Risk disclosure, Restricted countries.
13. **Glossary A to Z** (one entry per letter at minimum):
    - **A**gent key: a trade-only key authorized on your BULK account.
    - **A**TR: average true range, the volatility measure used for stops.
    - **B**ULK: the Solana-based perpetuals exchange Perpetua trades on.
    - **C**hurn: mode that alternates market buys and sells.
    - **D**aily loss limit: loss that triggers the kill switch for the UTC day.
    - **E**ntry size: share of balance x leverage used per trade.
    - **F**VG: fair value gap, a price imbalance zone used by Trend mode.
    - **G**race period: the 45 seconds engines get to cancel orders and close positions during a restart.
    - **H**old time: how long Trend mode keeps a position open.
    - **I**nventory skew: how Quote mode shifts prices to stay flat.
    - **J**itter: small random size changes that make trading look human.
    - **K**ill switch: automatic stop that cancels orders and halts the engine.
    - **L**everage: position size relative to your margin.
    - **M**aker: an order that rests on the book and adds liquidity.
    - **N**otional: dollar size of a position.
    - **O**rder block: a price zone where large orders previously filled.
    - **P**ace: preset for trade speed (Normal, Faster, Aggressive).
    - **Q**uote mode: post-only market making on both sides.
    - **R**econciliation: periodic check that engine state matches BULK.
    - **S**weep: a move through a swing high or low that takes out stops.
    - **T**aker: an order that fills immediately against the book.
    - **U**nrealized PnL: profit or loss on an open position.
    - **V**olume: total traded notional.
    - **W**allet adapter: the library that connects your Solana wallet.
    - **X** (cross margin): margin shared across positions.
    - **Y**ield: Perpetua does not offer yield; this entry says so plainly.
    - **Z**ero-custody: Perpetua never holds your funds.

Docs must have search, a dark and light theme matching the brand, copy buttons on code, "Last updated" dates, and the same three languages (English first, then Bangla and Hindi).

---

## 18. API design (FastAPI)

All routes under `/api/v1`. JSON only. Every mutating route needs a session and CSRF token. Sensitive routes need a step-up signature.

- `POST /auth/nonce`, `POST /auth/verify`, `POST /auth/logout`, `GET /auth/session`
- `GET /me`, `PATCH /me` (lang, theme, timezone), `DELETE /me` (step-up)
- `POST /terms/accept`
- `GET /bulk/account` (balance, margin, positions, open orders)
- `GET /markets` (cached `exchangeInfo`: symbol, tradable, max leverage, min size)
- `POST /agent/prepare` (creates agent, returns agent pubkey and payload bytes to sign)
- `POST /agent/register` (signed payload), `POST /agent/revoke/prepare`, `POST /agent/revoke`
- `GET /engine`, `PUT /engine/settings`, `POST /engine/start` (step-up), `POST /engine/stop`, `POST /engine/close-now`
- `GET /engine/plan` (dry-run sizing preview)
- `GET /trades`, `GET /fills`, `GET /stats?range=`, `GET /events`, `GET /events/stream` (SSE)
- `POST /notifications/telegram/code`, `DELETE /notifications/telegram`, `PUT /notifications/preferences`
- `GET /public/stats` (cached 60s, aggregate only)
- `POST /stepup/challenge`, which returns the human-readable action message and nonce for the wallet to sign.
- Admin routes under `/admin/api/v1` on the admin origin only.

OpenAPI spec generated and published in the docs (without admin routes).

---

## 19. Legal and compliance pages

- **Terms of Service:** eligibility, no investment advice, no custody, user responsibility for funds and settings, service availability, termination, limitation of liability, governing law (placeholder for counsel).
- **Risk Disclosure:** leverage, liquidation, slippage, strategy losses, exchange risk, smart contract and chain risk, no guarantee of points or airdrops.
- **Privacy Policy:** what is stored (wallet public key, settings, trading stats, hashed IP, Telegram chat id if linked), retention periods, deletion rights.
- **Cookie Policy:** only essential cookies on the app.
- **Restricted jurisdictions:** block sign-in from countries that BULK and later venues restrict, plus sanctioned regions. Configurable list in admin. Show a clear message, not a silent failure.
- Put a banner in the admin panel: "Have a lawyer review Terms, Risk Disclosure and the restricted list before public launch."

---

## 20. Performance, SEO and accessibility

- Lighthouse 95+ on marketing pages (performance, accessibility, best practices, SEO). App pages 90+.
- LCP under 2.0s on 4G, CLS under 0.05, INP under 200ms.
- Fonts self-hosted and subset, `font-display: swap`.
- Images in AVIF/WebP with sizes set; hero image under 250 KB.
- Metadata, Open Graph and Twitter cards on every marketing page, using the Perpetua cover and logo. `sitemap.xml`, `robots.txt` (app and admin are `noindex`).
- WCAG 2.2 AA: keyboard navigation, visible focus rings in gold, labelled form controls, live regions for engine status changes, no color-only status indicators.

---

## 21. Testing and quality

- **Unit:** preimage builders (byte-for-byte against `bulk-keychain`), signing policy (every reject rule), sizing math, settings validation, SIWS verification (bad domain, reused nonce, expired message, wrong signer).
- **Existing tests:** keep `tests/test_offline.py` and `tests/test_tgbot.py` passing, and port the Telegram flow tests to the web flow.
- **Integration:** full onboarding and start/stop against BULK testnet using the faucet, and against `tests/bench/fake_exchange.py` in CI.
- **End-to-end:** Playwright with a mock wallet adapter: sign-in, onboarding, start, stop, close now, revoke, language switch, mobile viewport.
- **Load:** k6 for the API, plus the existing `tests/bench/bench.py` for 500 running engines. Track event-loop lag.
- **Security:** OWASP ZAP baseline scan in CI, Semgrep rules for secret handling, a test that fails if any log line contains a base58 string of secret-key length, and an external penetration test before public launch.
- **Chaos:** kill the engine container mid-trade and verify orders are reconciled and the user is alerted.

---

## 22. Build phases and acceptance criteria

**Phase 1: Foundations.** Repo layout (`apps/web`, `apps/admin`, `services/api`, `services/engine`, `services/signer`, `services/notify`, `docs`), CI, IaC, staging environment, design system and component library.
*Done when:* CI is green with lint, types, tests and security scans; staging deploys from `main`.

**Phase 2: Auth and marketing site.** SIWS, sessions, all marketing pages, legal pages, i18n.
*Done when:* sign-in works with all three wallets on staging, marketing pages hit the Lighthouse targets.

**Phase 3: Signer Service and agent onboarding.** KMS custody, signing policy, agent prepare/register/revoke, wizard steps I to III.
*Done when:* a testnet user registers and revokes an agent from the browser without any secret leaving the wallet, and every policy rejection has a passing test.

**Phase 4: Engine Service.** Port manager and engine, RemoteSigner, Redis commands and events, wizard steps IV and V, dashboard, engine page.
*Done when:* 50 testnet users run all four modes for 24 hours with no orphaned orders and correct stats.

**Phase 5: Notifications, admin, docs.** Telegram alert linking, email, admin panel, full docs site, status page.
*Done when:* every alert type reaches Telegram and web, admin actions appear in user activity logs, docs are complete in English.

**Phase 6: Hardening and launch.** Penetration test, load test at 500 engines, backup restore drill, incident runbook, bug bounty page, legal review.
*Done when:* no open high or critical findings, restore drill passes, mainnet launch checklist signed off.

**Phase 7: More venues.** Add a `VenueAdapter` interface (account state, markets, place, cancel, cancel all, set leverage, register and revoke agent) and implement Hyperliquid (API wallets), Lighter and Arcus, each only after confirming the venue supports trade-only delegated keys.

---

## 23. Final deliverables

1. Monorepo with all apps and services, README per service, one-command local dev (`docker compose up`).
2. Infrastructure as code for staging and production.
3. Published docs site and OpenAPI reference.
4. Test suites with coverage reports (target 85% on API, Signer and engine glue code).
5. Security documentation: threat model (STRIDE), data-flow diagram, key custody design, incident response runbook, key rotation runbook.
6. Launch checklist with every item in Section 3 ticked, with evidence links.
7. A written list of open questions and assumptions, especially anything about BULK's API you could not confirm from official sources.

Build it carefully, verify everything against the existing code and BULK's official docs, and never trade security for speed.
