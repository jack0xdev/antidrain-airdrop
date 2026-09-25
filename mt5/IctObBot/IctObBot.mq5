//+------------------------------------------------------------------+
//|                                                     IctObBot.mq5 |
//|  Order Block trading bot for MetaTrader 5                        |
//|                                                                  |
//|  The order block detection is a port of the logic in             |
//|  "ICT Concepts [LuxAlgo]" (c) LuxAlgo, licensed under            |
//|  CC BY-NC-SA 4.0 https://creativecommons.org/licenses/by-nc-sa/4.0/
//|  This adaptation is released under the same license:             |
//|  attribution required, NON-COMMERCIAL use only, share-alike.     |
//|                                                                  |
//|  Everything runs on CLOSED candles, so nothing repaints.         |
//|                                                                  |
//|  Default strategy - OB SWEEP:                                    |
//|   bearish OB: candle wick goes ABOVE the OB top and the candle   |
//|               closes back below it -> SELL, SL = that candle's high
//|   bullish OB: candle wick goes BELOW the OB bottom and the candle|
//|               closes back above it -> BUY,  SL = that candle's low
//|   SL hit -> the next sweep of the same OB is taken again,        |
//|   max 3 entries per OB.                                          |
//+------------------------------------------------------------------+
#property copyright "OB detection logic (c) LuxAlgo - CC BY-NC-SA 4.0 (non-commercial)"
#property version   "1.10"
#property description "OB sweep bot: LuxAlgo ICT Concepts OB detection ported to MQL5 (closed candles only)."
#property description "Entry on OB sweep, SL at the sweep candle high/low, up to 3 entries per OB. CC BY-NC-SA 4.0 - not for sale."

#include <Trade\Trade.mqh>

enum ENUM_BOT_TF
  {
   TF_M1  = PERIOD_M1,  // 1 minute
   TF_M5  = PERIOD_M5,  // 5 minutes
   TF_M10 = PERIOD_M10, // 10 minutes
   TF_M15 = PERIOD_M15, // 15 minutes
   TF_M30 = PERIOD_M30, // 30 minutes
   TF_H1  = PERIOD_H1   // 1 hour
  };

enum ENUM_ENTRY_MODE
  {
   ENTRY_SWEEP   = 3, // OB sweep: wick through the OB, close back -> market entry
   ENTRY_LIMIT   = 0, // Limit order at the OB as soon as it is detected
   ENTRY_CONFIRM = 1, // Market order after a candle rejects the OB
   ENTRY_OFF     = 2  // No trades (detect, draw, log only)
  };

enum ENUM_ENTRY_LEVEL
  {
   LEVEL_EDGE = 0, // OB edge (top of bullish / bottom of bearish)
   LEVEL_MID  = 1  // OB 50% (mean threshold)
  };

//--- inputs
input group "=== Order block detection (LuxAlgo logic) ==="
input ENUM_BOT_TF InpTF           = TF_M5;          // Timeframe (1m / 5m / 10m / 15m / 30m / 1h)
input int      InpSwingLength     = 10;             // Swing Lookback (LuxAlgo default 10)
input bool     InpUseBody         = true;           // Use Candle Body (LuxAlgo default true)
input int      InpWarmupBars      = 1500;           // History bars processed at start

input group "=== Entry ==="
input ENUM_ENTRY_MODE  InpEntryMode  = ENTRY_SWEEP;  // Entry mode
input int      InpMaxEntries      = 3;              // Sweep: max entries per OB (re-entry after SL)
input bool     InpStopOnBreaker   = true;           // Sweep: stop when a candle body closes through the OB
input bool     InpReentryAfterWin = false;          // Sweep: keep trading the OB after a winning trade
input ENUM_ENTRY_LEVEL InpEntryLevel = LEVEL_EDGE;   // Limit mode: entry level
input bool     InpTradeBull       = true;           // Trade bullish OBs (buy)
input bool     InpTradeBear       = true;           // Trade bearish OBs (sell)
input int      InpTradeLastN      = 1;              // Trade only the newest N OBs per side (LuxAlgo shows 1)
input int      InpExpiryBars      = 0;              // No new entry N bars after detection (0 = never)

input group "=== Risk ==="
input double   InpLots            = 0.01;           // Fixed lots
input double   InpRiskPercent     = 0.0;            // Risk % of balance per trade (0 = fixed lots)
input double   InpRR              = 2.0;            // Take profit = RR x risk (0 = no TP)
input double   InpSLBufferATR     = 0.0;            // Extra SL buffer beyond sweep high/low or OB (ATR x)
input double   InpMinRiskATR      = 0.0;            // Minimum SL distance (ATR x, 0 = broker minimum)
input double   InpMaxRiskATR      = 0.0;            // Skip entry if SL distance > ATR x (0 = off)
input double   InpBreakEvenR      = 0.0;            // Move SL to entry at N x risk (0 = off)
input int      InpMaxPositions    = 1;              // Max open positions
input double   InpMaxSpread       = 0.50;           // Max spread for market orders (price)
input int      InpSlippagePts     = 50;             // Max slippage (points)
input ulong    InpMagic           = 26092502;       // Magic number

