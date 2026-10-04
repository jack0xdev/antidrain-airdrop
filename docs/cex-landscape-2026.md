# Centralized Crypto Exchanges — 2026 Landscape (Networks & Withdrawal Rules)

_As of 4 October 2026._

This report covers about 120 active centralized exchanges (CEXs): the global top tier, mid-tier offshore venues, and regional fiat on-ramps. A further section lists venues that closed, are winding down or are sanctioned in 2026.

---

## 0. Scope, method and limitations (read first)

| Item | Status |
|---|---|
| **Exchange name, website, rank, networks, withdrawal rules, notes** | Included. Sources: Q2-2026 exchange reports from CryptoRank, TokenInsight and CoinGecko research, plus exchange help-centre pages and 2026 news (see Sources). |
| **Withdrawal / settlement / deposit-processing contract addresses (items 6–8 of the request)** | **Not included.** During the research, pulling exchange-tagged addresses from a public label dataset was blocked by this environment's safety controls. That part was not pursued another way, so this report has **no addresses at all** (hot wallet or otherwise). |
| **Live verification** | Limited. The environment's network policy blocks direct fetches from CoinGecko, CoinMarketCap, CryptoRank, Etherscan and most exchange sites. Rankings come from published 2026 reports. Network support comes from exchange documentation and public knowledge as of mid-2026 and **should be re-checked on each exchange's deposit/withdraw page for the specific asset** before moving funds. |
| **"Top 200"** | No single top-200 list exists: CoinGecko, CoinMarketCap, CryptoRank and Kaiko all rank differently, and wash-trading adjustments vary. Below the top ~20, ranks are shown as **tiers** (Top 20 / 50 / 100 / 200), not exact positions. |
| **Excluded on purpose** | Exchanges under OFAC/EU/UK sanctions that block normal access (e.g., Garantex/Grinex, Iranian venues). HTX is listed with a sanctions warning because it still operates outside the EU and UK. |

**Legend for network columns:** ✓ = broadly supported (several assets) · ◐ = limited, asset-specific, or not verified · — = not supported to our knowledge.
**Abbreviations:** ETH = Ethereum mainnet, BSC = BNB Smart Chain, ARB = Arbitrum One, OP = Optimism, BASE = Base, POL = Polygon PoS, AVAX = Avalanche C-Chain, SOL = Solana, TRX = Tron, TON = The Open Network.

---

## 1. 2026 market snapshot

### 1.1 Spot volume leaders — Q2 2026 (CryptoRank)

| # | Exchange | Q2-2026 spot volume | Share |
|---|---|---|---|
| 1 | Binance | $731B | 24.4% |
| 2 | Bitget | $263B | 8.8% |
| 3 | Bybit | $182B | 6.1% |
| 4 | Gate | $152B | 5.1% |
| 5 | OKX | $149B | 5.0% |
| 6 | Coinbase | $144B | 4.8% |
| 7 | KuCoin | $138B | 4.6% |
| 8 | MEXC | $103B | 3.4% |

- Total CEX spot volume was about **$3.0T in Q2 2026**, a two-year low (−18.9% QoQ). Binance hit a record-low monthly share of 20.9% in June 2026.
- Bitget's June 2026 spot volume rose 512% (to about $202B), briefly making it #2.
- Other trackers (CoinGecko, TokenInsight) also put **Upbit, Crypto.com, HTX and Kraken** in the top 12. Kraken ranks top-5 on trust/regulated lists.
- **For 2025 as a whole** (CoinGecko), the spot leaders were Binance 39.2%, Bybit 8.1%, MEXC 7.8%, Gate 7.5%, Crypto.com 7.2% and Bitget 6.4%.

### 1.2 Structural changes in 2026 that affect withdrawals

| Event | Effect on users |
|---|---|
| **EU MiCA transition ended 1 July 2026** | EU residents can only use authorised CASPs (crypto-asset service providers). Several venues exited the EU or shut down (AscendEX, Knaken). |
| **EU Transfer of Funds Regulation (travel rule)** | For transfers to a **self-hosted wallet above €1,000**, the CASP must check that the user owns or controls the address. Methods include a signed message, a micro-deposit ("Satoshi test"), or a screenshot/attestation. EBA guidance now requires only one method. |
| **UK sanctions on 18 Russia-linked exchanges (May 2026), incl. HTX; EU sanctions on HTX from 23 Aug 2026** | Binance, OKX, Bybit and Bitget warned that transfers involving HTX get extra compliance review. Upbit suspended withdrawals to HTX. |
| **South Korea: amended Specific Financial Information Act, effective 20 Aug 2026** | Travel-rule linkage with overseas VASPs (virtual asset service providers) is formalised. Withdrawals go only to registered personal wallets or whitelisted VASPs. |
| **Binance "Withdraw Protection" (May 2026)** | Opt-in lock that blocks all on-chain withdrawals for 1–7 days, added as a defence against physical "wrench" attacks. |
| **Coinbase address book: "all EVM networks" entries (Feb 2026)** | One saved address can be used on every EVM chain Coinbase supports (Prime/Exchange API). |

