//+------------------------------------------------------------------+
//|                                               GoldNewsTrader.mq5 |
//|  XAUUSD news EA for MetaTrader 5                                 |
//|   - Finds high-impact USD news from the built-in MT5 calendar    |
//|   - 60 s before release: computes an UP/DOWN bias score          |
//|   - Modes: signal only / straddle (OCO) / bias / deviation       |
//|   - Logs every prediction vs. the real move, shows accuracy      |
//|                                                                  |
//|  WARNING: the direction of a news spike cannot be known before   |
//|  the number is released. The bias score is a probability-style   |
//|  guess, not a certainty. Test on demo first.                     |
//+------------------------------------------------------------------+
#property copyright "GoldNewsTrader"
#property version   "1.00"
#property description "Gold (XAUUSD) news EA: pre-news bias score, straddle, deviation entry, accuracy log."
#property description "News direction cannot be known before release - use on demo first."

#include <Trade\Trade.mqh>

enum ENUM_NEWS_MODE
  {
   MODE_SIGNAL_ONLY = 0, // Signal only (no trades: alert + log)
   MODE_STRADDLE    = 1, // Straddle: Buy Stop + Sell Stop (OCO)
   MODE_BIAS        = 2, // Bias: one pending order in predicted direction
   MODE_DEVIATION   = 3  // Deviation: market order after actual vs forecast
  };

//--- inputs
input group "=== News source ==="
input string   InpCurrency       = "USD";                    // Calendar currency
input ENUM_CALENDAR_EVENT_IMPORTANCE InpMinImportance = CALENDAR_IMPORTANCE_HIGH; // Minimum importance
input string   InpKeywords       = "";                       // Only events containing (comma list, empty = all)
input int      InpLookaheadHours = 48;                       // Calendar look-ahead (hours)
input string   InpManualTimes    = "";                       // Manual news times (server) "yyyy.mm.dd hh:mi;..." for tester

input group "=== Mode & timing ==="
input ENUM_NEWS_MODE InpMode     = MODE_SIGNAL_ONLY;         // Mode
input int      InpSecondsBefore  = 60;                       // Signal / pending placement: seconds before news
input int      InpPendingLifeSec = 120;                      // Delete unfilled pendings N sec after news
input int      InpDevMaxWaitSec  = 20;                       // Deviation: max seconds to wait for actual value
input int      InpBiasThreshold  = 25;                       // Min |score| to call a direction (0-100)

input group "=== Bias score (prediction) ==="
input int      InpDriftMinutes   = 15;                       // Pre-news drift lookback (M1 bars)
input int      InpTickWindowSec  = 90;                       // Tick-flow window (seconds)
input string   InpUsdProxy       = "EURUSD";                 // USD proxy symbol (empty = off)
input double   InpWDrift         = 0.35;                     // Weight: pre-news drift
input double   InpWTicks         = 0.30;                     // Weight: tick flow
input double   InpWUsd           = 0.20;                     // Weight: USD proxy
input double   InpWConsensus     = 0.15;                     // Weight: forecast vs previous

input group "=== Orders (distances in price: 1.50 = $1.50 on gold) ==="
input double   InpLots           = 0.01;                     // Fixed lots
input double   InpRiskPercent    = 0.0;                      // Risk % of balance per trade (0 = fixed lots)
input double   InpEntryDist      = 1.50;                     // Pending distance from price
input double   InpEntryATRMult   = 0.0;                      // Or ATR(M1) x mult if larger (0 = off)
input double   InpStopLoss       = 2.50;                     // Stop loss
input double   InpTakeProfit     = 8.00;                     // Take profit (0 = none)
input double   InpBreakEven      = 1.50;                     // Move SL to entry after this profit (0 = off)
input double   InpBreakEvenLock  = 0.20;                     // Profit locked at break-even
input double   InpTrailStart     = 3.00;                     // Start trailing after this profit (0 = off)
input double   InpTrailDist      = 1.50;                     // Trailing distance
input int      InpMaxHoldMin     = 15;                       // Close position after N minutes (0 = off)
input double   InpMaxSpread      = 1.00;                     // Max spread to open (price)
input int      InpSlippagePts    = 100;                      // Max slippage (points)
input ulong    InpMagic          = 26092501;                 // Magic number