input group "=== Filters ==="
input int      InpStartHour       = 0;              // Trade from hour (server time)
input int      InpEndHour         = 24;             // Trade until hour (server time)
input int      InpNewsBlockMin    = 15;             // No entries +-N min around high-impact USD news (0 = off)

input group "=== Display, alerts & log ==="
input int      InpDrawLastN       = 2;              // Draw newest N OBs per side
input color    InpBullColor       = clrDodgerBlue;  // Bullish OB color
input color    InpBearColor       = clrTomato;      // Bearish OB color
input color    InpBreakerColor    = clrDimGray;     // Breaker color
input bool     InpAlert           = true;           // Alert on new OB / entry
input bool     InpWriteLog        = true;           // Log detections to CSV (Common\Files)
input string   InpLogFile         = "ob_detections.csv"; // Log file name

//--- types
struct OrderBlock
  {
   double   top;
   double   btm;
   datetime obTime;       // the OB candle
   long     obIdx;
   datetime swingTime;    // swing high/low that was broken
   long     swingIdx;
   datetime detectTime;   // candle whose close broke the swing = OB appears at its close
   long     detectIdx;
   bool     breaker;
   bool     mitigated;    // price came back into the OB after detection
   bool     used;         // traded or given up - never trade again
   ulong    ticket;       // pending order ticket
   int      entries;      // sweep: trades taken on this OB
   bool     won;          // sweep: a trade on this OB closed in profit
   ulong    posId;        // sweep: open position of this OB (0 = none)
  };

struct Swing
  {
   double   y;
   datetime time;
   long     idx;
   bool     crossed;
   bool     valid;
  };

//--- state
CTrade          g_trade;
ENUM_TIMEFRAMES g_tf;
OrderBlock      g_bull[];
OrderBlock      g_bear[];
Swing           g_top;
Swing           g_btm;
int             g_os          = 0;
long            g_idx         = -1;     // running index of processed closed candles
datetime        g_lastBarTime = 0;      // open time of the last processed closed candle
bool            g_ready       = false;  // warm-up done
bool            g_live        = false;  // false while replaying history
int             g_detections  = 0;
int             g_lags[];               // OB candle -> detection, in candles
int             g_swingLags[];          // swing -> detection, in candles

//+------------------------------------------------------------------+
int OnInit()
  {
   g_tf = (ENUM_TIMEFRAMES)InpTF;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpSlippagePts);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   if(InpSwingLength < 3)
     {
      Print("Swing Lookback must be >= 3");
      return(INIT_PARAMETERS_INCORRECT);
     }
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, "ICTOB_");
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   if(!g_ready && !Warmup())
      return;

   datetime t1 = iTime(_Symbol, g_tf, 1);
   if(t1 != 0 && t1 != g_lastBarTime)
      ProcessNewBars();

   ManagePositions();
   if(CountPendings() > 0 && (!TradingWindowOk() || CountPositions() >= InpMaxPositions))
      CancelPendingsTemp();
  }

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
   if(InpAlert)
      Alert(_Symbol, " OB bot: position opened at ", DoubleToString(HistoryDealGetDouble(trans.deal, DEAL_PRICE), _Digits));
   if(CountPositions() >= InpMaxPositions)
      CancelPendingsTemp();
  }

//+------------------------------------------------------------------+
//| Replay history so the state matches what LuxAlgo shows           |
//+------------------------------------------------------------------+
bool Warmup()
  {
   int bars = Bars(_Symbol, g_tf);
   if(bars < InpSwingLength + 50)
      return false;
   int start = MathMin(InpWarmupBars, bars - InpSwingLength - 2);

   ArrayResize(g_bull, 0);
   ArrayResize(g_bear, 0);
   ArrayResize(g_lags, 0);
   ArrayResize(g_swingLags, 0);
   g_top.valid = false;
   g_btm.valid = false;
   g_os = 0;
   g_idx = -1;
   g_detections = 0;
   DeleteAllOurPendings();   // re-placed below if still valid
   if(InpWriteLog)
      StartLog();

   g_live = false;
   for(int s = start; s >= 1; s--)
      ProcessBar(s);
   g_lastBarTime = iTime(_Symbol, g_tf, 1);
   g_live  = true;
   g_ready = true;

   Print(StringFormat("Warm-up: %d candles, %d OB detections, %d bullish / %d bearish OBs alive",
                      start, g_detections, ArraySize(g_bull), ArraySize(g_bear)));
   if(InpEntryMode == ENTRY_SWEEP)
      RestoreFromHistory();   // entry count survives a restart / settings change
   else
      ManageEntries();        // sweeps are only taken on new live candles
   DrawOBs();
   UpdatePanel();
   return true;
  }

