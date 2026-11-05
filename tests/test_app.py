from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def make_candles(n=120):
    rows=[]
    price=100.0
    for i in range(n):
        price += 0.35 if i < 60 else -0.12
        rows.append({"time":1700000000000+i*3600000,"open":price-0.1,"high":price+0.4,"low":price-0.4,"close":price,"volume":1000})
    return rows

def test_health_is_read_only():
    r=client.get("/health")
    assert r.status_code==200
    assert r.json()["mode"]=="read-only"

def test_backtest_returns_metrics_and_assumptions():
    r=client.post("/api/backtest",json={"candles":make_candles(),"strategy":"ema_cross"})
    assert r.status_code==200
    data=r.json()
    assert "max_drawdown_pct" in data["metrics"]
    assert data["assumptions"]["long_only"] is True
    assert data["assumptions"]["fee_bps_each_side"]==10

def test_backtest_rejects_non_chronological_candles():
    candles=make_candles()
    candles[20]["time"]=candles[19]["time"]
    r=client.post("/api/backtest",json={"candles":candles})
    assert r.status_code==400

def test_analytics_rejects_returns_below_minus_one():
    r=client.post("/api/analytics",json={"returns":[0.01,-1.0,0.02]})
    assert r.status_code==400

def test_analytics_returns_basic_stats():
    r=client.post("/api/analytics",json={"returns":[0.01,-0.005,0.02,-0.01,0.004],"periods_per_year":252})
    assert r.status_code==200
    assert r.json()["count"]==5
    assert "sharpe" in r.json()

def test_monte_carlo_is_reproducible():
    payload={"returns":[0.01,-0.02,0.015,0.005,-0.01],"paths":100,"steps":10,"seed":42}
    a=client.post("/api/monte-carlo",json=payload)
    b=client.post("/api/monte-carlo",json=payload)
    assert a.status_code==200
    assert a.json()["ending_equity_percentiles"]==b.json()["ending_equity_percentiles"]
