# Perpetua: Project Context (handoff)

Read this file first in any new chat. It holds every decision made so far.

## Concept

Web3 perp volume farming service. Users connect their wallet and sign in on the website, fund their own exchange account with USDC, and authorize a trade-only agent key. A bot uses that key to trade and build volume on perp DEXs with the user's own money.

- **v1 venue:** BULK (bulk.trade), a Solana perp DEX. USDC collateral.
- **Later:** Hyperliquid, Lighter, Arcus.
- **Existing bot:** `bulk-bot-mainnet-vps` (Python 3.12). Custom BULK connector (`bulkbot/`) plus a Telegram multi-user control bot (`tgbot/`). Runs on a VPS with Docker. Not in this repo; the owner has the zip.
- **Style:** classic / classical (Roman marble, gold, engraved banknote look).

## Brand

- **Name:** Perpetua (Latin for "perpetual")
- **Full name:** Perpetua Finance, or just "Perpetua ⚜️". Avoid "Perpetua Protocol" because "Perpetual Protocol" (perp.com) already exists.
- **Tagline:** Volume, Perpetually.
- **Colors:** navy `#0B1426`, antique gold `#C9A45C`, ivory `#F2EBDD`
- **Fonts:** Cinzel (headings), Cormorant Garamond (body), Inter (app UI and numbers)
- **Mark:** ⚜️

## Handles (availability not yet checked)

| Platform | Display name | Username |
|---|---|---|
| X | Perpetua ⚜️ | @perpetua_fi |
| Telegram channel | Perpetua Protocol | @perpetua_fi |
| Telegram group | Perpetua Community | @perpetua_chat |
| Telegram bot | Perpetua Bot | @PerpetuaFiBot |
| Discord | Perpetua Protocol | discord.gg/perpetua |
| Instagram | Perpetua ⚜️ | @perpetua.fi |

Backups: @perpetuaxyz, @perpetua_hq, @perpetuaprotocol

## Bios

**X / Instagram (Option 1, recommended):**
```
Classical discipline. Perpetual volume. ⚜️
Automated volume farming on Hyperliquid · Lighter · Bulk · Arcus
Your wallet. Your funds.
```

**Option 2:**
```
Farm perp DEX airdrops on autopilot ⚜️
Connect once, we build your volume on Hyperliquid, Lighter, Bulk & Arcus.
Volume, Perpetually.
```

**Option 3:**
```
Volume, Perpetually. ⚜️
Automated perp volume farming across the top DEXs.
```

Location: `The Perpetual Hall 🏛️` · Website: `perpetua.fi`

Only use "Your wallet. Your funds." / "non-custodial" if the bot truly cannot withdraw (agent key, trade-only).

**Telegram channel description:**
```
⚜️ Perpetua Protocol: Volume, Perpetually.

Connect your wallet, fund your account, and let our bot farm volume across the top perpetual DEXs: Hyperliquid, Lighter, Bulk and Arcus.

🏛️ Automated volume farming
📈 Multi-venue perp trading
🔐 Your wallet, your funds

Community: @perpetua_chat
Website: perpetua.fi
```

**Discord About:**
```
Welcome to the Hall of Perpetua ⚜️
We farm perpetual DEX volume for our users on Hyperliquid, Lighter, Bulk and Arcus. Connect your wallet, fund your account, and let the volume flow, perpetually.
```

## Domains (availability not yet checked)

Top picks: **perpetua.fi** (first choice), perpetua.xyz, perpetua.trade, perpetua.finance, perpetua.markets
.com backups: perpetuafi.com, useperpetua.com, getperpetua.com, perpetuahq.com, perpetua.app

Structure: `perpetua.fi` (landing), `app.perpetua.fi` (dashboard), `docs.perpetua.fi` (docs). Also buy a .com and redirect it, to block phishing clones.

## Image prompts