//+------------------------------------------------------------------+
void ProcessNewBars()
  {
   int from = 1;
   int sh = iBarShift(_Symbol, g_tf, g_lastBarTime, true);
   if(sh > 1)
      from = sh - 1;
   for(int s = from; s >= 1; s--)
      ProcessBar(s);
   g_lastBarTime = iTime(_Symbol, g_tf, 1);

   ManageEntries();
   DrawOBs();
   UpdatePanel();
  }

//+------------------------------------------------------------------+
//| One closed candle at shift s - same order as the Pine script     |
//+------------------------------------------------------------------+
void ProcessBar(int s)
  {
   g_idx++;
   int len = InpSwingLength;

   //--- swings(): a high is a swing when the next `len` candles stay below it
   double upper = H(s), lower = L(s);
   for(int k = 1; k < len; k++)
     {
      upper = MathMax(upper, H(s + k));
      lower = MathMin(lower, L(s + k));
     }
   int prevOs = g_os;
   if(H(s + len) > upper)
      g_os = 0;
   else
      if(L(s + len) < lower)
         g_os = 1;
   if(g_os == 0 && prevOs != 0)
      NewSwing(g_top, H(s + len), T(s + len), g_idx - len);
   if(g_os == 1 && prevOs != 1)
      NewSwing(g_btm, L(s + len), T(s + len), g_idx - len);

   double c = C(s), o = O(s);

   //--- bullish OB: a close above the swing high
   if(g_top.valid && !g_top.crossed && c > g_top.y)
     {
      g_top.crossed = true;
      long   d = g_idx - g_top.idx;
      double minima = BodyMax(s + 1), maxima = BodyMin(s + 1);
      int    loc = s + 1;
      for(int i = 1; i <= d - 1; i++)
        {
         double mn = BodyMin(s + i);
         minima = MathMin(mn, minima);
         if(minima == mn)
           {
            maxima = BodyMax(s + i);
            loc = s + i;
           }
        }
      AddOB(g_bull, true, maxima, minima, loc, s, g_top);
     }
   for(int i = ArraySize(g_bull) - 1; i >= 0; i--)
     {
      if(!g_bull[i].breaker)
        {
         if(g_bull[i].detectIdx < g_idx && L(s) <= g_bull[i].top)
            g_bull[i].mitigated = true;
         if(MathMin(c, o) < g_bull[i].btm)
            g_bull[i].breaker = true;
        }
      else
         if(c > g_bull[i].top)
            RemoveOB(g_bull, i);
     }

   //--- bearish OB: a close below the swing low
   if(g_btm.valid && !g_btm.crossed && c < g_btm.y)
     {
      g_btm.crossed = true;
      long   d = g_idx - g_btm.idx;
      double minima = BodyMin(s + 1), maxima = BodyMax(s + 1);
      int    loc = s + 1;
      for(int i = 1; i <= d - 1; i++)
        {
         double mx = BodyMax(s + i);
         maxima = MathMax(mx, maxima);
         if(maxima == mx)
           {
            minima = BodyMin(s + i);
            loc = s + i;
           }
        }
      AddOB(g_bear, false, maxima, minima, loc, s, g_btm);
     }
   for(int i = ArraySize(g_bear) - 1; i >= 0; i--)
     {
      if(!g_bear[i].breaker)
        {
         if(g_bear[i].detectIdx < g_idx && H(s) >= g_bear[i].btm)
            g_bear[i].mitigated = true;
         if(MathMax(c, o) > g_bear[i].top)
            g_bear[i].breaker = true;
        }
      else
         if(c < g_bear[i].btm)
            RemoveOB(g_bear, i);
     }
  }

//+------------------------------------------------------------------+
void NewSwing(Swing &sw, double y, datetime t, long idx)
  {
   sw.y       = y;
   sw.time    = t;
   sw.idx     = idx;
   sw.crossed = false;
   sw.valid   = true;
  }

//+------------------------------------------------------------------+
void AddOB(OrderBlock &arr[], bool bull, double top, double btm, int locShift, int s, const Swing &sw)
  {
   OrderBlock ob;
   ob.top        = top;
   ob.btm        = btm;
   ob.obTime     = T(locShift);
   ob.obIdx      = g_idx - (locShift - s);
   ob.swingTime  = sw.time;
   ob.swingIdx   = sw.idx;
   ob.detectTime = T(s);
   ob.detectIdx  = g_idx;
   ob.breaker    = false;
   ob.mitigated  = false;
   ob.used       = false;
   ob.ticket     = 0;
   ob.entries    = 0;
   ob.won        = false;
   ob.posId      = 0;

   int n = ArraySize(arr);
   ArrayResize(arr, n + 1);
   for(int i = n; i > 0; i--)
      arr[i] = arr[i - 1];
   arr[0] = ob;
   if(ArraySize(arr) > 100)
      RemoveOB(arr, ArraySize(arr) - 1);

   int lag      = (int)(ob.detectIdx - ob.obIdx);
   int swingLag = (int)(ob.detectIdx - ob.swingIdx);
   PushInt(g_lags, lag);
   PushInt(g_swingLags, swingLag);
   g_detections++;
   LogOB(ob, bull, lag, swingLag);

   if(g_live)
     {
      string msg = StringFormat("%s %s OB %s-%s | OB candle %s | shown %s | lag %d candles (%s) | swing->shown %d candles",
                                _Symbol, bull ? "Bullish" : "Bearish",
                                DoubleToString(ob.btm, _Digits), DoubleToString(ob.top, _Digits),
                                TimeToString(ob.obTime, TIME_DATE | TIME_MINUTES),
                                TimeToString(ob.detectTime + PeriodSeconds(g_tf), TIME_DATE | TIME_MINUTES),
                                lag, Duration((long)(ob.detectTime - ob.obTime)), swingLag);
      Print(msg);
      if(InpAlert)
         Alert(msg);
     }
  }