input group "=== Alerts & log ==="
input bool     InpAlert          = true;                     // Terminal alert
input bool     InpPush           = false;                    // Push notification to phone
input bool     InpWriteLog       = true;                     // Log predictions to CSV (Common\Files)
input string   InpLogFile        = "GoldNewsLog.csv";        // Log file name

//--- state
CTrade   g_trade;
bool     g_useManual  = false;

datetime g_newsTime   = 0;       // release time (trade server time)
string   g_newsTitle  = "";
ulong    g_valueIds[];           // calendar value ids released at g_newsTime
string   g_eventNames[];
datetime g_lastLoad   = 0;

bool     g_signalDone = false;
bool     g_released   = false;
bool     g_devDone    = false;
bool     g_logged     = false;

double   g_score  = 0;
int      g_predDir = 0;          // +1 up, -1 down, 0 no call
double   g_cDrift = 0, g_cTicks = 0, g_cUsd = 0, g_cCons = 0;
double   g_pSignal = 0, g_pRelease = 0, g_p60 = 0, g_p300 = 0;

int      g_statTotal = 0;
int      g_statHits  = 0;
string   g_lastResult = "";

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpSlippagePts);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("Warning: this EA is designed for gold (XAUUSD). Current symbol: ", _Symbol);

   bool tester = (MQLInfoInteger(MQL_TESTER) != 0);
   g_useManual = (StringLen(InpManualTimes) > 0 || tester);
   if(tester && StringLen(InpManualTimes) == 0)
      Print("Strategy tester has no economic calendar. Put news times into InpManualTimes.");
   if(g_useManual && InpMode == MODE_DEVIATION)
      Print("Deviation mode needs the live calendar (actual/forecast). Manual times cannot trade it.");

   if(InpUsdProxy != "" && !SymbolSelect(InpUsdProxy, true))
      Print("USD proxy symbol not found: ", InpUsdProxy, " (USD component disabled)");

   if(tester && InpWriteLog)
      FileDelete(LogName(), FILE_COMMON);
   LoadStats();

   EventSetMillisecondTimer(250);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   ManagePositions();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   datetime now = TimeTradeServer();

   if(!g_signalDone && (g_lastLoad == 0 || now - g_lastLoad >= 30))
      LoadNextNews(now);

   if(g_newsTime > 0)
      ProcessNews(now);

   if(CountPositions() > 0 && CountPendings() > 0)
      DeletePendings();   // OCO safety net

   ManagePositions();
   UpdatePanel(now);
  }

//+------------------------------------------------------------------+
//| OCO: as soon as one pending order fills, delete the other        |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.symbol != _Symbol)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   if((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic)
      return;
   if(HistoryDealGetInteger(trans.deal, DEAL_ENTRY) != DEAL_ENTRY_IN)
      return;
   DeletePendings();
  }

