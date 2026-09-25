# IctObBot: OB Sweep bot (LuxAlgo ICT Concepts logic → MT5)

> **License:** OB detection logic ta LuxAlgo er "ICT Concepts" indicator theke port kora.
> Original code **CC BY-NC-SA 4.0**, tai ei bot o **same license** e:
> LuxAlgo ke credit dite hobe, **bikri/commercial use kora jabe na**, ar share korle same license e korte hobe.

## Strategy: OB sweep entry (default)

**Bearish OB → SELL**

```
        ┃  <- sweep candle er HIGH = SL
        ┃
 ───────╂──────── OB top
 ▓▓▓▓▓▓▓█▓▓▓▓▓▓▓  bearish OB
 ▓▓▓▓▓▓▓█▓▓▓▓▓▓▓  <- candle OB top er NICHE close -> candle close hole SELL
 ─────────────── OB bottom
```

**Bullish OB → BUY** (ulta)

```
 ─────────────── OB top
 ▓▓▓▓▓▓▓█▓▓▓▓▓▓▓  <- candle OB bottom er UPORE close -> candle close hole BUY
 ▓▓▓▓▓▓▓█▓▓▓▓▓▓▓  bullish OB
 ───────╂──────── OB bottom
        ┃
        ┃  <- sweep candle er LOW = SL
```

1. **Sweep:** candle er wick OB er baire jay, kintu candle abar OB er dike **close** kore.
2. **Entry:** oi candle close hoyar sathe sathe market order.
3. **SL:** sweep candle er **high** (sell) ba **low** (buy). Sell e spread o jog hoy, jeno spread er karone SL hit na hoy.
4. **TP:** `InpRR` x risk (default 2R). `InpRR = 0` dile TP nei.
5. **Re-entry:** SL hit hole, same OB abar sweep hole abar entry. **Ek OB e maximum 3 bar** (`InpMaxEntries`).
   - SL hit kora candle nijei jodi abar OB er dike close kore, sheta-i porer sweep, tai sathe sathe re-entry hoy.
   - Kono trade TP te profit e close hole oi OB shesh (`InpReentryAfterWin = false`).
   - Kono candle er **body** OB er opor pashe close korle OB break (breaker), tokhon ar entry nei (`InpStopOnBreaker = true`).
   - Ek somoy ekta-i trade (`InpMaxPositions = 1`). Ager trade close na hole notun entry nei.
6. **Timeframe:** `InpTF` e **1m / 5m / 10m / 15m / 30m / 1h** theke je ta select korben, bot shudhu oi TF er candle e OB ar sweep khujbe. Chart je TF e-i thakuk, kono shomossha nei.

Bot restart hole ba setting change korle entry count harabe na. Trade er comment (`OBsw B 2026.09.25 10:05 #2`) theke abar gune ney.

Chart e protita OB er pashe status dekhay: `WAIT SWEEP 1/3`, `IN TRADE 2/3`, `DONE 3/3`, `WON`, `BREAKER`.

## OB detect hoye show hote koto time lage?

LuxAlgo te **Swing Lookback = 10** (default). OB 2 dhape ashe:

**Dhap 1: swing high confirm hote 10 ta candle lage.**
Kono high tokhon-i "swing high" hoy jokhon tar **porer 10 ta candle** er kono ta oi high er upore na jay.
Mane swing high candle er por 10 ta candle close na hoya porjonto indicator jane-i na je eta swing high.

**Dhap 2: kono candle swing high er upore CLOSE korle tokhon OB ashe.**
Bullish OB tokhon-i toiri hoy jokhon ekta candle oi swing high er **upore close** kore (bearish OB er khetre swing low er niche).
Tarpor swing high ar breakout candle er majhe **sobcheye low body wala candle** ta ke OB dhora hoy.

| | Koto candle |
|---|---|
| Swing high theke OB show (minimum) | **11 candle** (10 confirm + 1 breakout close) |
| Swing high theke OB show (maximum) | Kono limit nei. Breakout jokhon hobe tokhon. |
| OB candle theke OB show | Kom kore 1 candle, beshirbhag somoy **onek candle** (swing er por OB candle, tarpor breakout) |
| Breakout candle close er por | **0**, sathe sathe ashe |

Timeframe onujayi **minimum** time (swing high candle theke):

| TF | Minimum |
|---|---|
| M1 | 11 min |
| M5 | 55 min |
| M15 | 2 ghonta 45 min |
| H1 | 11 ghonta |

### 3 ta jinish bot banate hole obosshoi mathay rakhben