//+------------------------------------------------------------------+
void RemoveOB(OrderBlock &arr[], int index)
  {
   if(arr[index].ticket > 0)
      DeleteOrder(arr[index].ticket);
   int n = ArraySize(arr);
   for(int i = index; i < n - 1; i++)
      arr[i] = arr[i + 1];
   ArrayResize(arr, n - 1);
  }

//+------------------------------------------------------------------+
//| Entries                                                          |
//+------------------------------------------------------------------+
void ManageEntries()
  {
   ManageSide(g_bull, true);
   ManageSide(g_bear, false);
  }

//+------------------------------------------------------------------+
void ManageSide(OrderBlock &arr[], bool bull)
  {
   bool allowed = bull ? InpTradeBull : InpTradeBear;
   for(int i = 0; i < ArraySize(arr); i++)
     {
      bool expired = (InpExpiryBars > 0 && g_idx - arr[i].detectIdx > InpExpiryBars);
      if(InpEntryMode == ENTRY_SWEEP)
        {
         SweepEntry(arr[i], bull, allowed && !expired && i < InpTradeLastN);
         continue;
        }
      bool dead    = arr[i].breaker || expired || !allowed || i >= InpTradeLastN || InpEntryMode != ENTRY_LIMIT;

      //--- existing pending order
      if(arr[i].ticket > 0)
        {
         if(!OrderSelect(arr[i].ticket))      // filled (or removed by broker)
           {
            arr[i].ticket = 0;
            arr[i].used   = true;
           }
         else
            if(dead)
              {
               DeleteOrder(arr[i].ticket);
               arr[i].ticket = 0;
               arr[i].used   = true;
              }
         continue;
        }

      if(arr[i].used || arr[i].breaker || expired || !allowed || i >= InpTradeLastN)
         continue;
      if(!TradingWindowOk() || CountPositions() >= InpMaxPositions)
         continue;

      if(InpEntryMode == ENTRY_LIMIT)
        {
         if(arr[i].mitigated)                 // price already came back before we could place
           {
            arr[i].used = true;
            continue;
           }
         PlaceLimit(arr[i], bull);
        }
      else
         if(InpEntryMode == ENTRY_CONFIRM && arr[i].detectIdx < g_idx && Rejection(arr[i], bull))
           {
            OpenMarket(arr[i], bull);
            arr[i].used = true;
           }
     }
  }

//+------------------------------------------------------------------+
//| OB sweep: runs once per closed candle (shift 1)                  |
//+------------------------------------------------------------------+
void SweepEntry(OrderBlock &ob, bool bull, bool eligible)
  {
   //--- previous trade of this OB: still open -> wait; closed -> win or loss?
   if(ob.posId > 0)
     {
      if(PositionOpenById(ob.posId))
         return;
      double profit = ClosedProfit(ob.posId);
      Print(StringFormat("%s OB trade %d/%d closed: %s %.2f", bull ? "Bullish" : "Bearish",
                         ob.entries, InpMaxEntries, profit > 0 ? "profit" : "loss", profit));
      if(profit > 0 && !InpReentryAfterWin)
         ob.won = true;
      ob.posId = 0;
     }

   if(!eligible || ob.won || ob.entries >= InpMaxEntries)
      return;
   if(ob.breaker && InpStopOnBreaker)
      return;
   if(ob.detectIdx >= g_idx)                 // the sweep must come after the OB exists
      return;
   if(!Swept(ob, bull))
      return;

   string what = StringFormat("%s OB sweep %s-%s", bull ? "Bullish" : "Bearish",
                              DoubleToString(ob.btm, _Digits), DoubleToString(ob.top, _Digits));
   if(!TradingWindowOk() || CountPositions() >= InpMaxPositions)
     {
      Print(what, " - skipped (session / news / max positions)");
      return;
     }
   OpenSweep(ob, bull, what);
  }

//+------------------------------------------------------------------+
//| Wick through the OB edge, close back on the OB side              |
//+------------------------------------------------------------------+
bool Swept(const OrderBlock &ob, bool bull)
  {
   if(bull)
      return (L(1) < ob.btm && C(1) > ob.btm);
   return (H(1) > ob.top && C(1) < ob.top);
  }