//+------------------------------------------------------------------+
//| Find the next news release (calendar or manual list)             |
//+------------------------------------------------------------------+
void LoadNextNews(datetime now)
  {
   g_lastLoad = now;
   datetime best  = 0;
   string   title = "";
   ArrayResize(g_valueIds, 0);
   ArrayResize(g_eventNames, 0);

   if(g_useManual)
     {
      string parts[];
      int n = StringSplit(InpManualTimes, ';', parts);
      for(int i = 0; i < n; i++)
        {
         string s = parts[i];
         StringTrimLeft(s);
         StringTrimRight(s);
         if(s == "")
            continue;
         datetime t = StringToTime(s);
         if(t <= now + 5)
            continue;
         if(best == 0 || t < best)
            best = t;
        }
      title = "Manual news time";
     }
   else
     {
      MqlCalendarValue values[];
      int n = CalendarValueHistory(values, now, (datetime)(now + InpLookaheadHours * 3600), NULL, InpCurrency);
      for(int i = 0; i < n; i++)
        {
         if(values[i].time <= now + 5)
            continue;
         if(!EventPasses(values[i].event_id))
            continue;
         if(best == 0 || values[i].time < best)
            best = values[i].time;
        }
      // several releases often share one timestamp (e.g. NFP + unemployment + earnings)
      for(int i = 0; i < n && best > 0; i++)
        {
         if(values[i].time != best || !EventPasses(values[i].event_id))
            continue;
         MqlCalendarEvent ev;
         if(!CalendarEventById(values[i].event_id, ev))
            continue;
         int k = ArraySize(g_valueIds);
         ArrayResize(g_valueIds, k + 1);
         ArrayResize(g_eventNames, k + 1);
         g_valueIds[k]   = values[i].id;
         g_eventNames[k] = ev.name;
        }
      if(ArraySize(g_eventNames) > 0)
        {
         title = InpCurrency + " " + g_eventNames[0];
         if(ArraySize(g_eventNames) > 1)
            title += StringFormat(" (+%d more)", ArraySize(g_eventNames) - 1);
        }
     }

   if(best != g_newsTime && best > 0)
      Print("Next news: ", title, " at ", TimeToString(best, TIME_DATE | TIME_MINUTES), " (server time)");
   g_newsTime  = best;
   g_newsTitle = title;
  }

//+------------------------------------------------------------------+
bool EventPasses(ulong eventId)
  {
   MqlCalendarEvent ev;
   if(!CalendarEventById(eventId, ev))
      return false;
   if(ev.importance < InpMinImportance)
      return false;
   if(ev.time_mode != CALENDAR_TIMEMODE_DATETIME)   // skip all-day / tentative
      return false;
   return MatchKeywords(ev.name);
  }