---

## 2. Withdrawal mechanics common to almost every CEX

Unless a row below says otherwise, assume all of the following apply.

1. **Custom address: yes.** Every exchange listed lets you withdraw to an external address of your choice on a supported network. "Multi-address" means an **address book**: unlimited saved addresses, per asset or (on many venues) "universal"/EVM-wide entries.
2. **KYC first.** Mandatory at nearly every top-50 venue: Binance, OKX, Bybit, Bitget, KuCoin (all users since 2023), Gate (KYC before deposit/withdraw), Coinbase, Kraken. **MEXC** still allows unverified accounts, but withdrawals are capped at about **1,000 USDT/day**.
3. **Whitelist mode (optional).** With it on, only address-book entries can receive funds. New entries usually face a **24-hour cooldown** (Bybit "New Address Withdrawal Lock", Binance whitelist, OKX).
4. **Security holds.** Changing your password, 2FA or phone, or logging in from a new device, typically freezes withdrawals for **24–48 hours**. Kraken applies a **72-hour hold** after card/ACH/PayPal purchases, and its help centre says adding a new withdrawal address also triggers a 72-hour hold.
5. **Travel rule prompts.** You may have to state whether the destination is your own wallet or another exchange (and which one), and give beneficiary details for third-party transfers. Some jurisdictions (Japan, Korea, EU above €1,000) also require wallet-ownership proof or block VASPs that aren't on the approved list.
6. **Memo/tag.** Required for XRP, XLM, ATOM, EOS, HBAR, TON (to exchanges) and some others. A missing tag is the most common cause of lost CEX deposits.
7. **Fees.** A flat network fee is set by the exchange for each asset and chain. Rough levels: ETH mainnet is the most expensive; L2s (ARB/OP/BASE), SOL, TRX and BSC are usually under $1. Internal transfers (same exchange, by email, UID or pay ID) are usually free and instant: Binance Pay, OKX/Bybit internal transfer, Coinbase-to-Coinbase.
8. **Contract wallets.** Most exchanges withdraw with a plain transfer from a pooled wallet. Sending to a smart-contract wallet (Safe, ERC-4337 account) generally works for native ETH and ERC-20, but some exchanges warn that **contract recipients may fail or need gas headroom**. Check each exchange's FAQ.

---

## 3. Tier 1 — Global leaders

### 3.1 Overview