//+------------------------------------------------------------------+
//| Market entry, SL at the sweep candle's low (buy) / high (sell)   |
//+------------------------------------------------------------------+
void OpenSweep(OrderBlock &ob, bool bull, string what)
  {
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double spread = ask - bid;
   if(spread > InpMaxSpread)
     {
      Print(what, " - skipped, spread ", DoubleToString(spread, _Digits));
      return;
     }
   double atr    = Atr(14);
   double buffer = InpSLBufferATR * atr;
   double minD   = MathMax(MinStopDist() + spread, InpMinRiskATR * atr);
   double entry, sl, risk;
   if(bull)
     {
      entry = ask;
      sl    = L(1) - buffer;                  // buy SL triggers on bid, candle lows are bid
      risk  = MathMax(entry - sl, minD);
      sl    = entry - risk;
     }
   else
     {
      entry = bid;
      sl    = H(1) + spread + buffer;         // sell SL triggers on ask = bid + spread
      risk  = MathMax(sl - entry, minD);
      sl    = entry + risk;
     }
   if(InpMaxRiskATR > 0 && atr > 0 && risk > InpMaxRiskATR * atr)
     {
      Print(what, StringFormat(" - skipped, SL distance %.2f > %.1f x ATR", risk, InpMaxRiskATR));
      return;
     }
   double tp = 0;
   if(InpRR > 0)
      tp = bull ? entry + InpRR * risk : entry - InpRR * risk;

   double lots    = CalcLots(risk);
   string comment = StringFormat("OBsw %s #%d", ObTag(ob, bull), ob.entries + 1);
   bool ok = bull ? g_trade.Buy(lots, _Symbol, 0, NP(sl), tp > 0 ? NP(tp) : 0, comment)
                  : g_trade.Sell(lots, _Symbol, 0, NP(sl), tp > 0 ? NP(tp) : 0, comment);
   uint rc = g_trade.ResultRetcode();
   if(!ok || g_trade.ResultOrder() == 0 ||
      (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_DONE_PARTIAL && rc != TRADE_RETCODE_PLACED))
     {
      PrintTradeError(bull ? "Sweep buy" : "Sweep sell");
      return;
     }
   ob.entries++;
   ob.posId = g_trade.ResultOrder();         // position id = ticket of the opening order
   string msg = StringFormat("%s %s -> %s entry %d/%d  SL %s  TP %s", _Symbol, what, bull ? "BUY" : "SELL",
                             ob.entries, InpMaxEntries, DoubleToString(NP(sl), _Digits),
                             tp > 0 ? DoubleToString(NP(tp), _Digits) : "none");
   Print(msg);
   if(InpAlert)
      Alert(msg);
  }

//+------------------------------------------------------------------+
//| Rebuild entry counters from our deals (comment "OBsw <tag> #n")  |
//+------------------------------------------------------------------+
void RestoreFromHistory()
  {
   datetime now = TimeCurrent();
   if(!HistorySelect(now - 90 * 86400, now + 86400))
      return;
   string comments[];
   ulong  positions[];
   int total = HistoryDealsTotal();
   for(int k = 0; k < total; k++)
     {
      ulong d = HistoryDealGetTicket(k);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic || HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      int n = ArraySize(comments);
      ArrayResize(comments, n + 1);
      ArrayResize(positions, n + 1);
      comments[n]  = HistoryDealGetString(d, DEAL_COMMENT);
      positions[n] = (ulong)HistoryDealGetInteger(d, DEAL_POSITION_ID);
     }
   // HistorySelectByPosition() below resets the selection, so the deals are copied first
   for(int k = 0; k < ArraySize(comments); k++)
     {
      RestoreSide(g_bull, true, comments[k], positions[k]);
      RestoreSide(g_bear, false, comments[k], positions[k]);
     }
  }

void RestoreSide(OrderBlock &arr[], bool bull, string comment, ulong pos)
  {
   for(int i = 0; i < ArraySize(arr); i++)
     {
      if(StringFind(comment, ObTag(arr[i], bull)) < 0)
         continue;
      arr[i].entries++;
      if(PositionOpenById(pos))
         arr[i].posId = pos;
      else
         if(ClosedProfit(pos) > 0 && !InpReentryAfterWin)
            arr[i].won = true;
     }
  }

string ObTag(const OrderBlock &ob, bool bull)
  {
   return (bull ? "B " : "S ") + TimeToString(ob.obTime, TIME_DATE | TIME_MINUTES);
  }

bool PositionOpenById(ulong id)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == id)
         return true;
     }
   return false;
  }

double ClosedProfit(ulong id)
  {
   if(!HistorySelectByPosition(id))
      return 0;
   double p = 0;
   for(int k = 0; k < HistoryDealsTotal(); k++)
     {
      ulong d = HistoryDealGetTicket(k);
      p += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
     }
   return p;
  }

//+------------------------------------------------------------------+
bool Rejection(const OrderBlock &ob, bool bull)
  {
   if(bull)
      return (L(1) <= ob.top && C(1) > ob.top && C(1) > O(1));
   return (H(1) >= ob.btm && C(1) < ob.btm && C(1) < O(1));
  }