//+------------------------------------------------------------------+
bool MatchKeywords(string name)
  {
   if(StringLen(InpKeywords) == 0)
      return true;
   string n = name;
   StringToLower(n);
   string keys[];
   int k = StringSplit(InpKeywords, ',', keys);
   for(int i = 0; i < k; i++)
     {
      string key = keys[i];
      StringTrimLeft(key);
      StringTrimRight(key);
      StringToLower(key);
      if(key != "" && StringFind(n, key) >= 0)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| News life-cycle: signal -> release -> +60s -> +5m -> log         |
//+------------------------------------------------------------------+
void ProcessNews(datetime now)
  {
   if(!g_signalDone && now >= g_newsTime - InpSecondsBefore)
      FireSignal(now);

   if(g_signalDone && !g_released && now >= g_newsTime)
     {
      g_released = true;
      g_pRelease = Mid();
     }

   if(InpMode == MODE_DEVIATION && g_released && !g_devDone)
      CheckDeviation(now);

   if(g_released && g_p60 == 0 && now >= g_newsTime + 60)
      g_p60 = Mid();

   if(g_released && now >= g_newsTime + InpPendingLifeSec && CountPendings() > 0)
     {
      Print("Pending orders not triggered - deleting.");
      DeletePendings();
     }

   if(g_p60 > 0 && !g_logged && now >= g_newsTime + 300)
     {
      g_p300 = Mid();
      WriteLog();
      g_logged = true;
     }

   if(g_logged && now >= g_newsTime + MathMax(300, InpPendingLifeSec))
      ResetCycle();
  }

//+------------------------------------------------------------------+
void FireSignal(datetime now)
  {
   g_signalDone = true;
   g_pSignal    = Mid();
   g_score      = ComputeBias();
   g_predDir    = (MathAbs(g_score) >= InpBiasThreshold) ? (g_score > 0 ? 1 : -1) : 0;

   string msg = StringFormat("%s | %s in %ds | bias %+.0f -> %s",
                             _Symbol, g_newsTitle, (int)(g_newsTime - now), g_score, DirText(g_predDir));
   Print(msg, StringFormat("  [drift %+.2f  ticks %+.2f  usd %+.2f  consensus %+.2f]",
                           g_cDrift, g_cTicks, g_cUsd, g_cCons));
   if(InpAlert)
      Alert(msg);
   if(InpPush && !SendNotification(msg))
      Print("Push notification failed: ", GetLastError());

   if(InpMode == MODE_STRADDLE)
      PlacePendings(true, true);
   else
      if(InpMode == MODE_BIAS && g_predDir != 0)
         PlacePendings(g_predDir > 0, g_predDir < 0);
  }

//+------------------------------------------------------------------+
//| Bias score in [-100, +100]; positive = gold expected UP          |
//+------------------------------------------------------------------+
double ComputeBias()
  {
   double sum = 0, sumW = 0;
   g_cDrift = 0;
   g_cTicks = 0;
   g_cUsd   = 0;
   g_cCons  = 0;

   // 1) pre-news drift of gold, normalised by ATR * sqrt(minutes)
   if(InpWDrift > 0)
     {
      double atr  = AtrM1(_Symbol, 14);
      double past = iClose(_Symbol, PERIOD_M1, InpDriftMinutes);
      if(atr > 0 && past > 0)
        {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         g_cDrift = Squash((bid - past) / (atr * MathSqrt((double)InpDriftMinutes)));
         sum  += InpWDrift * g_cDrift;
         sumW += InpWDrift;
        }
     }

   // 2) up-tick vs down-tick imbalance in the last seconds
   if(InpWTicks > 0)
     {
      double f;
      if(TickFlow(f))
        {
         g_cTicks = f;
         sum  += InpWTicks * f;
         sumW += InpWTicks;
        }
     }

   // 3) USD proxy: EURUSD up = USD weak = gold up; USDxxx / DXY up = gold down
   if(InpWUsd > 0 && InpUsdProxy != "")
     {
      double pAtr  = AtrM1(InpUsdProxy, 14);
      double pPast = iClose(InpUsdProxy, PERIOD_M1, InpDriftMinutes);
      double pNow  = SymbolInfoDouble(InpUsdProxy, SYMBOL_BID);
      if(pAtr > 0 && pPast > 0 && pNow > 0)
        {
         double sign = (StringFind(InpUsdProxy, "USD") == 0 || StringFind(InpUsdProxy, "DX") >= 0) ? -1.0 : 1.0;
         g_cUsd = Squash(sign * (pNow - pPast) / (pAtr * MathSqrt((double)InpDriftMinutes)));
         sum  += InpWUsd * g_cUsd;
         sumW += InpWUsd;
        }
     }

   // 4) consensus: forecast vs previous (weak - the market already prices it)
   if(InpWConsensus > 0 && ArraySize(g_valueIds) > 0)
     {
      double c;
      if(ConsensusBias(c))
        {
         g_cCons = c;
         sum  += InpWConsensus * c;
         sumW += InpWConsensus;
        }
     }

   if(sumW <= 0)
      return 0;
   return 100.0 * sum / sumW;
  }

//+------------------------------------------------------------------+
bool TickFlow(double &f)
  {
   f = 0;
   MqlTick last;
   if(!SymbolInfoTick(_Symbol, last))
      return false;
   ulong to   = (ulong)last.time_msc;
   ulong from = to - (ulong)InpTickWindowSec * 1000;
   MqlTick ticks[];
   int n = CopyTicksRange(_Symbol, ticks, COPY_TICKS_INFO, from, to);
   if(n < 10)
      return false;
   int up = 0, dn = 0;
   for(int i = 1; i < n; i++)
     {
      if(ticks[i].bid > ticks[i - 1].bid)
         up++;
      else
         if(ticks[i].bid < ticks[i - 1].bid)
            dn++;
     }
   if(up + dn < 10)
      return false;
   f = Squash(2.0 * (up - dn) / (double)(up + dn));
   return true;
  }

//+------------------------------------------------------------------+
bool ConsensusBias(double &c)
  {
   c = 0;
   int    used = 0;
   double usd  = 0;
   for(int i = 0; i < ArraySize(g_valueIds); i++)
     {
      MqlCalendarValue v;
      if(!CalendarValueById(g_valueIds[i], v))
         continue;
      long prev = (v.revised_prev_value != LONG_MIN) ? v.revised_prev_value : v.prev_value;
      if(v.forecast_value == LONG_MIN || prev == LONG_MIN)
         continue;
      used++;
      if(v.forecast_value > prev)
         usd += Polarity(g_eventNames[i]);
      else
         if(v.forecast_value < prev)
            usd -= Polarity(g_eventNames[i]);
     }
   if(used == 0)
      return false;
   c = -usd / used;   // gold moves against USD
   return true;
  }

//+------------------------------------------------------------------+
//| Deviation mode: trade the published number                        |
//+------------------------------------------------------------------+
void CheckDeviation(datetime now)
  {
   int total = ArraySize(g_valueIds);
   if(total == 0)
     {
      g_devDone = true;
      return;
     }
   if(now > g_newsTime + InpDevMaxWaitSec)
     {
      g_devDone = true;
      Print("Deviation: no usable actual value within ", InpDevMaxWaitSec, "s - no trade.");
      return;
     }

   int    released = 0;
   double usd = 0;
   string info = "";
   for(int i = 0; i < total; i++)
     {
      MqlCalendarValue v;
      if(!CalendarValueById(g_valueIds[i], v) || v.actual_value == LONG_MIN)
         continue;
      released++;
      double s = 0;
      if(v.impact_type == CALENDAR_IMPACT_POSITIVE)
         s = 1;
      else
         if(v.impact_type == CALENDAR_IMPACT_NEGATIVE)
            s = -1;
         else
            if(v.forecast_value != LONG_MIN)
              {
               if(v.actual_value > v.forecast_value)
                  s = Polarity(g_eventNames[i]);
               else
                  if(v.actual_value < v.forecast_value)
                     s = -Polarity(g_eventNames[i]);
              }
      usd  += s;
      info += StringFormat("%s actual %.2f forecast %s; ", g_eventNames[i], v.actual_value / 1e6,
                           v.forecast_value == LONG_MIN ? "n/a" : DoubleToString(v.forecast_value / 1e6, 2));
     }

   if(released == 0)
      return;                          // not published yet - keep polling
   if(usd == 0 && released < total)
      return;                          // wait for the remaining releases

   int goldDir = (usd > 0) ? -1 : (usd < 0 ? 1 : 0);
   g_devDone = true;
   string msg = StringFormat("Deviation: %sUSD score %+.0f -> gold %s", info, usd, DirText(goldDir));
   Print(msg);
   if(InpAlert)
      Alert(msg);
   if(goldDir != 0)
      OpenMarket(goldDir);
  }

//+------------------------------------------------------------------+
//| Orders                                                           |
//+------------------------------------------------------------------+
void PlacePendings(bool buy, bool sell)
  {
   if(!SpreadOk())
     {
      Print("Spread too wide at signal time - no orders.");
      return;
     }
   if(CountPositions() > 0 || CountPendings() > 0)
     {
      Print("EA already has open orders/positions - skipping this news.");
      return;
     }

   double minD = MinStopDist();
   double dist = InpEntryDist;
   if(InpEntryATRMult > 0)
      dist = MathMax(dist, AtrM1(_Symbol, 14) * InpEntryATRMult);
   dist = MathMax(dist, minD);
   double slD  = MathMax(InpStopLoss, minD);
   double lots = CalcLots(slD);
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(buy)
     {
      double p  = NP(ask + dist);
      double tp = (InpTakeProfit > 0) ? NP(p + InpTakeProfit) : 0;
      if(!g_trade.BuyStop(lots, p, _Symbol, NP(p - slD), tp, ORDER_TIME_GTC, 0, "News buy stop"))
         PrintTradeError("BuyStop");
     }
   if(sell)
     {
      double p  = NP(bid - dist);
      double tp = (InpTakeProfit > 0) ? NP(p - InpTakeProfit) : 0;
      if(!g_trade.SellStop(lots, p, _Symbol, NP(p + slD), tp, ORDER_TIME_GTC, 0, "News sell stop"))
         PrintTradeError("SellStop");
     }
  }

//+------------------------------------------------------------------+
void OpenMarket(int dir)
  {
   if(!SpreadOk())
     {
      Print("Spread too wide after release - no trade.");
      return;
     }
   if(CountPositions() > 0)
      return;
   double slD  = MathMax(InpStopLoss, MinStopDist());
   double lots = CalcLots(slD);
   if(dir > 0)
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double tp  = (InpTakeProfit > 0) ? NP(ask + InpTakeProfit) : 0;
      if(!g_trade.Buy(lots, _Symbol, 0, NP(ask - slD), tp, "News deviation buy"))
         PrintTradeError("Buy");
     }
   else
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double tp  = (InpTakeProfit > 0) ? NP(bid - InpTakeProfit) : 0;
      if(!g_trade.Sell(lots, _Symbol, 0, NP(bid + slD), tp, "News deviation sell"))
         PrintTradeError("Sell");
     }
  }

