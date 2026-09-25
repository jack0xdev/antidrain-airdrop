# IctObBot: Order Block bot (LuxAlgo ICT Concepts logic → MT5)

> **License:** OB detection logic ta LuxAlgo er "ICT Concepts" indicator theke port kora.
> Original code **CC BY-NC-SA 4.0**, tai ei bot o **same license** e:
> LuxAlgo ke credit dite hobe, **bikri/commercial use kora jabe na**, ar share korle same license e korte hobe.

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

## Bot ki kore

- LuxAlgo er OB logic hubohu port kora: swing (lookback 10), use body, OB = swing ar breakout er
  majhe lowest-body candle, breaker (body OB er opor dike close korle), breaker remove.
- Chart e OB box, "shown" dot, status (`FRESH / PENDING / USED / MITIGATED / BREAKER`) ar lag dekhay.
- Entry mode:
  - **`ENTRY_LIMIT`** (default): OB detect howar sathe sathe OB er edge e (ba 50% e) limit order.
    OB breaker hole, notun OB ashle, ba `InpExpiryBars` par hole order cancel.
  - **`ENTRY_CONFIRM`**: price OB te touch kore rejection candle (bullish OB te bullish close OB er upore) dile market entry.
  - **`ENTRY_OFF`**: trade nei, shudhu detect, draw ar log. **Prothome eta diye TradingView er sathe mile kina check korun.**
- SL: OB er opor pashe + ATR buffer (minimum 0.5 ATR, OB 3 ATR er beshi boro hole skip). TP: RR x risk (default 2R). 1R e break-even.
- Filter: session hour (server time), high-impact USD news er ±15 min e notun entry nei, max position 1.

## Install ar test

1. `IctObBot.mq5` ke `MQL5\Experts` e copy korun, MetaEditor e **F7** diye compile korun. Error ashle amake pathan.
2. XAUUSD chart e din (M5/M15 bhalo shuru). Prothome **`InpEntryMode = ENTRY_OFF`** rakhun.
3. Same symbol/TF e TradingView e LuxAlgo lagan (Swing Lookback 10, Use Candle Body ON). Latest OB duitai mile kina dekhun.
   Broker ar TradingView er data (ar timezone) alada holey candle ektu alada hoy, tai choto difference normal.
4. **Strategy Tester:** "Every tick based on real ticks", XAUUSD, 3–6 mash. Tester e news filter kaj kore na.
5. Demo te 3–4 shoptaho chalan, tarpor real er kotha bhabun.

## Main settings

| Input | Default | Mane |
|---|---|---|
| `InpTF` | current | Kon timeframe er OB |
| `InpSwingLength` | 10 | LuxAlgo "Swing Lookback". Komale OB taratari ashe kintu beshi noise. |
| `InpUseBody` | true | LuxAlgo "Use Candle Body" |
| `InpEntryMode` | LIMIT | LIMIT / CONFIRM / OFF |
| `InpEntryLevel` | EDGE | OB er edge na 50% e limit |
| `InpTradeLastN` | 1 | Shudhu newest OB trade (LuxAlgo o 1 ta dekhay) |
| `InpExpiryBars` | 50 | Eto candle er moddhe entry na hole bad |
| `InpRR` | 2.0 | TP = 2 x risk |
| `InpRiskPercent` | 0 | 0 = fixed `InpLots`; 1 = balance er 1% risk |
| `InpNewsBlockMin` | 15 | News er ±15 min e entry nei |

## Risk

Order block kono guaranteed setup na. Onek OB breaker hoye jay (SL hit). Kono indicator ba bot
profit guarantee kore na. Tester ar demo te positive result na dekhe real money diben na.