//+------------------------------------------------------------------+
//| SL beyond the OB (+ATR buffer), min/max risk, TP = RR x risk     |
//+------------------------------------------------------------------+
bool Levels(const OrderBlock &ob, bool bull, double entry, double &sl, double &tp)
  {
   double atr = Atr(14);
   if(atr <= 0)
      return false;
   double minRisk = MathMax(InpMinRiskATR * atr, MinStopDist());
   double risk;
   if(bull)
     {
      sl   = ob.btm - InpSLBufferATR * atr;
      risk = MathMax(entry - sl, minRisk);
      sl   = entry - risk;
      tp   = (InpRR > 0) ? entry + InpRR * risk : 0;
     }
   else
     {
      sl   = ob.top + InpSLBufferATR * atr;
      risk = MathMax(sl - entry, minRisk);
      sl   = entry + risk;
      tp   = (InpRR > 0) ? entry - InpRR * risk : 0;
     }
   if(InpMaxRiskATR > 0 && risk > InpMaxRiskATR * atr)
     {
      Print(StringFormat("OB skipped: risk %.2f > %.1f x ATR", risk, InpMaxRiskATR));
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
void PlaceLimit(OrderBlock &ob, bool bull)
  {
   double entry;
   if(InpEntryLevel == LEVEL_MID)
      entry = (ob.top + ob.btm) / 2.0;
   else
      entry = bull ? ob.top : ob.btm;
   entry = NP(entry);

   double minD = MinStopDist();
   if(bull && entry >= SymbolInfoDouble(_Symbol, SYMBOL_ASK) - minD)
     {
      ob.used = true;
      return;
     }
   if(!bull && entry <= SymbolInfoDouble(_Symbol, SYMBOL_BID) + minD)
     {
      ob.used = true;
      return;
     }

   double sl, tp;
   if(!Levels(ob, bull, entry, sl, tp))
     {
      ob.used = true;
      return;
     }
   double lots = CalcLots(MathAbs(entry - sl));
   bool ok = bull ? g_trade.BuyLimit(lots, entry, _Symbol, NP(sl), NP(tp), ORDER_TIME_GTC, 0, "OB buy limit")
                  : g_trade.SellLimit(lots, entry, _Symbol, NP(sl), NP(tp), ORDER_TIME_GTC, 0, "OB sell limit");
   if(ok && g_trade.ResultOrder() > 0)
     {
      ob.ticket = g_trade.ResultOrder();
      Print(StringFormat("%s limit placed at %s  SL %s  TP %s", bull ? "Buy" : "Sell",
                         DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), DoubleToString(tp, _Digits)));
     }
   else
     {
      PrintTradeError(bull ? "BuyLimit" : "SellLimit");
      ob.used = true;
     }
  }

//+------------------------------------------------------------------+
void OpenMarket(const OrderBlock &ob, bool bull)
  {
   if(SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID) > InpMaxSpread)
     {
      Print("Spread too wide - OB entry skipped");
      return;
     }
   double entry = bull ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl, tp;
   if(!Levels(ob, bull, entry, sl, tp))
      return;
   double lots = CalcLots(MathAbs(entry - sl));
   bool ok = bull ? g_trade.Buy(lots, _Symbol, 0, NP(sl), NP(tp), "OB confirm buy")
                  : g_trade.Sell(lots, _Symbol, 0, NP(sl), NP(tp), "OB confirm sell");
   if(!ok)
      PrintTradeError(bull ? "Buy" : "Sell");
  }

//+------------------------------------------------------------------+
//| Break-even at N x risk                                           |
//+------------------------------------------------------------------+
void ManagePositions()
  {
   if(InpBreakEvenR <= 0)
      return;
   double minD = MinStopDist();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
        {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if(sl > 0 && sl < open && bid - open >= InpBreakEvenR * (open - sl) && open <= bid - minD)
            if(!g_trade.PositionModify(ticket, NP(open), tp))
               PrintTradeError("Break-even");
        }
      else
        {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(sl > open && open - ask >= InpBreakEvenR * (sl - open) && open >= ask + minD)
            if(!g_trade.PositionModify(ticket, NP(open), tp))
               PrintTradeError("Break-even");
        }
     }
  }

//+------------------------------------------------------------------+
//| Pending order housekeeping                                       |
//+------------------------------------------------------------------+
void CancelPendingsTemp()   // session / news / max positions: OB stays tradable
  {
   CancelSide(g_bull);
   CancelSide(g_bear);
  }

void CancelSide(OrderBlock &arr[])
  {
   for(int i = 0; i < ArraySize(arr); i++)
     {
      if(arr[i].ticket == 0)
         continue;
      if(OrderSelect(arr[i].ticket))
         DeleteOrder(arr[i].ticket);
      else
         arr[i].used = true;                 // it was filled
      arr[i].ticket = 0;
     }
  }