//+------------------------------------------------------------------+
//| Break-even, trailing stop, max holding time                      |
//+------------------------------------------------------------------+
void ManagePositions()
  {
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double minD = MinStopDist();
   double step = MathMax(ts, InpTrailDist * 0.1);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      if(InpMaxHoldMin > 0 && TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME) >= InpMaxHoldMin * 60)
        {
         if(!g_trade.PositionClose(ticket))
            PrintTradeError("Close (max hold)");
         continue;
        }

      long   type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double newSL = sl;

      if(type == POSITION_TYPE_BUY)
        {
         double profit = bid - open;
         if(InpBreakEven > 0 && profit >= InpBreakEven && (sl == 0 || sl < open + InpBreakEvenLock))
            newSL = open + InpBreakEvenLock;
         if(InpTrailStart > 0 && profit >= InpTrailStart)
            newSL = MathMax(newSL, bid - InpTrailDist);
         newSL = NP(newSL);
         if(newSL > 0 && newSL >= sl + step && newSL <= bid - minD)
            if(!g_trade.PositionModify(ticket, newSL, tp))
               PrintTradeError("Modify");
        }
      else
        {
         double profit = open - ask;
         if(InpBreakEven > 0 && profit >= InpBreakEven && (sl == 0 || sl > open - InpBreakEvenLock))
            newSL = open - InpBreakEvenLock;
         if(InpTrailStart > 0 && profit >= InpTrailStart)
            newSL = (newSL == 0) ? ask + InpTrailDist : MathMin(newSL, ask + InpTrailDist);
         newSL = NP(newSL);
         if(newSL > 0 && (sl == 0 || newSL <= sl - step) && newSL >= ask + minD)
            if(!g_trade.PositionModify(ticket, newSL, tp))
               PrintTradeError("Modify");
        }
     }
  }