| Exchange | Website | Rank / volume (2026) | Withdrawal to custom address | Restrictions & notable rules | Special notes |
|---|---|---|---|---|---|
| **Binance** | binance.com | #1 spot & derivatives; Q2 $731B spot (24.4%) | Yes; address book, universal addresses, whitelist | KYC mandatory; travel-rule questionnaire in many regions; whitelist with 24 h cooldown; opt-in **Withdraw Protection** 1–7 day lock (May 2026) | Widest network coverage. Free internal Binance Pay. Regional entities: Binance.US, Binance TR, Binance Japan, Tokocrypto (ID). |
| **Bitget** | bitget.com | #2 spot in Q2 2026 ($263B, 8.8%); top-5 derivatives | Yes; address book & whitelist | KYC mandatory (since 2023), Tier-1 daily withdrawal up to $3M | Very broad chain list. Owns Bitget Wallet (self-custody). |
| **Bybit** | bybit.com | #3 spot Q2 2026 ($182B); #2 for full-year 2025 | Yes; address book, whitelist | KYC mandatory; **New Address Withdrawal Lock** (24 h); travel-rule prompts (EU entity under MiCA) | Survived the Feb 2025 hot-wallet hack ($1.46B, attributed to the DPRK); user funds were made whole. |
| **Gate** (Gate.io → **Gate.com**, May 2025) | gate.com | #4 spot Q2 2026 ($152B) | Yes | KYC required before deposit/withdraw; limits shown per account | One of the largest altcoin and chain catalogues. Licensed entities in Japan, Dubai and the EU (Malta). |
| **OKX** | okx.com | #5 spot Q2 ($149B); top-3 derivatives | Yes; address book with "universal EVM address" option | KYC; whitelist with 24 h lock on new addresses; travel-rule prompts (EU/UAE/SG entities) | Runs X Layer (own L2). OKX US and OKX TR are separate entities with narrower asset lists. |
| **Coinbase** | coinbase.com | #6 spot Q2 ($144B); CoinGecko Trust Score 10/10 | Yes; **address book/allowlist**, EVM-wide entries since Feb 2026 | Strict KYC; some withdrawal holds after bank/card buys; travel-rule beneficiary prompts | **Base** is Coinbase's own L2. Owns **Deribit** ($2.9B acquisition completed Aug 2025). Coinbase International is the offshore derivatives venue. |
| **KuCoin** | kucoin.com | #7 spot Q2 ($138B) | Yes | Mandatory KYC; unverified users are limited to sell/withdraw-only | Broad chain catalogue; KuCoin EU entity under MiCA. |
| **MEXC** | mexc.com | #8 spot Q2 ($103B); fastest growing 2025 (+90.9% YoY) | Yes | **No-KYC tier allowed**: about 1,000 USDT/day cap; Primary KYC raises it to 80 BTC/day, Advanced to 200 BTC/day | Very fast new-listing pace; broad chain support. |
| **Upbit** | upbit.com | Top-10 by volume (Korea #1) | **Only to registered personal wallets or whitelisted VASPs** | Korean real-name KYC; travel rule above ₩1M; withdrawals blocked to un-whitelisted foreign exchanges; **HTX withdrawals suspended (2026)** | Nov 2025 incident: about $30M from a Solana hot wallet. Operator: Dunamu (VerifyVASP travel-rule network). |
| **Crypto.com** | crypto.com | Top-10 spot (7.2% share in 2025) | Yes; whitelist with cooldown | KYC; travel-rule prompts; withdrawal whitelist is mandatory in some app versions | Runs Cronos (EVM). App and Exchange have separate balances. |
| **HTX** (ex-Huobi) | htx.com | Top-12 by volume | Yes | ⚠️ **Sanctioned by the UK (May 2026) and EU (from 23 Aug 2026)**. EU/EEA/CH users had a window to withdraw. Transfers to/from HTX trigger extra review at Binance, OKX, Bybit and Bitget, and Upbit suspended HTX withdrawals | Reserves reported moving to Poloniex (same ownership circle). High counterparty risk. |
| **Kraken** | kraken.com | Top-12 spot; top regulated venue | Yes; address book | KYC; **72-hour holds** after certain fiat buys and new withdrawal addresses; EU TFR self-hosted wallet checks | Runs **Ink** (OP Stack L2). MiCA licensed (Ireland). |
| **BingX** | bingx.com | Top-20 (derivatives/copy trading) | Yes | KYC tiers; whitelist option | Broad EVM, SOL and TRX coverage. |
| **Bithumb** | bithumb.com | Top-20 (Korea #2) | Registered/verified wallets only | Korean KYC & travel rule; unverified wallet addresses rejected | Part of the CODE travel-rule network (with Coinone and Korbit). |
| **Bitfinex** | bitfinex.com | Top-30 | Yes | KYC for fiat and higher limits | Strong USDT/TON/TRX rails; iFinex group (Tether affiliate). |
| **Gemini** | gemini.com | Top-50 | Yes; address allowlist (approved addresses) | ⚠️ **Exited the UK, EU and Australia** (withdrawal-only from 5 Mar 2026, closed 6 Apr 2026; account transfer to eToro offered) | Listed (GEMI) since Sept 2025; now focused on the US and Singapore. |
| **Bitstamp** (by Robinhood) | bitstamp.net | Top-50 | Yes | KYC; EU TFR checks | Acquired by Robinhood (closed June 2025). |

### 3.2 Network support matrix (Tier 1)

| Exchange | ETH | BSC | ARB | OP | BASE | POL | AVAX | SOL | TRX | TON | Other notable chains |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Binance | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | opBNB, zkSync, Linea, Starknet, Sui, Aptos, NEAR, Kaia, BTC, LN |
| Bitget | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Morph, Sui, Aptos, Mantle |
| Bybit | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Mantle, Sui, Aptos |
| Gate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Gate Layer/GateChain, very long tail |
| OKX | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | X Layer, zkSync, Linea, Starknet, Sui, Aptos |
| Coinbase | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ◐ | Base native; BTC, LTC, DOGE, XRP, etc. |
| KuCoin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | KCC legacy, Sui, Aptos |
| MEXC | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Very long tail of new chains |
| Upbit | ✓ | ◐ | ◐ | ◐ | ◐ | ◐ | ✓ | ✓ | ✓ | ◐ | Mostly native networks of listed coins; Kaia |
| Crypto.com | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | Cronos EVM / Cronos POS |
| HTX | ✓ | ✓ | ✓ | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | HECO legacy |
| Kraken | ✓ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | Ink, BTC/LN, many L1s |
| BingX | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Bithumb | ✓ | ◐ | ◐ | ◐ | ◐ | ◐ | ✓ | ✓ | ✓ | ◐ | Native networks of listed coins |
| Bitfinex | ✓ | ◐ | ◐ | ◐ | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ | Liquid, many USDT rails |
| Gemini | ✓ | — | ◐ | ◐ | ◐ | ◐ | ◐ | ✓ | — | — | BTC, ZEC, etc. |
| Bitstamp | ✓ | — | ◐ | ◐ | ◐ | ◐ | ◐ | ✓ | — | — | — |

---

## 4. Tier 2 — Offshore/global mid-tier (≈ Top 20–80)

| Exchange | Website | Approx. tier | Main networks | Withdrawal rules & restrictions | Notes |
|---|---|---|---|---|---|
| WhiteBIT | whitebit.com | Top 30 | ETH, BSC, ARB, OP, BASE, POL, SOL, TRX, TON + WhiteChain | KYC; travel-rule flow documented (VASP directory, self-hosted flag) | Named in India FIU notice (Sept 2026). |
| LBank | lbank.com | Top 30 | ETH, BSC, ARB, BASE, SOL, TRX, TON + long tail | KYC tiers; whitelist | Fast meme/new-token listings. |
| XT.com | xt.com | Top 40 | ETH, BSC, ARB, BASE, POL, SOL, TRX, TON | KYC tiers | Named in India FIU notice (Sept 2026). |
| Toobit | toobit.com | Top 50 (derivatives) | ETH, BSC, ARB, SOL, TRX, TON | KYC | Named in India FIU notice. |
| BloFin | blofin.com | Top 50 (derivatives) | ETH, BSC, ARB, BASE, SOL, TRX | KYC tiers | Named in India FIU notice. |
| Bitunix | bitunix.com | Top 50 (derivatives) | ETH, BSC, ARB, SOL, TRX | KYC tiers | Named in India FIU notice. |
| WEEX | weex.com | Top 50 (derivatives) | ETH, BSC, ARB, SOL, TRX | KYC tiers | Named in India FIU notice. |
| Phemex | phemex.com | Top 60 | ETH, BSC, ARB, OP, BASE, POL, AVAX, SOL, TRX | KYC; whitelist | Hot-wallet key compromise in Jan 2025; still operating. |
| Pionex | pionex.com | Top 60 | ETH, BSC, ARB, SOL, TRX, TON | KYC | Trading-bot focused; Pionex US separate. Named in India FIU notice. |
| BTCC | btcc.com | Top 80 | ETH, BSC, SOL, TRX | KYC tiers | Derivatives focused. |
| Bitrue | bitrue.com | Top 80 | ETH, BSC, XRP Ledger, XDC, SOL, TRX | KYC tiers; memo for XRP | XRP-ecosystem focus. |
| DigiFinex | digifinex.com | Top 80 | ETH, BSC, SOL, TRX | KYC tiers | Named in India FIU notice. |
| CoinW | coinw.com | Top 80 | ETH, BSC, ARB, SOL, TRX | KYC tiers | — |
| BYDFi | bydfi.com | Top 80 | ETH, BSC, ARB, SOL, TRX | KYC tiers | — |
| Deepcoin | deepcoin.com | Top 80 | ETH, BSC, SOL, TRX | KYC tiers | Derivatives. |
| BTSE | btse.com | Top 80 | ETH, BSC, ARB, SOL, TRX | KYC | — |
| WOO X | woox.io | Top 80 | ETH, BSC, ARB, BASE, SOL, TRX | KYC | Hacked July 2025 ($14M); named in India FIU notice. |
| HashKey Global / HashKey Exchange (HK) | global.hashkey.com / hashkey.com | Top 80 | ETH, ARB, BASE, SOL, TRX (HK entity narrower) | HK SFC-licensed entity: strict whitelist and self-hosted wallet ownership proof | HashKey Chain (OP Stack L2). |
| OSL | osl.com | Top 120 | ETH, SOL, BTC | HK SFC rules: whitelisted & verified self-hosted wallets only | Institutional/HK retail. |
| Bullish | bullish.com | Top 40 (institutional) | ETH, SOL, BTC + major stablecoins | Institutional onboarding | Listed (NYSE: BLSH) since Aug 2025; owns CoinDesk. |
| Coinbase International | international.coinbase.com | Top 30 (perps) | Settles in USDC (ETH/BASE/SOL) | Non-US institutions/retail | Offshore arm of Coinbase. |
| Deribit (Coinbase) | deribit.com | #1 crypto options | BTC, ETH, SOL, USDC/USDT (ETH, SOL) | KYC; address whitelist with **optional security-key requirement per address** | Acquired by Coinbase (Aug 2025). |
| Poloniex | poloniex.com | Top 100 | ETH, BSC, TRX, SOL | KYC | ⚠️ Linked to HTX ownership circle; reported to have received HTX reserves in 2026; not MiCA-licensed. |
| HitBTC | hitbtc.com | Top 120 | ETH, BSC, TRX | KYC | — |
| CEX.IO | cex.io | Top 120 | ETH, BSC, SOL, TRX, POL | KYC | — |
| P2B | p2pb2b.com | Top 120 | ETH, BSC, TRX, SOL | KYC tiers | Listing-oriented; volume quality questioned. |
| ProBit Global | probit.com | Top 150 | ETH, BSC, POL, SOL | KYC tiers | — |
| Hotcoin | hotcoin.com | Top 150 | ETH, BSC, TRX, SOL | KYC tiers | — |
| BigONE | big.one | Top 150 | ETH, BSC, TRX, SOL | KYC tiers | Hacked 2025 ($27M); still operating. |
| Biconomy.com | biconomy.com | Top 150 | ETH, BSC, TRX | KYC tiers | Not affiliated with the Biconomy AA protocol. |
| Azbit | azbit.com | Top 200 | ETH, BSC, TRX | KYC tiers | — |
| LATOKEN | latoken.com | Top 200 | ETH, BSC, TRX, SOL | KYC tiers | Named in India FIU notice. |
| KCEX | kcex.com | Top 200 | ETH, BSC, SOL, TRX | Light KYC | Derivatives. |
| Ourbit | ourbit.com | Top 200 | ETH, BSC, SOL, TRX | Light KYC | — |
| Blockchain.com Exchange | exchange.blockchain.com | Top 150 | ETH, BTC, SOL | KYC | — |
| LMAX Digital | lmaxdigital.com | Institutional | BTC, ETH, SOL, USDC | Institutional whitelist | Institutional only. |

---

## 5. Regional / fiat on-ramp exchanges

Regional venues usually support **fewer chains**, mostly the native network of each listed coin plus ETH and sometimes TRX/SOL USDT. Their withdrawal rules follow local law, which is often stricter than offshore venues.

### 5.1 East Asia

| Exchange | Website | Country | Tier | Networks | Withdrawal rules | Notes |
|---|---|---|---|---|---|---|
| Upbit | upbit.com | South Korea | Top 10 | Native + ETH, SOL, TRX, AVAX | Registered wallets / whitelisted VASPs only | See Tier 1. |
| Bithumb | bithumb.com | South Korea | Top 20 | Native + ETH, SOL, TRX | Verified wallets only | See Tier 1. |
| Coinone | coinone.co.kr | South Korea | Top 80 | Native + ETH | Withdrawals to unverified external wallets halted (travel rule) | CODE network. |
| Korbit | korbit.co.kr | South Korea | Top 120 | Native + ETH | Verified wallets only | CODE network. |
| GOPAX | gopax.co.kr | South Korea | Top 200 | Native + ETH | Verified wallets only | Binance-linked since 2023. |
| bitFlyer | bitflyer.com | Japan | Top 60 | BTC, ETH, ERC-20, XRP, SOL ◐ | Withdrawals to exchanges outside the TRUST travel-rule network are blocked for 21 jurisdictions; **self-custody wallets allowed** | bitFlyer Europe/US separate. |
| Coincheck | coincheck.com | Japan | Top 100 | Native + ETH | Travel-rule restrictions to non-allowed VASPs | Nasdaq-listed parent (Coincheck Group). |
| bitbank | bitbank.cc | Japan | Top 100 | Native + ETH | Japanese travel-rule restrictions | — |
| GMO Coin | coin.z.com | Japan | Top 150 | Native + ETH | Japanese travel-rule restrictions | — |
| SBI VC Trade | sbivc.co.jp | Japan | Top 200 | Native + ETH | Japanese travel-rule restrictions | Took over DMM Bitcoin accounts (2025). |
| BITPoint | bitpoint.co.jp | Japan | Top 200 | Native + ETH | Japanese travel-rule restrictions | — |
| Binance Japan | binance.com/ja | Japan | Top 150 | Narrower than global Binance | Japanese travel-rule restrictions | — |
| MAX (MaiCoin) | max.maicoin.com | Taiwan | Top 150 | ETH, TRX, BSC ◐ | KYC | — |
| BitoPro | bitopro.com | Taiwan | Top 200 | ETH, TRX | KYC | — |
| OSL / HashKey Exchange | osl.com / hashkey.com | Hong Kong | — | See §4 | SFC rules: verified self-hosted wallets | — |

### 5.2 South & Southeast Asia

| Exchange | Website | Country | Tier | Networks | Withdrawal rules | Notes |
|---|---|---|---|---|---|---|
| Bitkub | bitkub.com | Thailand | Top 80 | Native + ETH, BSC, KUB chain | Thai SEC KYC; travel rule | Bitkub Chain (EVM). |
| Bitazza | bitazza.com | Thailand | Top 200 | ETH, BSC, TRX | KYC | — |
| Indodax | indodax.com | Indonesia | Top 100 | Native + ETH, BSC, TRX | KYC; travel rule | — |
| Tokocrypto | tokocrypto.com | Indonesia | Top 150 | Binance-linked networks | KYC | Binance-affiliated. |
| Pintu | pintu.co.id | Indonesia | Top 200 | ETH, BSC, SOL, POL | KYC | — |
| Reku | reku.id | Indonesia | Top 200 | ETH, BSC, TRX | KYC | — |
| Coins.ph | coins.ph | Philippines | Top 200 | ETH, BSC, SOL, TRX, POL | KYC | — |
| PDAX | pdax.ph | Philippines | Top 200 | ETH, BTC | KYC | — |
| CoinDCX | coindcx.com | India | Top 100 | ETH, BSC, POL, SOL, TRX | KYC; 1% TDS on transfers in India | Internal operational account hacked July 2025 ($44M); user funds covered. |
| WazirX | wazirx.com | India | Top 150 | ETH, BSC, TRX, POL | KYC | Relaunched 24 Oct 2025 after the 2024 hack and Singapore restructuring. |
| CoinSwitch | coinswitch.co | India | Top 200 | ETH, BSC, POL, TRX | KYC; TDS | — |
| ZebPay | zebpay.com | India | Top 200 | ETH, BTC, POL, TRX | KYC; TDS | — |
| Mudrex | mudrex.com | India | Top 200 | ETH, POL, TRX | KYC; TDS | — |
| Giottus | giottus.com | India | Top 200 | ETH, BSC, TRX | KYC; TDS | — |
| Delta Exchange | delta.exchange | India (derivatives) | Top 150 | ETH, TRX, BSC | KYC | — |

### 5.3 Turkey, Middle East & Africa

| Exchange | Website | Country | Tier | Networks | Withdrawal rules | Notes |
|---|---|---|---|---|---|---|
| Binance TR | binance.tr | Türkiye | Top 60 | Subset of Binance | Turkish KYC; MASAK travel-rule rules | — |
| BtcTurk | btcturk.com | Türkiye | Top 60 | ETH, AVAX, SOL, TRX ◐ | KYC; MASAK rules | Hot-wallet hacks in 2024 ($55M) and 2025 (~$49M). |
| Paribu | paribu.com | Türkiye | Top 80 | ETH, AVAX, SOL, TRX ◐ | KYC; MASAK rules | — |
| OKX TR | tr.okx.com | Türkiye | Top 150 | Subset of OKX | KYC; MASAK rules | — |
| CoinTR | cointr.com | Türkiye | Top 200 | ETH, TRX, BSC | KYC | — |
| Icrypex | icrypex.com | Türkiye | Top 200 | ETH, TRX | KYC | — |
| Bitlo | bitlo.com | Türkiye | Top 200 | ETH, TRX | KYC | — |
| Luno | luno.com | South Africa / Africa | Top 200 | BTC, ETH, SOL, XRP | KYC; SA travel rule (FIC) | — |
| VALR | valr.com | South Africa | Top 150 | ETH, SOL, TRX, BSC | KYC; FIC travel rule | — |
| Quidax | quidax.io | Nigeria | Top 200 | ETH, BSC, TRX | KYC | — |

### 5.4 Europe

| Exchange | Website | Country | Tier | Networks | Withdrawal rules | Notes |
|---|---|---|---|---|---|---|
| Bitvavo | bitvavo.com | Netherlands | Top 50 | ETH, SOL, ARB, BASE ◐, POL ◐ | MiCA; TFR self-hosted proof above €1,000 | Largest EU-native exchange. |
| Bitpanda | bitpanda.com | Austria | Top 120 | ETH, SOL, POL ◐ | MiCA; TFR | — |
| One Trading | onetrading.com | Austria | Top 200 | ETH, SOL | MiCA; TFR | Ex-Bitpanda Pro. |
| Bit2Me | bit2me.com | Spain | Top 200 | ETH, BSC, POL, SOL ◐ | MiCA; TFR | — |
| Coinmetro | coinmetro.com | Estonia | Top 200 | ETH, XRP, XLM | TFR | — |
| LCX | lcx.com | Liechtenstein | Top 200 | ETH | TFR | — |
| Young Platform | youngplatform.com | Italy | Top 200 | ETH, POL | MiCA; TFR | — |
| Kanga | kanga.exchange | Poland | Top 200 | ETH, BSC | TFR | — |
| Kraken / Bitstamp / Coinbase / Crypto.com / OKX / Bybit EU entities | — | EU | Tier 1 | See Tier 1 | MiCA + TFR self-hosted wallet checks | — |

### 5.5 Americas & Oceania

| Exchange | Website | Country | Tier | Networks | Withdrawal rules | Notes |
|---|---|---|---|---|---|---|
| Binance.US | binance.us | USA | Top 120 | Subset of Binance (ETH, SOL, BSC ◐) | US KYC | — |
| Kraken / Coinbase / Gemini / Bitstamp | — | USA | Tier 1 | See Tier 1 | — | — |
| Bitso | bitso.com | Mexico / LatAm | Top 80 | ETH, SOL, TRX, POL, ARB ◐ | KYC | — |
| Mercado Bitcoin | mercadobitcoin.com.br | Brazil | Top 120 | ETH, SOL, POL ◐ | KYC; Brazilian travel-rule rules | — |
| Foxbit | foxbit.com.br | Brazil | Top 200 | ETH, BSC, TRX | KYC | — |
| NovaDAX | novadax.com.br | Brazil | Top 200 | ETH, BSC, TRX | KYC | — |
| Ripio | ripio.com | Argentina | Top 200 | ETH, BSC, POL | KYC | — |
| Buenbit | buenbit.com | Argentina | Top 200 | ETH, BSC, TRX | KYC | — |
| Independent Reserve | independentreserve.com | Australia / SG | Top 200 | ETH, SOL, BTC | AUSTRAC KYC | — |
| CoinSpot | coinspot.com.au | Australia | Top 200 | ETH, BSC, SOL, TRX | AUSTRAC KYC | — |
| Swyftx | swyftx.com | Australia | Top 200 | ETH, BSC, SOL | AUSTRAC KYC | — |
| BTC Markets | btcmarkets.net | Australia | Top 200 | ETH, SOL | AUSTRAC KYC | — |
| CoinJar | coinjar.com | Australia / UK | Top 200 | ETH, SOL | KYC | — |

---

## 6. Closed, winding down, or sanctioned in 2025–2026 (do not use for new deposits)

| Exchange | Status | Key dates | Withdrawal situation |
|---|---|---|---|
| **AscendEX** (ex-BitMax) | Ceased operations | 1 Jul 2026 (missed MiCA authorisation; failed deal) | Reported reserves near zero; user funds in limbo. |
| **BitMEX** | Closed | Announced 23 Jul 2026; ceased 23 Sep 2026 04:00 UTC | Owner HDR stated user assets were safe; withdraw if anything remains. |
| **BitMart** | Phased wind-down | Announced 26 Jul 2026; full termination **31 Jan 2027, 15:59 UTC** | Withdrawals open until then. |
| **CoinEx** | Closing | Announced 14 Sep 2026; spot delisted 29 Sep; **withdrawals close 22 Dec 2026** | Withdraw before the deadline. |
| **EXMO** | Wound down after UK sanctions (asset freeze 26 May 2026) | Jul 2026 | 29.4% balance shortfall swapped into a non-withdrawable IOU token (USDRecover). |
| **Bit.com** | Closed | Three-phase shutdown 27 Dec 2025 – 31 Mar 2026 | Funds could move to Matrixport. |
| **Knaken** (NL) | Bankrupt | Offline June 2026; bankrupt 16 Jul 2026 | About €7M of client funds missing. |
| **Zondacrypto** (ex-BitBay) | Reported bankrupt | 27 Aug 2026 (single secondary source) | Verify with the trustee. |
| **Gemini — UK/EU/AU** | Regional exit | Withdrawal-only 5 Mar 2026; closed 6 Apr 2026 | US/SG accounts unaffected. |
| **HTX** | Operating, but **sanctioned by the UK and EU** | UK May 2026; EU from 23 Aug 2026 | Counterparties apply enhanced review; Upbit blocks withdrawals to HTX. |
| **DMM Bitcoin** (JP) | Closed after 2024 hack | Accounts moved to SBI VC Trade (2025) | — |

---

## 7. Practical takeaways for a Base-focused project

- **Base (chain ID 8453) withdrawals are supported directly** by Coinbase, Binance, OKX, Bybit, Bitget, Gate, KuCoin, MEXC, BingX, Crypto.com and Kraken. Smaller venues often support only ETH mainnet or BSC/TRX, so their users may need to bridge.
- If you expect users to fund wallets from an exchange, tell them to **select the Base network explicitly**. Withdrawing ETH on Ethereum mainnet to a Base address arrives on mainnet, not Base.
- **EU users** sending more than €1,000 to a fresh self-custody wallet will be asked to prove they own it. **Korean and Japanese users** may be limited to registered wallets.

---

## Sources

- CryptoRank — Crypto Exchange Q2 2026 Recap: https://cryptorank.io/insights/reports/crypto-exchange-q2-2026
- CryptoRank — April 2026 CEX spot volume recap: https://cryptorank.io/insights/reports/april-2026-cex-spot-volume-recap
- TokenInsight — Crypto Exchange Report Q2 2026: https://tokeninsight.com/en/research/reports/crypto-exchange-report-q2-2026
- CoinGecko — CEX market share research: https://www.coingecko.com/research/publications/centralized-crypto-exchanges-market-share
- CoinGecko (Threads) — Top 12 CEXs by spot volume: https://www.threads.com/@coingecko/post/DXItEXnlUcY/
- cryptonews.net — Binance 38.7% of top-10 spot volume: https://cryptonews.net/news/market/33189312/
- CoinLaw — Exchange ranking 2026: https://coinlaw.io/crypto-exchange-ranking/
- CNBC — BitMEX to shut down: https://www.cnbc.com/2026/07/23/cryptocurrency-exchange-bitmex-shut-down.html
- CoinDesk — BitMEX closure: https://www.coindesk.com/markets/2026/07/23/bitmex-s-11-year-run-comes-to-an-end-notifies-users-it-is-ending-operations-in-by-sept-23
- Decrypt — CoinEx shutting down: https://decrypt.co/378324/coinex-shutting-down
- CryptoTimes — CoinEx withdrawals until 22 Dec 2026: https://www.cryptotimes.io/2026/09/15/coinex-announces-shutdown-after-9-years-withdrawals-open-until-december-22-2026/
- GitHub release (Ricosworks1) — Nine exchanges shut down in 2026: https://github.com/Ricosworks1/blockchain-payment-flow-analysis/releases/tag/market-update-nine-exchanges-shut-down-bitmex-dies-sept-2026
- Gemini support — closing UK/EU/AU accounts: https://support.gemini.com/hc/en-us/articles/46255474469275
- Phemex News — Bit.com shutdown: https://phemex.com/news/article/bitcom-to-cease-operations-by-march-31-2026-in-threephase-shutdown-49437
- Finance Magnates — EXMO wind-down: https://www.financemagnates.com/cryptocurrency/exmo-pulls-the-plug-sanctioned-crypto-exchange-winds-down-leaves-users-holding-iou-tokens/
- NL Times — Knaken bankrupt: https://nltimes.nl/2026/07/16/crypto-trading-platform-knaken-declared-bankrupt-eu7-million-customer-funds-missing
- BeInCrypto — HTX UK sanctions: https://beincrypto.com/htx-fca-settlement-uk-users/
- Traders Union — EU sanctions on HTX from 23 Aug: https://tradersunion.com/news/cryptocurrency-news/show/2792304-eu-sanctions-bar-htx-transactions/
- Protos — HTX reserves at Poloniex: https://protos.com/we-found-htxs-reserves-at-poloniex/
- The Block — India FIU notice to 15 platforms: https://www.theblock.co/news/regulation/2026-09-09-india-seeks-takedowns-of-15-crypto-platforms-over-aml-compliance-413975
- Bybit Help Center — withdrawal security / address book: https://www.bybit.com/en/help-center/article/How-to-Manage-Your-Withdrawal-Security
- Bankless Times — Binance Withdraw Protection: https://www.banklesstimes.com/articles/2026/05/04/binance-rolls-out-withdrawal-lock-to-curb-wrench-attacks-on-crypto-holders/
- Coinbase CDP — Exchange changelog (EVM-wide address book): https://docs.cdp.coinbase.com/exchange/changes/changelog
- Coinbase CDP — Prime withdrawals & address book: https://docs.cdp.coinbase.com/prime/concepts/transactions/withdrawals
- Kraken support — withdrawing crypto: https://support.kraken.com/articles/360000672763-how-to-withdraw-cryptocurrencies-from-your-kraken-account
- Deribit API — per-address security key: https://docs.deribit.com/api-reference/wallet/private-set_address_requires_security_key.md
- WhiteBIT docs — travel rule: https://docs.whitebit.com/concepts/travel-rule
- Notabene — EU TFR self-hosted wallet requirements: https://notabene.id/post/a-deep-dive-into-self-hosted-wallet-transaction-requirements-under-the-eu-tfr
- 21 Analytics — TFR user guide: https://www.21analytics.co/tfr-user-guide/
- Bitcoinist — Bithumb unverified wallets: https://bitcoinist.com/bithumb-to-not-accept-withdrawals-for-unverified-wallets/amp/
- Finance Magnates — Coinone halts unverified wallet withdrawals: https://www.financemagnates.com/cryptocurrency/coinone-to-halt-withdrawal-services-to-unverified-external-wallets/
- fnnews — Korea amended act effective 20 Aug 2026: https://en.fnnews.com/news/202606291314347636
- Cointelegraph — bitFlyer travel rule: https://regional-front.cointelegraph.com/news/bitflyer-adopts-crypto-deposit-limits-to-comply-with-travel-rule
- Benzinga — bitFlyer self-custody still allowed: https://www.benzinga.com/amp/content/32633626
- Edgex — MEXC KYC tiers 2026: https://pro.edgex.exchange/en-US/news/article/mexc-kyc-verification-tiers-withdrawal-limits
- Edgex — Gate KYC: https://pro.edgex.exchange/en-US/news/article/gate-io-kyc-requirements-verification-tiers
- FinanceFeeds — Bitget mandatory KYC: https://financefeeds.com/bitget-implements-mandatory-kyc-and-daily-withdrawal-limit-of-up-to-3-million/
- Blockworks — KuCoin mandatory KYC: https://blockworks.co/news/kucoin-enforces-kyc-verification
- Coinspectator — CEX hack losses 2025–26: https://coinspectator.com/mainstream/2026/03/09/crypto-exchanges-lost-2-4-billion-to-hacks-in-just-over-a-year-71-came-from-a-single-incident/
- Cointelegraph — Bybit comeback after 2025 hack: https://cointelegraph.com/news/bybit-slow-steady-comeback-after-2025-hack-coingecko
- CryptoSlate — Gate.com rebrand: https://cryptoslate.com/press-releases/gate-introduces-brand-new-domain-gate-com-and-brand-logo-advancing-toward-the-next-generation-crypto-exchange/
- The Block — Coinbase completes Deribit acquisition: https://www.theblock.co/post/366957/coinbase-completes-2-9-billion-cash-and-stock-acquisition-of-deribit
- The Block — Robinhood completes Bitstamp acquisition: https://www.theblock.co/news/deals/2025-06-03-robinhood-bitstamp-acquisition-356701
- Business Standard — WazirX relaunch: https://www.business-standard.com/markets/cryptocurrency/wazirx-to-resume-operations-in-india-on-oct-24-here-s-all-you-need-to-know-125102300424_1.html
