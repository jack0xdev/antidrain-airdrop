# GoldNewsTrader: MT5 Gold (XAUUSD) News EA

## Age ekta shotti kotha

News er number (NFP, CPI, FOMC...) release howar age keu jane na, broker o na, bank o na.
Tai **1 minute age gold up hobe na down hobe, eta 100% predict kora possible na.** Je EA/signal
seller "guaranteed prediction" bole, se mitha bolche.

Ei EA tai 3 ta kaj kore:

1. **1 minute age ekta bias score dey** (−100 theke +100, UP / DOWN / NEUTRAL). Eta ekta
   probability-style guess, guarantee na.
2. **Emon trade mode dey jekhane prediction lagbe na.** Straddle mode e dui dikei order thake, ar
   Deviation mode e actual number release er por trade hoy.
3. **Nijer accuracy nije mape.** Protita news er por CSV te likhe rakhe prediction thik chilo na
   bhul, ar chart e dekhay: `Measured accuracy: 14/25 = 56%`.

## Bias score kivabe hoy (news er 60 second age)

| Component | Ki dekhe | Default weight |
|---|---|---|
| Pre-news drift | Last 15 min e gold koto uthlo/namlo (ATR diye normalize) | 0.35 |
| Tick flow | Last 90 sec e up-tick vs down-tick | 0.30 |
| USD proxy | EURUSD er move (EURUSD up = USD weak = gold up) | 0.20 |
| Consensus | Forecast vs previous (market age thekei eta price kore rakhe, tai weak) | 0.15 |

Score ≥ +25 hole **UP**, ≤ −25 hole **DOWN**, majhe thakle **NEUTRAL** (kono call nei).

## Modes

| Mode | Ki kore | Prediction lage? |
|---|---|---|
| `MODE_SIGNAL_ONLY` (default) | Shudhu alert, phone push ar log. Kono trade nei. | – |
| `MODE_STRADDLE` | 60s age Buy Stop (+$1.5) ar Sell Stop (−$1.5) boshay. Ekta fill hole arekta auto delete (OCO). | Na |
| `MODE_BIAS` | Shudhu predicted dike ekta pending order. | Haa (risky) |
| `MODE_DEVIATION` | MT5 calendar e actual number ashle actual vs forecast dekhe: USD strong mane gold SELL, USD weak mane gold BUY. | Na, kintu speed lage |

Shob mode e thake: SL/TP, break-even, trailing stop, max hold time (default 15 min), spread
filter, ar risk % lot size.

## Install

1. MT5 e **File → Open Data Folder → MQL5 → Experts** e `GoldNewsTrader.mq5` copy korun.
2. MetaEditor e file ta open kore **F7** (Compile) chapun. Error ashle amake error ta pathan.
3. MT5 e **Toolbox → Calendar** tab ekbar open korun, jeno calendar data load hoy.
4. **XAUUSD** chart e (je kono timeframe) EA drag korun, ar **Algo Trading** ON korun.
5. Phone e alert chaile: **Tools → Options → Notifications** e MetaQuotes ID din, ar `InpPush = true` korun.

## Kivabe use korben (recommended)

1. **Prothom 4–8 shoptaho `MODE_SIGNAL_ONLY` e rakhun.** Trade hobe na, shudhu log hobe.
2. Log file ekhane: `File → Open Data Folder → ..\Common\Files\GoldNewsLog.csv`.
   Chart e `Measured accuracy` dekhun.
3. Jodi accuracy **20+ news e o ~50–55% er upore na jay**, tahole bias diye trade korben na.
   Tokhon `MODE_STRADDLE` ba `MODE_DEVIATION` **demo account e** test korun.
4. Real account e jaoar age demo te positive result na dekhle jaben na.

## Important settings

| Input | Default | Mane |
|---|---|---|
| `InpCurrency` | USD | Kon currency er news |
| `InpMinImportance` | HIGH | Shudhu high-impact news |
| `InpKeywords` | (khali) | Jemon `nonfarm,cpi,interest rate,fomc,gdp`. Khali rakhle shob high-impact news. |
| `InpSecondsBefore` | 60 | Koto second age signal/order |
| `InpBiasThreshold` | 25 | Score er koto upore gele UP/DOWN call hobe |
| `InpEntryDist` | 1.50 | Pending order price theke koto dure ($) |
| `InpStopLoss` / `InpTakeProfit` | 2.50 / 8.00 | $ e |
| `InpMaxSpread` | 1.00 | Spread er beshi hole order hobe na |
| `InpRiskPercent` | 0 | 0 mane fixed lot (`InpLots`); 1 mane balance er 1% risk |

Distance gulo **price e** (gold e 1.50 = $1.50), points e na. 0.01 lot e $1 move ≈ $1 profit/loss.

## Strategy Tester (backtest)

MT5 tester e economic calendar kaj kore na. Tai:

- `InpManualTimes` e news time din, **broker server time** e. Jemon:
  `2026.08.07 15:30;2026.09.05 15:30`
  (NFP New York 8:30 hoy, ja beshirbhag GMT+2/+3 broker e 15:30.)
- Model: **Every tick based on real ticks.**
- Tester e Deviation mode kaj korbe na (actual/forecast data nei).

## Risk (obosshoi porun)

- News er somoy gold er **spread 5–20x bere jay**, ar **slippage** e SL er cheye onek beshi loss hote pare.
- Straddle e **whipsaw** hoy: dui dike spike hole dui order-i fill hoye dui dike loss hote pare.
- Deviation mode e MT5 calendar actual value ashte **kichu second deri** hoy, tokhon price already move kore felte pare.
- Onek broker ar **prop firm (FTMO etc.) news trading ban kore**. Rules check korun.
- Ei EA kono profit guarantee kore na. Demo te test na kore real money diben na.