//+------------------------------------------------------------------+
int CountPositions()
  {
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         c++;
     }
   return c;
  }

//+------------------------------------------------------------------+
int CountPendings()
  {
   int c = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetString(ORDER_SYMBOL) == _Symbol && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic)
         c++;
     }
   return c;
  }

//+------------------------------------------------------------------+
void DeletePendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetString(ORDER_SYMBOL) == _Symbol && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic)
         if(!g_trade.OrderDelete(t))
            PrintTradeError("OrderDelete");
     }
  }

//+------------------------------------------------------------------+
double CalcLots(double slDist)
  {
   double lots = InpLots;
   if(InpRiskPercent > 0 && slDist > 0)
     {
      double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      if(tickSize > 0 && tickValue > 0)
         lots = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0 / (slDist / tickSize * tickValue);
     }
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   int digits = 2;
   if(step > 0)
     {
      lots   = MathFloor(lots / step) * step;
      digits = (int)MathMax(0, MathCeil(-MathLog10(step)));
     }
   lots = MathMax(vmin, MathMin(vmax, lots));
   return NormalizeDouble(lots, digits);
  }

//+------------------------------------------------------------------+
//| Log + measured accuracy                                          |
//+------------------------------------------------------------------+
string LogName()
  {
   return (MQLInfoInteger(MQL_TESTER) != 0) ? "tester_" + InpLogFile : InpLogFile;
  }