void DeleteOrder(ulong ticket)
  {
   if(OrderSelect(ticket) && !g_trade.OrderDelete(ticket))
      PrintTradeError("OrderDelete");
  }

void DeleteAllOurPendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetString(ORDER_SYMBOL) == _Symbol && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic)
         DeleteOrder(t);
     }
  }

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
//| Filters                                                          |
//+------------------------------------------------------------------+
bool TradingWindowOk()
  {
   if(InpEntryMode == ENTRY_OFF)
      return false;
   MqlDateTime dt;
   TimeToStruct(TimeTradeServer(), dt);
   bool inSession = (InpStartHour <= InpEndHour) ? (dt.hour >= InpStartHour && dt.hour < InpEndHour)
                    : (dt.hour >= InpStartHour || dt.hour < InpEndHour);
   return inSession && !NewsBlocked();
  }

bool NewsBlocked()
  {
   if(InpNewsBlockMin <= 0 || MQLInfoInteger(MQL_TESTER) != 0)
      return false;
   static datetime lastCheck = 0;
   static bool     blocked   = false;
   datetime now = TimeTradeServer();
   if(now - lastCheck < 30)
      return blocked;
   lastCheck = now;
   blocked   = false;
   MqlCalendarValue v[];
   int n = CalendarValueHistory(v, (datetime)(now - InpNewsBlockMin * 60), (datetime)(now + InpNewsBlockMin * 60), NULL, "USD");
   for(int i = 0; i < n && !blocked; i++)
     {
      MqlCalendarEvent ev;
      if(CalendarEventById(v[i].event_id, ev) && ev.importance == CALENDAR_IMPORTANCE_HIGH)
         blocked = true;
     }
   return blocked;
  }

//+------------------------------------------------------------------+
//| Log                                                              |
//+------------------------------------------------------------------+
string LogName()
  {
   return (MQLInfoInteger(MQL_TESTER) != 0) ? "tester_" + InpLogFile : InpLogFile;
  }

void StartLog()
  {
   int h = FileOpen(LogName(), FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
      return;
   FileWrite(h, "side", "ob_candle", "swing_candle", "breakout_candle", "shown_at", "lag_candles", "swing_to_shown_candles",
             "lag_minutes", "top", "bottom");
   FileClose(h);
  }

void LogOB(const OrderBlock &ob, bool bull, int lag, int swingLag)
  {
   if(!InpWriteLog)
      return;
   int h = FileOpen(LogName(), FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ, ',');
   if(h == INVALID_HANDLE)
      return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h, bull ? "bull" : "bear",
             TimeToString(ob.obTime, TIME_DATE | TIME_MINUTES),
             TimeToString(ob.swingTime, TIME_DATE | TIME_MINUTES),
             TimeToString(ob.detectTime, TIME_DATE | TIME_MINUTES),
             TimeToString(ob.detectTime + PeriodSeconds(g_tf), TIME_DATE | TIME_MINUTES),
             lag, swingLag, (long)(ob.detectTime - ob.obTime) / 60,
             DoubleToString(ob.top, _Digits), DoubleToString(ob.btm, _Digits));
   FileClose(h);
  }

//+------------------------------------------------------------------+
//| Chart                                                            |
//+------------------------------------------------------------------+
void DrawOBs()
  {
   ObjectsDeleteAll(0, "ICTOB_");
   datetime right = iTime(_Symbol, g_tf, 0) + PeriodSeconds(g_tf) * 10;
   DrawSide(g_bull, true, right);
   DrawSide(g_bear, false, right);
   ChartRedraw();
  }

void DrawSide(OrderBlock &arr[], bool bull, datetime right)
  {
   for(int i = 0; i < MathMin(InpDrawLastN, ArraySize(arr)); i++)
     {
      string name = StringFormat("ICTOB_%s_%d", bull ? "bull" : "bear", i);
      color  clr  = arr[i].breaker ? InpBreakerColor : (bull ? InpBullColor : InpBearColor);
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, arr[i].obTime, arr[i].top, right, arr[i].btm);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);

      // where the OB actually appeared (close of the breakout candle)
      string mark = name + "_shown";
      double y = bull ? arr[i].btm : arr[i].top;
      ObjectCreate(0, mark, OBJ_ARROW, 0, arr[i].detectTime, y);
      ObjectSetInteger(0, mark, OBJPROP_ARROWCODE, 159);
      ObjectSetInteger(0, mark, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, mark, OBJPROP_WIDTH, 3);

      string lbl = name + "_txt";
      ObjectCreate(0, lbl, OBJ_TEXT, 0, right, y);
      ObjectSetString(0, lbl, OBJPROP_TEXT, StringFormat("%sOB  %s  lag %d", bull ? "+" : "-",
                      StatusText(arr[i]), (int)(arr[i].detectIdx - arr[i].obIdx)));
      ObjectSetInteger(0, lbl, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, lbl, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, lbl, OBJPROP_ANCHOR, bull ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER);
     }
  }