1. **Repaint (TradingView live chart e):** script protita tick e chole. Tai candle cholakalin price
   swing high er upore gele OB **candle er majhkhane-i dekha dite pare**, ar candle niche close
   korle **abar vanish** hoye jay. Confirm OB shudhu **candle close er por**. Ei bot shudhu close
   hoye jaoa candle use kore, tai repaint nei.
2. **Chart dekhe dhoka:** OB box ta **ager** candle e draw hoy (OB candle e), kintu OB ta ashe
   **pore** (breakout close e). Chart e dekhben price OB te touch kore uthe geche, "perfect entry".
   Kintu oi touch ta hoyto OB ashar **age-i** hoyeche, tokhon bot er jana-i chilo na. Tai chart dekhe
   backtest korle result mitha rokom bhalo dekhabe. Ei bot chart e ekta **dot** diye dekhay OB asole
   kokhon ashlo.
3. **Present mode:** LuxAlgo "Present" mode e shudhu **last 500 candle** e OB khoje. Tai onek purono
   OB TradingView ar ei bot e ektu alada hote pare. Latest OB same thakbe.

Real lag ta ei bot nije mepe dekhay: chart panel e (median/avg/min/max) ar
`Common\Files\ob_detections.csv` e protita OB er OB candle, swing, breakout time ar lag.

## Onno entry mode (optional)

| `InpEntryMode` | Ki kore |
|---|---|
| `ENTRY_SWEEP` (default) | Upore bola OB sweep strategy |
| `ENTRY_LIMIT` | OB detect hole OB er edge (ba 50%) e limit order |
| `ENTRY_CONFIRM` | OB te touch kore rejection candle dile entry |
| `ENTRY_OFF` | Trade nei, shudhu OB detect, draw ar log. TradingView er sathe milano ba test er jonno. |

## Install ar test

1. `IctObBot.mq5` ke `MQL5\Experts` e copy korun, MetaEditor e **F7** diye compile korun. Error ashle amake pathan.
2. XAUUSD chart e din, `InpTF` e timeframe select korun.
3. Prothome `InpEntryMode = ENTRY_OFF` diye TradingView er LuxAlgo er sathe OB mile kina dekhun
   (Swing Lookback 10, Use Candle Body ON, same TF). Broker ar TradingView er data alada, tai choto difference normal.
4. **Strategy Tester:** "Every tick based on real ticks", XAUUSD, 3–6 mash, protita TF alada test korun.
   Tester e news filter kaj kore na.
5. Demo te 3–4 shoptaho chalan, tarpor real er kotha bhabun.

## Main settings

| Input | Default | Mane |
|---|---|---|
| `InpTF` | 5m | 1m / 5m / 10m / 15m / 30m / 1h |
| `InpEntryMode` | SWEEP | Entry mode |
| `InpMaxEntries` | 3 | Ek OB e max koto bar entry (SL hit er por re-entry) |
| `InpStopOnBreaker` | true | Body OB er opor pashe close korle OB bad |
| `InpReentryAfterWin` | false | Profit hoyar por o oi OB e entry nibe kina |
| `InpTradeLastN` | 1 | Shudhu newest OB (protita side e). Notun OB ashle purono ta bad. 2 dile 2 ta. |
| `InpRR` | 2.0 | TP = 2 x risk (0 = TP nei) |
| `InpSLBufferATR` | 0 | SL sweep high/low er aro koto dure (ATR x). 0 = thik high/low e. |
| `InpMaxRiskATR` | 0 | Sweep candle onek boro hole skip (jemon 3 = 3 ATR er beshi SL hole skip). 0 = off |
| `InpLots` / `InpRiskPercent` | 0.01 / 0 | Fixed lot, ba balance er % risk (SL onujayi lot hisab) |
| `InpMaxSpread` | 0.50 | Er beshi spread hole entry nei |
| `InpStartHour` / `InpEndHour` | 0 / 24 | Kon ghonta theke kon ghonta trade (server time) |
| `InpNewsBlockMin` | 15 | High-impact USD news er ±15 min e entry nei |
| `InpSwingLength` | 10 | LuxAlgo "Swing Lookback" |

**Tip:** sweep candle onek boro hole SL o boro hoy. Fixed lot e loss beshi hobe. `InpRiskPercent = 1`
dile protita trade e balance er 1% risk hobe, SL choto ba boro jai hok.

## Risk

3 bar re-entry mane ek OB e **3 ta SL porjonto** hote pare. Order block kono guaranteed setup na.
Kono indicator ba bot profit guarantee kore na. Tester ar demo te positive result na dekhe real money diben na.