//+------------------------------------------------------------------+
int HitFlag(double move)   // 1 = correct, 0 = wrong, -1 = no call / no move
  {
   if(g_predDir == 0 || move == 0)
      return -1;
   return ((move > 0 && g_predDir > 0) || (move < 0 && g_predDir < 0)) ? 1 : 0;
  }

//+------------------------------------------------------------------+
void WriteLog()
  {
   double m60  = g_p60 - g_pRelease;
   double m300 = g_p300 - g_pRelease;
   int hit60   = HitFlag(m60);
   int hit300  = HitFlag(m300);
   if(hit60 >= 0)
     {
      g_statTotal++;
      if(hit60 == 1)
         g_statHits++;
     }

   g_lastResult = StringFormat("Last: %s | bias %+.0f %s | move +60s %+.2f, +5m %+.2f | %s",
                               TimeToString(g_newsTime, TIME_DATE | TIME_MINUTES), g_score, DirText(g_predDir),
                               m60, m300, hit60 == 1 ? "CORRECT" : (hit60 == 0 ? "WRONG" : "no call"));
   Print(g_lastResult);

   if(!InpWriteLog)
      return;
   int h = FileOpen(LogName(), FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ, ',');
   if(h == INVALID_HANDLE)
     {
      Print("Cannot open log file: ", GetLastError());
      return;
     }
   if(FileSize(h) == 0)
      FileWrite(h, "news_time", "events", "mode", "score", "pred_dir", "drift", "ticks", "usd", "consensus",
                "price_signal", "price_release", "price_60s", "price_300s", "move_60s", "move_300s", "hit_60s", "hit_300s");
   FileSeek(h, 0, SEEK_END);

   string events = g_newsTitle;
   if(ArraySize(g_eventNames) > 0)
     {
      events = "";
      for(int i = 0; i < ArraySize(g_eventNames); i++)
         events += (i > 0 ? " | " : "") + g_eventNames[i];
     }
   StringReplace(events, ",", " ");

   FileWrite(h, TimeToString(g_newsTime, TIME_DATE | TIME_MINUTES), events, EnumToString(InpMode),
             DoubleToString(g_score, 1), g_predDir,
             DoubleToString(g_cDrift, 3), DoubleToString(g_cTicks, 3), DoubleToString(g_cUsd, 3), DoubleToString(g_cCons, 3),
             DoubleToString(g_pSignal, _Digits), DoubleToString(g_pRelease, _Digits),
             DoubleToString(g_p60, _Digits), DoubleToString(g_p300, _Digits),
             DoubleToString(m60, _Digits), DoubleToString(m300, _Digits), hit60, hit300);
   FileClose(h);
  }

