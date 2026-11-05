
"""KashTrader Pro read-only API. Public market data and research simulation only."""
from __future__ import annotations
import math, os, statistics, time
from functools import lru_cache
from typing import Literal
import numpy as np
import ccxt
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

EXCHANGES = {"binance", "bybit", "okx", "kucoin", "gateio", "kraken"}
PERIODS = {"1m":525600,"3m":175200,"5m":105120,"15m":35040,"30m":17520,"1h":8760,"2h":4380,"4h":2190,"6h":1460,"8h":1095,"12h":730,"1d":365,"1w":52}
app = FastAPI(title="KashTrader Pro API", version="1.0.0", description="Read-only exchange intelligence and transparent backtesting.")
origins = [x.strip() for x in os.getenv("KASH_ALLOWED_ORIGINS", "https://kashtrader.vercel.app,http://localhost:5500").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["Content-Type"])

@lru_cache(maxsize=12)
def exchange_for(exchange_id: str):
    key = exchange_id.lower()
    if key not in EXCHANGES or not hasattr(ccxt, key):
        raise HTTPException(400, "Exchange is not enabled. Choose: " + ", ".join(sorted(EXCHANGES)))
    try:
        ex = getattr(ccxt, key)({"enableRateLimit": True, "timeout": 15000})
        ex.load_markets()
        return ex
    except Exception as e:
        raise HTTPException(502, "Exchange initialization failed: " + str(e)[:180])

@app.get("/health")
def health():
    return {"ok": True, "service": "kashtrader-pro-api", "version": "1.0.0", "mode": "read-only"}

@app.get("/api/market/summary")
def summary(exchange: str = Query("binance"), quote: str = Query("USDT"), limit: int = Query(40, ge=5, le=150)):
    ex = exchange_for(exchange)
    try:
        tickers = ex.fetch_tickers()
    except Exception as e:
        raise HTTPException(502, "Ticker feed failed: " + str(e)[:180])
    quote = quote.upper()
    rows = []
    stables = {"USDT","USDC","BUSD","FDUSD","DAI","TUSD"}
    for symbol, t in tickers.items():
        m = ex.markets.get(symbol) or {}
        if not m or m.get("active") is False or m.get("spot") is False or not symbol.endswith("/" + quote):
            continue
        if m.get("base") in stables:
            continue
        last, volume = t.get("last"), t.get("quoteVolume")
        if last is None or volume is None:
            continue
        try:
            last, volume = float(last), float(volume)
            if not math.isfinite(last) or not math.isfinite(volume):
                continue
        except (TypeError, ValueError):
            continue
        rows.append({"symbol":symbol,"last":last,"change_pct":t.get("percentage"),"quote_volume":volume,"bid":t.get("bid"),"ask":t.get("ask")})
    rows.sort(key=lambda x:x["quote_volume"], reverse=True)
    return {"exchange":exchange,"quote":quote,"count":min(limit,len(rows)),"updated_at":int(time.time()*1000),"markets":rows[:limit]}