### Profile picture (1:1, `--ar 1:1 --style raw --v 7`)
```
A regal, classical emblem logo for a premium Web3 trading protocol named "Perpetua", designed as a perfectly centered circular medallion on a deep midnight navy background (#0B1426). At the heart of the medallion sits an elegant, ornate serif monogram letter "P" in antique burnished gold (#C9A45C), rendered in the style of Roman imperial inscriptions, with fine chiseled bevels, subtle metallic sheen and soft highlights catching the light. The "P" is gracefully intertwined with a flowing infinity-loop ribbon, symbolizing perpetual motion and endless volume. Surrounding the monogram is a finely detailed laurel wreath of gold leaves, each leaf crisply engraved with delicate veins, the two branches meeting at the bottom and tied with a small ribbon. The outer ring of the medallion features intricate guilloche engraving patterns, like those found on vintage banknotes and old-world stock certificates, with ultra-fine concentric lines and rosette details. Tiny subtle stars or dots are spaced evenly around the outer rim like a classical coin edge. The overall aesthetic is timeless, luxurious and trustworthy, a fusion of ancient Roman coinage, Renaissance heraldry and modern crypto finance. Lighting is soft and dramatic, with a gentle golden rim glow separating the medallion from the dark background. Ultra-sharp detail, symmetrical composition, clean negative space around the emblem so it reads clearly even at very small sizes, perfect for a circular social media avatar crop. Style: premium engraved gold coin, embossed metal relief, museum-quality craftsmanship, high contrast between gold and navy, 8K, photorealistic metallic texture with a refined vector-like clarity.
```
Negative: `text, words, watermark, signature, blurry, low quality, cartoon, neon, cyberpunk, clutter, asymmetry, extra letters, distorted P, busy background, 3D plastic look`

### Cover / banner (3:1 for X, `--ar 3:1 --style raw --v 7`)
```
An ultra-wide, cinematic, classical banner for a premium Web3 perpetual trading protocol called "Perpetua". The scene is a grand ancient Greco-Roman marble hall at twilight, with a long symmetrical row of towering ivory Corinthian columns (#F2EBDD) receding into soft golden haze. The floor is polished dark navy marble (#0B1426) with thin veins of gold, reflecting the columns like still water. Along the upper frieze of the hall, instead of traditional carvings, elegant bas-relief candlestick charts and rising price lines are chiseled into the marble and inlaid with antique gold leaf (#C9A45C), glowing faintly as if lit from within, a seamless blend of ancient architecture and modern finance. Between the columns, subtle floating streams of fine golden light trace flowing infinity-shaped paths, representing endless trading volume moving perpetually through the hall. In the far background, a large softly glowing golden laurel wreath emblem hangs above a monumental archway, partially veiled in atmospheric mist. The edges of the composition are framed with delicate guilloche engraving patterns and fine filigree borders, inspired by vintage banknotes, old stock certificates and Renaissance manuscripts. The color palette is strictly deep midnight navy, antique burnished gold and warm ivory marble, creating a mood that is timeless, powerful, trustworthy and luxurious. Lighting is dramatic chiaroscuro: warm golden god-rays streaming diagonally through the columns, deep shadows, gentle volumetric fog. The center-left area is kept calm, darker and uncluttered to leave clean negative space for a title and tagline to be added later, while the richest detail sits on the right side. Composition is wide, balanced and elegant, with nothing important placed at the far bottom-left corner (where a profile picture overlaps on social media). Style: classical oil painting meets hyper-detailed architectural render, museum-grade, cinematic depth of field, 8K resolution, ultra-sharp, refined and minimal in color, no modern clutter.
```
Negative: `text, letters, logos, watermark, neon colors, cyberpunk, people, faces, crowded, cartoon, low resolution, blurry, oversaturated, random symbols, brand logos`

Tips: add the name and tagline later in Canva/Figma (Cinzel font). Do not use the venues' official logos.

## Website

The full production build prompt is in [`docs/PERPETUA_WEBSITE_PROMPT.md`](PERPETUA_WEBSITE_PROMPT.md). Stack: Next.js 15 + FastAPI (reusing `bulkbot/`) + PostgreSQL + Redis + a separate KMS-backed Signer Service.

## Security findings in the existing Telegram bot

1. **The Telegram flow asks users to paste their wallet private key** so the bot can register the agent. The key is deleted after use, but it still passes through Telegram and the server. The website must never do this. Users sign agent registration in their own wallet.
2. **The master PIN can decrypt every user's agent key**, and on a Linux VPS it is saved as a plain file (`tg_secrets/master.pin`). The website replaces this with KMS custody and no master key.
3. Admin unlock is silent to the user. On the website, every admin action shows in the user's activity log.

## Open questions

- Does BULK accept a raw Ed25519 `signMessage` signature from Phantom/Solflare/Backpack for agent registration? Must be tested on testnet before building onboarding.
- Is the BULK account address the same as the user's Solana wallet address?
- Does bulk.trade offer its own UI for registering agent keys?
- Social handles and domains: availability not checked yet.

## Next steps

1. Check and register handles and the domain.
2. Generate the profile picture and cover.
3. Give the website prompt (plus the bot zip) to a coding agent and build phase by phase.