//+------------------------------------------------------------------+
void LoadStats()
  {
   g_statTotal = 0;
   g_statHits  = 0;
   if(!InpWriteLog || !FileIsExist(LogName(), FILE_COMMON))
      return;
   int h = FileOpen(LogName(), FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
   if(h == INVALID_HANDLE)
      return;
   int    col = 0;
   bool   header = true;
   string hit = "";
   while(!FileIsEnding(h))
     {
      string s = FileReadString(h);
      if(col == 15)
         hit = s;
      col++;
      if(FileIsLineEnding(h) || FileIsEnding(h))
        {
         if(!header && hit != "" && StringToInteger(hit) >= 0)
           {
            g_statTotal++;
            if(StringToInteger(hit) == 1)
               g_statHits++;
           }
         header = false;
         col = 0;
         hit = "";
        }
     }
   FileClose(h);
  }

//+------------------------------------------------------------------+
void ResetCycle()
  {
   g_newsTime   = 0;
   g_newsTitle  = "";
   ArrayResize(g_valueIds, 0);
   ArrayResize(g_eventNames, 0);
   g_signalDone = false;
   g_released   = false;
   g_devDone    = false;
   g_logged     = false;
   g_score      = 0;
   g_predDir    = 0;
   g_pSignal    = 0;
   g_pRelease   = 0;
   g_p60        = 0;
   g_p300       = 0;
   g_lastLoad   = 0;
  }

//+------------------------------------------------------------------+
//| Chart panel                                                      |
//+------------------------------------------------------------------+
void UpdatePanel(datetime now)
  {
   static datetime last = 0;
   if(now == last)
      return;
   last = now;

   string s = "Gold News Trader  |  " + EnumToString(InpMode) + "\n";
   if(g_newsTime > 0)
     {
      long left = (long)(g_newsTime - now);
      s += "Next news: " + g_newsTitle + "\n";
      s += "Release (server): " + TimeToString(g_newsTime, TIME_DATE | TIME_MINUTES) + "   " +
           (left >= 0 ? "in " + Countdown(left) : "released " + Countdown(-left) + " ago") + "\n";
     }
   else
      s += "No upcoming news found (check calendar / filters / manual times)\n";

   if(g_signalDone)
      s += StringFormat("Bias: %+.0f -> %s   [drift %+.2f  ticks %+.2f  usd %+.2f  cons %+.2f]\n",
                        g_score, DirText(g_predDir), g_cDrift, g_cTicks, g_cUsd, g_cCons);
   else
      s += StringFormat("Bias is calculated %d s before release\n", InpSecondsBefore);

   double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   s += StringFormat("Spread: %.2f  (max %.2f)\n", spread, InpMaxSpread);

   if(g_statTotal > 0)
      s += StringFormat("Measured accuracy (+60s): %d/%d = %.0f%%\n", g_statHits, g_statTotal, 100.0 * g_statHits / g_statTotal);
   else
      s += "Measured accuracy: no data yet\n";
   if(g_lastResult != "")
      s += g_lastResult + "\n";
   s += "Direction before release is a guess, not a certainty.";
   Comment(s);
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
double Mid()
  {
   return (SymbolInfoDouble(_Symbol, SYMBOL_BID) + SymbolInfoDouble(_Symbol, SYMBOL_ASK)) / 2.0;
  }

bool SpreadOk()
  {
   return (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) <= InpMaxSpread;
  }

double MinStopDist()
  {
   return (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
  }

double NP(double price)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0)
      price = MathRound(price / ts) * ts;
   return NormalizeDouble(price, _Digits);
  }

double AtrM1(string sym, int period)
  {
   MqlRates r[];
   int n = CopyRates(sym, PERIOD_M1, 1, period + 1, r);   // closed bars, oldest first
   if(n < period + 1)
      return 0;
   double sum = 0;
   for(int i = 1; i < n; i++)
      sum += MathMax(r[i].high - r[i].low,
                     MathMax(MathAbs(r[i].high - r[i - 1].close), MathAbs(r[i].low - r[i - 1].close)));
   return sum / (n - 1);
  }

double Squash(double x)   // tanh: maps any value into (-1, 1)
  {
   if(x > 20)
      return 1;
   if(x < -20)
      return -1;
   double e = MathExp(2.0 * x);
   return (e - 1.0) / (e + 1.0);
  }

double Polarity(string name)   // +1: higher number = stronger USD; -1: higher = weaker
  {
   string n = name;
   StringToLower(n);
   if(StringFind(n, "unemployment") >= 0 || StringFind(n, "jobless") >= 0 || StringFind(n, "claims") >= 0)
      return -1.0;
   return 1.0;
  }

string DirText(int dir)
  {
   return (dir > 0) ? "UP" : (dir < 0 ? "DOWN" : "NEUTRAL");
  }

string Countdown(long secs)
  {
   long d = secs / 86400;
   long h = (secs % 86400) / 3600;
   long m = (secs % 3600) / 60;
   long s = secs % 60;
   string t = StringFormat("%02d:%02d:%02d", (int)h, (int)m, (int)s);
   return (d > 0) ? StringFormat("%dd ", (int)d) + t : t;
  }

void PrintTradeError(string what)
  {
   Print(what, " failed: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
  }
//+------------------------------------------------------------------+