@app.get("/api/market/ohlcv")
def ohlcv(exchange: str = Query("binance"), symbol: str = Query("BTC/USDT"), timeframe: str = Query("1h"), limit: int = Query(500, ge=50, le=1000)):
    ex = exchange_for(exchange)
    if symbol not in ex.markets: raise HTTPException(404, symbol + " is not listed on " + exchange)
    if timeframe not in ex.timeframes: raise HTTPException(400, "Unsupported timeframe: " + timeframe)
    try: raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e: raise HTTPException(502, "OHLCV feed failed: " + str(e)[:180])
    data = [{"time":int(x[0]),"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4]),"volume":float(x[5] or 0)} for x in raw]
    return {"exchange":exchange,"symbol":symbol,"timeframe":timeframe,"count":len(data),"candles":data}

@app.get("/api/market/orderbook")
def orderbook(exchange: str = Query("binance"), symbol: str = Query("BTC/USDT"), limit: int = Query(20, ge=5, le=100)):
    ex = exchange_for(exchange)
    if symbol not in ex.markets: raise HTTPException(404, symbol + " is not listed on " + exchange)
    try: book = ex.fetch_order_book(symbol, limit=limit)
    except Exception as e: raise HTTPException(502, "Order-book feed failed: " + str(e)[:180])
    bids, asks = book.get("bids",[]), book.get("asks",[])
    bid = bids[0][0] if bids else None
    ask = asks[0][0] if asks else None
    mid = (bid + ask) / 2 if bid is not None and ask is not None else None
    return {"exchange":exchange,"symbol":symbol,"timestamp":book.get("timestamp"),"best_bid":bid,"best_ask":ask,"spread_bps":((ask-bid)/mid*10000) if mid else None,"bids":bids,"asks":asks}

@app.get("/api/market/funding")
def funding(exchange: str = Query("binance"), symbol: str = Query("BTC/USDT:USDT")):
    ex = exchange_for(exchange)
    if not ex.has.get("fetchFundingRate"): raise HTTPException(501,"Funding-rate endpoint is not supported by this exchange adapter.")
    try: f = ex.fetch_funding_rate(symbol)
    except Exception as e: raise HTTPException(502,"Funding-rate feed failed: "+str(e)[:180])
    return {"exchange":exchange,"symbol":symbol,"funding_rate":f.get("fundingRate"),"funding_timestamp":f.get("fundingTimestamp"),"next_funding_timestamp":f.get("nextFundingTimestamp"),"mark_price":f.get("markPrice")}

class Candle(BaseModel):
    time: int
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(default=0, ge=0)

class BacktestRequest(BaseModel):
    candles: list[Candle] = Field(min_length=60,max_length=1000)
    strategy: Literal["ema_cross","rsi_reversion"] = "ema_cross"
    timeframe: str = "1h"
    fast_period: int = Field(default=12,ge=2,le=100)
    slow_period: int = Field(default=26,ge=3,le=250)
    rsi_period: int = Field(default=14,ge=2,le=100)
    rsi_entry: float = Field(default=30,ge=5,le=45)
    rsi_exit: float = Field(default=60,ge=50,le=95)
    initial_cash: float = Field(default=10000,gt=0,le=1e9)
    exposure_fraction: float = Field(default=.95,gt=0,le=1)
    fee_bps: float = Field(default=10,ge=0,le=200)
    slippage_bps: float = Field(default=5,ge=0,le=200)

def ema(a, n):
    out=np.full(len(a),np.nan); 
    if len(a)>=n:
        out[n-1]=float(np.mean(a[:n])); alpha=2/(n+1)
        for i in range(n,len(a)): out[i]=alpha*a[i]+(1-alpha)*out[i-1]
    return out

def rsi(a,n):
    out=np.full(len(a),np.nan)
    if len(a)<=n:return out
    d=np.diff(a); gains=np.maximum(d,0); losses=np.maximum(-d,0)
    ag=float(np.mean(gains[:n])); al=float(np.mean(losses[:n]))
    def v(g,l): return (100.0 if g>0 else 50.0) if l==0 else 100-100/(1+g/l)
    out[n]=v(ag,al)
    for i in range(n+1,len(a)):
        ag=((n-1)*ag+gains[i-1])/n; al=((n-1)*al+losses[i-1])/n; out[i]=v(ag,al)
    return out

def metrics(equity, pnls, timeframe):
    a=np.asarray(equity,float); r=np.diff(a)/np.maximum(a[:-1],1e-12)
    annual=PERIODS.get(timeframe,365)
    sd=float(np.std(r,ddof=1)) if len(r)>1 else 0
    down=r[r<0]; dsd=float(np.std(down,ddof=1)) if len(down)>1 else 0
    peak=np.maximum.accumulate(a); dd=a/np.maximum(peak,1e-12)-1; maxdd=float(np.min(dd))
    days=max((len(a)-1)/annual*365,1/365)
    cagr=(float((a[-1]/a[0])**(1/days)-1) if a[-1]>0 and a[0]>0 else None)
    wins=[x for x in pnls if x>0]; losses=[x for x in pnls if x<0]
    grosswin=sum(wins); grossloss=abs(sum(losses))
    return {"total_return_pct":float((a[-1]/a[0]-1)*100),"cagr_pct":cagr*100 if cagr is not None else None,"max_drawdown_pct":maxdd*100,"sharpe":float(np.mean(r)/sd*math.sqrt(annual)) if sd>0 else None,"sortino":float(np.mean(r)/dsd*math.sqrt(annual)) if dsd>0 else None,"calmar":cagr/abs(maxdd) if cagr is not None and maxdd<0 else None,"win_rate_pct":len(wins)/len(pnls)*100 if pnls else None,"profit_factor":grosswin/grossloss if grossloss>0 else ("infinite" if wins else None),"average_trade_pnl":statistics.mean(pnls) if pnls else None,"trade_count":len(pnls),"ending_equity":float(a[-1])}

@app.post("/api/backtest")
def backtest(req: BacktestRequest):
    if req.strategy=="ema_cross" and req.fast_period>=req.slow_period: raise HTTPException(400,"fast_period must be smaller than slow_period.")
    c=req.candles; ts=[x.time for x in c]
    if any(ts[i]<=ts[i-1] for i in range(1,len(ts))): raise HTTPException(400,"Candles must be strictly chronological.")
    if any(x.high<max(x.open,x.close,x.low) or x.low>min(x.open,x.close,x.high) for x in c): raise HTTPException(400,"Invalid OHLC candle high/low.")
    close=np.asarray([x.close for x in c]); op=np.asarray([x.open for x in c])
    if req.strategy=="ema_cross":
        f,s=ema(close,req.fast_period),ema(close,req.slow_period)
        signal=np.isfinite(f)&np.isfinite(s)&(f>s)
    else:
        values=rsi(close,req.rsi_period); signal=np.zeros(len(c),bool); active=False
        for i,x in enumerate(values):
            if np.isfinite(x):
                if not active and x<=req.rsi_entry:active=True
                elif active and x>=req.rsi_exit:active=False
            signal[i]=active
    cash=float(req.initial_cash); qty=0.; entry=None; entryfee=0.; entrytime=None; trades=[]; eq=[cash]
    fee=req.fee_bps/10000; slip=req.slippage_bps/10000
    for i in range(1,len(c)):
        want=bool(signal[i-1]); px=float(op[i])
        if qty>0 and not want:
            fill=px*(1-slip); proceeds=qty*fill; exfee=proceeds*fee
            pnl=proceeds-exfee-qty*entry-entryfee; cash+=proceeds-exfee
            trades.append({"entry_time":entrytime,"exit_time":ts[i],"entry_price":entry,"exit_price":fill,"quantity":qty,"net_pnl":pnl,"return_pct":pnl/max(qty*entry+entryfee,1e-12)*100})
            qty=0.;entry=None;entryfee=0.;entrytime=None
        elif qty==0 and want:
            fill=px*(1+slip); allocation=cash*req.exposure_fraction
            qty=allocation/fill;entry=fill;entryfee=allocation*fee;entrytime=ts[i];cash-=allocation+entryfee
        eq.append(cash+qty*float(c[i].close))
    if qty>0:
        fill=float(c[-1].close)*(1-slip);proceeds=qty*fill;exfee=proceeds*fee
        pnl=proceeds-exfee-qty*entry-entryfee;cash+=proceeds-exfee
        trades.append({"entry_time":entrytime,"exit_time":ts[-1],"entry_price":entry,"exit_price":fill,"quantity":qty,"net_pnl":pnl,"return_pct":pnl/max(qty*entry+entryfee,1e-12)*100,"forced_final_close":True})
        eq[-1]=cash
    pnls=[float(t["net_pnl"]) for t in trades]
    return {"strategy":req.strategy,"assumptions":{"execution":"signal on prior closed candle, fill at next candle open","fee_bps_each_side":req.fee_bps,"slippage_bps_each_side":req.slippage_bps,"exposure_fraction":req.exposure_fraction,"long_only":True,"final_position":"closed at final candle close","timeframe":req.timeframe},"metrics":metrics(eq,pnls,req.timeframe),"equity_curve":eq,"trades":trades[-200:],"warnings":["Historical simulation only; it does not predict future results.","OHLC candles cannot reveal the exact intrabar path. Stop/target fills are not simulated.","Test out of sample and compare against a benchmark before relying on a strategy."]}

class AnalyticsRequest(BaseModel):
    returns:list[float]=Field(min_length=3,max_length=10000)
    periods_per_year:int=Field(default=365,ge=1,le=100000)
    initial_equity:float=Field(default=10000,gt=0,le=1e9)

@app.post("/api/analytics")
def analytics(req:AnalyticsRequest):
    r=np.asarray(req.returns,float)
    if not np.all(np.isfinite(r)) or np.any(r<=-1):raise HTTPException(400,"Returns must be finite decimals greater than -1.")
    eq=req.initial_equity*np.cumprod(1+r);eq=np.insert(eq,0,req.initial_equity)
    peak=np.maximum.accumulate(eq);dd=eq/peak-1;sd=float(np.std(r,ddof=1));down=r[r<0];dsd=float(np.std(down,ddof=1)) if len(down)>1 else 0
    years=max(len(r)/req.periods_per_year,1/req.periods_per_year);cagr=(eq[-1]/eq[0])**(1/years)-1 if eq[-1]>0 else None
    try:
        import quantstats as qs
        qsver=getattr(qs,"__version__","installed")
    except Exception:qsver=None
    return {"count":len(r),"total_return_pct":float((eq[-1]/eq[0]-1)*100),"cagr_pct":cagr*100 if cagr is not None else None,"annualized_volatility_pct":sd*math.sqrt(req.periods_per_year)*100,"sharpe":float(np.mean(r)/sd*math.sqrt(req.periods_per_year)) if sd>0 else None,"sortino":float(np.mean(r)/dsd*math.sqrt(req.periods_per_year)) if dsd>0 else None,"max_drawdown_pct":float(np.min(dd)*100),"calmar":cagr/abs(float(np.min(dd))) if cagr is not None and np.min(dd)<0 else None,"positive_period_pct":float(np.mean(r>0)*100),"ending_equity":float(eq[-1]),"quantstats_available":bool(qsver),"quantstats_version":qsver}

class MonteCarloRequest(BaseModel):
    returns:list[float]=Field(min_length=5,max_length=5000)
    initial_equity:float=Field(default=10000,gt=0)
    paths:int=Field(default=1000,ge=100,le=10000)
    steps:int=Field(default=100,ge=10,le=1000)
    seed:int=Field(default=42,ge=0,le=4294967295)

@app.post("/api/monte-carlo")
def monte_carlo(req:MonteCarloRequest):
    r=np.asarray(req.returns,float)
    if not np.all(np.isfinite(r)) or np.any(r<=-1):raise HTTPException(400,"Returns must be finite decimal returns greater than -1.")
    rng=np.random.default_rng(req.seed);sample=rng.choice(r,size=(req.paths,req.steps),replace=True)
    ends=req.initial_equity*np.prod(1+sample,axis=1)
    return {"paths":req.paths,"steps":req.steps,"seed":req.seed,"ending_equity_percentiles":{str(p):float(np.percentile(ends,p)) for p in [5,25,50,75,95]},"probability_of_loss_pct":float(np.mean(ends<req.initial_equity)*100),"warning":"Bootstrap scenarios resample supplied historical returns. Not a forecast or guarantee."}