void UpdatePanel()
  {
   string s = StringFormat("ICT OB Bot | %s %s | swing %d | body %s | %s\n", _Symbol, EnumToString(g_tf),
                           InpSwingLength, InpUseBody ? "on" : "off", EnumToString(InpEntryMode));
   s += SideText("Bull", g_bull);
   s += SideText("Bear", g_bear);

   int n = ArraySize(g_lags);
   if(n > 0)
     {
      s += StringFormat("Lag OB candle -> shown (%d OBs): median %d, avg %.1f, min %d, max %d candles\n",
                        n, Median(g_lags), Average(g_lags), g_lags[ArrayMinimum(g_lags)], g_lags[ArrayMaximum(g_lags)]);
      s += StringFormat("Lag swing -> shown: median %d, min %d candles (minimum possible = %d)\n",
                        Median(g_swingLags), g_swingLags[ArrayMinimum(g_swingLags)], InpSwingLength + 1);
     }
   s += StringFormat("Positions %d | Pendings %d | Trading window %s\n", CountPositions(), CountPendings(),
                     TradingWindowOk() ? "open" : "closed");
   s += "OB detection: LuxAlgo ICT Concepts, CC BY-NC-SA 4.0 (non-commercial)";
   Comment(s);
  }

string SideText(string side, OrderBlock &arr[])
  {
   if(ArraySize(arr) == 0)
      return side + " OB: none\n";
   OrderBlock ob = arr[0];
   return StringFormat("%s OB: %s - %s | OB candle %s | shown %s | lag %d candles (%s) | %s\n",
                       side, DoubleToString(ob.btm, _Digits), DoubleToString(ob.top, _Digits),
                       TimeToString(ob.obTime, TIME_DATE | TIME_MINUTES),
                       TimeToString(ob.detectTime + PeriodSeconds(g_tf), TIME_DATE | TIME_MINUTES),
                       (int)(ob.detectIdx - ob.obIdx), Duration((long)(ob.detectTime - ob.obTime)), StatusText(ob));
  }

string StatusText(const OrderBlock &ob)
  {
   if(InpEntryMode == ENTRY_SWEEP)
     {
      if(ob.posId > 0)
         return StringFormat("IN TRADE %d/%d", ob.entries, InpMaxEntries);
      if(ob.won)
         return StringFormat("WON %d/%d", ob.entries, InpMaxEntries);
      if(ob.entries >= InpMaxEntries)
         return StringFormat("DONE %d/%d", ob.entries, InpMaxEntries);
      if(ob.breaker)
         return StringFormat("BREAKER %d/%d", ob.entries, InpMaxEntries);
      return StringFormat("WAIT SWEEP %d/%d", ob.entries, InpMaxEntries);
     }
   if(ob.breaker)
      return "BREAKER";
   if(ob.ticket > 0)
      return "PENDING";
   if(ob.used)
      return "USED";
   if(ob.mitigated)
      return "MITIGATED";
   return "FRESH";
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
double   H(int s)       { return iHigh(_Symbol, g_tf, s); }
double   L(int s)       { return iLow(_Symbol, g_tf, s); }
double   O(int s)       { return iOpen(_Symbol, g_tf, s); }
double   C(int s)       { return iClose(_Symbol, g_tf, s); }
datetime T(int s)       { return iTime(_Symbol, g_tf, s); }
double   BodyMax(int s) { return InpUseBody ? MathMax(O(s), C(s)) : H(s); }
double   BodyMin(int s) { return InpUseBody ? MathMin(O(s), C(s)) : L(s); }

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

double Atr(int period)
  {
   MqlRates r[];
   int n = CopyRates(_Symbol, g_tf, 1, period + 1, r);   // closed candles, oldest first
   if(n < period + 1)
      return 0;
   double sum = 0;
   for(int i = 1; i < n; i++)
      sum += MathMax(r[i].high - r[i].low,
                     MathMax(MathAbs(r[i].high - r[i - 1].close), MathAbs(r[i].low - r[i - 1].close)));
   return sum / (n - 1);
  }

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

void PushInt(int &arr[], int v)
  {
   int n = ArraySize(arr);
   ArrayResize(arr, n + 1);
   arr[n] = v;
  }

int Median(const int &arr[])
  {
   int tmp[];
   ArrayCopy(tmp, arr);
   ArraySort(tmp);
   return tmp[ArraySize(tmp) / 2];
  }

double Average(const int &arr[])
  {
   double sum = 0;
   for(int i = 0; i < ArraySize(arr); i++)
      sum += arr[i];
   return sum / ArraySize(arr);
  }

string Duration(long secs)
  {
   long d = secs / 86400;
   long h = (secs % 86400) / 3600;
   long m = (secs % 3600) / 60;
   if(d > 0)
      return StringFormat("%dd %dh %dm", (int)d, (int)h, (int)m);
   if(h > 0)
      return StringFormat("%dh %dm", (int)h, (int)m);
   return StringFormat("%dm", (int)m);
  }

void PrintTradeError(string what)
  {
   Print(what, " failed: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
  }
//+------------------------------------------------------------------+
