
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import json, time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

LATEST_JSON = DATA_DIR / "latest.json"
LATEST_CSV = DATA_DIR / "latest.csv"

TWSE_UNIVERSE = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_UNIVERSE = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
HEADERS={"User-Agent":"Mozilla/5.0"}

SCAN_LIMIT = 500
TARGET_COUNT = 10
MIN_SCORE = 68
MIN_WIN_RATE = 50

def get_universe():
    rows=[]
    try:
        for r in requests.get(TWSE_UNIVERSE,headers=HEADERS,timeout=20).json():
            c=str(r.get("公司代號","")).strip()
            n=str(r.get("公司簡稱","")).strip()
            if c.isdigit() and len(c)==4:
                rows.append({"code":c,"ticker":c+".TW","name":n,"market":"上市"})
    except Exception:
        pass
    try:
        for r in requests.get(TPEX_UNIVERSE,headers=HEADERS,timeout=20).json():
            c=str(r.get("公司代號","")).strip()
            n=str(r.get("公司簡稱","")).strip()
            if c.isdigit() and len(c)==4:
                rows.append({"code":c,"ticker":c+".TWO","name":n,"market":"上櫃"})
    except Exception:
        pass
    return pd.DataFrame(rows).drop_duplicates("ticker")

def ind(d):
    d=d.copy()
    c,h,l,v=d["Close"],d["High"],d["Low"],d["Volume"]
    d["MA10"]=c.rolling(10).mean(); d["MA20"]=c.rolling(20).mean(); d["MA60"]=c.rolling(60).mean()
    e12=c.ewm(span=12,adjust=False).mean(); e26=c.ewm(span=26,adjust=False).mean()
    dif=e12-e26; dea=dif.ewm(span=9,adjust=False).mean(); d["MACD"]=dif-dea
    lo=l.rolling(9).min(); hi=h.rolling(9).max()
    rsv=(c-lo)/(hi-lo).replace(0,np.nan)*100
    d["K"]=rsv.ewm(alpha=1/3,adjust=False).mean()
    d["D"]=d["K"].ewm(alpha=1/3,adjust=False).mean()
    d["J"]=3*d["K"]-2*d["D"]
    d["VM20"]=v.rolling(20).mean()
    d["VALUE20"]=(c*v).rolling(20).mean()
    d["HH20"]=h.rolling(20).max().shift(1)
    d["HH60"]=h.rolling(60).max().shift(1)
    d["RET5"]=c.pct_change(5); d["RET20"]=c.pct_change(20)
    return d

def score_daily(d,i):
    if i<70:return 0,[],[]
    x,p=d.iloc[i],d.iloc[i-1]
    s=0;r=[];risk=[]
    if x["Close"]>x["MA10"]: s+=8;r.append("站上MA10")
    if x["MA10"]>x["MA20"]: s+=10;r.append("MA10>MA20")
    if x["MA20"]>x["MA60"]: s+=7;r.append("MA20>MA60")
    if x["MA10"]>p["MA10"]: s+=3;r.append("MA10上彎")
    if x["MACD"]>p["MACD"]: s+=8;r.append("MACD轉強")
    if x["MACD"]<0 and x["MACD"]>p["MACD"]: s+=5;r.append("MACD綠柱縮短")
    if x["MACD"]>0: s+=4
    if x["J"]>p["J"]: s+=6;r.append("J值上彎")
    if p["J"]<50 and x["J"]>p["J"]: s+=4;r.append("J值低檔轉強")
    if x["K"]>x["D"]: s+=2
    vr=x["Volume"]/x["VM20"] if x["VM20"]>0 else np.nan
    if np.isfinite(vr) and .7<=vr<=1.7: s+=4;r.append("量能健康")
    if np.isfinite(vr) and vr>=1.15 and x["Close"]>p["Close"]: s+=7;r.append("價漲量增")
    if p["Volume"]<p["VM20"] and x["Volume"]>p["Volume"]: s+=3;r.append("量縮後回溫")
    if x["Close"]>x["HH20"]: s+=5;r.append("突破20日高")
    if x["Close"]>x["HH60"]: s+=4;r.append("突破60日高")
    gap=(x["Close"]/x["MA10"]-1)*100
    if 0<=gap<=5.5: s+=6;r.append("乖離合理")
    elif gap>10: s-=10;risk.append("短線乖離過大")
    if x["RET5"]>0 and x["RET5"]<0.12: s+=4
    if x["RET20"]>0: s+=3
    if x["Close"]<x["MA20"]: s-=10;risk.append("跌破MA20")
    if x["J"]>105: s-=6;risk.append("J值過熱")
    if x["Volume"]>x["VM20"]*2.3 and x["Close"]<x["Open"]:
        s-=14;risk.append("爆量長黑")
    return max(0,min(100,int(round(s)))),r,risk

def score_60m(ticker):
    try:
        d=yf.download(ticker,period="60d",interval="60m",auto_adjust=False,progress=False,threads=False)
        if d.empty:return 0,[]
        if isinstance(d.columns,pd.MultiIndex):
            d.columns=d.columns.get_level_values(0)
        d=ind(d.dropna())
        if len(d)<30:return 0,[]
        x,p=d.iloc[-1],d.iloc[-2]
        s=0;r=[]
        if x["Close"]>x["MA10"]:s+=5;r.append("60分K站上MA10")
        if x["MA10"]>x["MA20"]:s+=7;r.append("60分K MA10>MA20")
        if x["MA10"]>p["MA10"]:s+=3;r.append("60分K MA10上彎")
        if x["MACD"]>p["MACD"]:s+=5;r.append("60分K MACD轉強")
        if x["MACD"]<0 and x["MACD"]>p["MACD"]:s+=4;r.append("60分K綠柱縮短")
        if x["J"]>p["J"]:s+=4;r.append("60分K J值上彎")
        return min(28,s),r
    except Exception:
        return 0,[]

def backtest(d,threshold=58,horizon=10):
    wins=[];rets=[]
    for i in range(max(90,len(d)-420),len(d)-horizon):
        sc,_,_=score_daily(d,i)
        if sc<threshold: continue
        e=float(d.iloc[i]["Close"])
        f=d.iloc[i+1:i+1+horizon]
        if f.empty: continue
        ret=float(f.iloc[-1]["Close"]/e-1)
        dd=float(f["Low"].min()/e-1)
        wins.append(1 if (ret>=0.03 and dd>=-0.06) else 0)
        rets.append(ret)
    if not wins:return 0,None,None
    return len(wins),round(100*sum(wins)/len(wins),1),round(100*np.mean(rets),2)

def analyze(meta,d):
    if d is None or len(d)<160:return None
    d=ind(d.dropna()); x=d.iloc[-1]
    if x["Close"]<12 or x["VALUE20"]<50_000_000 or x["VM20"]<300_000:return None

    daily,reasons,risks=score_daily(d,len(d)-1)
    s60,r60=score_60m(meta["ticker"]); reasons+=r60
    sig,wr,avg=backtest(d)

    conf=min(1,sig/15) if sig else 0
    wr_eff=wr if wr is not None else 50
    btadj=((wr_eff-50)/50)*18*conf + min(8,sig*.4)

    penalty=0
    if sig<4:
        penalty-=6; risks.append("回測樣本偏少")
    elif sig<8:
        penalty-=2

    if wr is not None and sig>=8:
        if wr<45:
            penalty-=12; risks.append("歷史勝率偏低")
        elif wr<50:
            penalty-=5

    final=int(max(0,min(100,round(daily+s60+btadj+penalty))))

    if final>=90 and (wr is None or sig<8 or wr>=60): grade="S級首選"
    elif final>=85 and (wr is None or sig<8 or wr>=58): grade="A+主選"
    elif final>=78: grade="A級主選"
    elif final>=68: grade="B級觀察"
    else: grade="未入選"

    return {
        **meta,
        "score":final,"grade":grade,"close":round(float(x["Close"]),2),
        "entry_low":round(max(float(x["MA10"]),float(x["Close"])*.985),2),
        "entry_high":round(float(x["Close"])*1.01,2),
        "stop":round(min(float(x["MA20"]),float(x["Close"])*.94),2),
        "resistance":round(max(float(x["HH20"]) if np.isfinite(x["HH20"]) else float(x["Close"]),float(x["Close"])*1.06),2),
        "win_rate":wr,"signals":sig,"avg_return":avg,
        "daily_score":daily,"score_60m":s60,
        "reasons":reasons[:12],"risks":risks or ["暫無明顯警訊"],
        "avg_value_m":round(float(x["VALUE20"])/1_000_000,1)
    }

def main():
    u=get_universe()
    if u.empty:
        raise RuntimeError("無法取得上市櫃股票池")

    metas=u.head(SCAN_LIMIT).to_dict("records")
    out=[]; chunk=40

    for s in range(0,len(metas),chunk):
        part=metas[s:s+chunk]
        tickers=[m["ticker"] for m in part]
        try:
            raw=yf.download(tickers,period="2y",interval="1d",group_by="ticker",
                            auto_adjust=False,threads=True,progress=False)
        except Exception:
            continue
        many=len(tickers)>1
        for m in part:
            try:
                d=raw[m["ticker"]] if many else raw
                r=analyze(m,d[["Open","High","Low","Close","Volume"]])
                if r:out.append(r)
            except Exception:
                pass
        time.sleep(.1)

    out.sort(key=lambda x:(x["score"],x["win_rate"] or 0,x["signals"],x["avg_value_m"]),reverse=True)

    quality=[]
    for x in out:
        if x["score"]<MIN_SCORE: continue
        if x["signals"]>=8 and x["win_rate"] is not None and x["win_rate"]<MIN_WIN_RATE: continue
        quality.append(x)

    selected=quality[:TARGET_COUNT]

    now=datetime.now(ZoneInfo("Asia/Taipei"))
    payload={
        "generated_at":now.strftime("%Y-%m-%d %H:%M:%S"),
        "analyzed_count":len(out),
        "quality_count":len(quality),
        "results":selected
    }

    LATEST_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

    pd.DataFrame([{
        "排名":i+1,"代號":x["code"],"名稱":x["name"],"市場":x["market"],"評分":x["score"],"等級":x["grade"],
        "收盤":x["close"],"進場低":x["entry_low"],"進場高":x["entry_high"],"停損":x["stop"],"壓力":x["resistance"],
        "回測勝率%":x["win_rate"],"樣本":x["signals"],"平均報酬%":x["avg_return"],"日K":x["daily_score"],"60分K":x["score_60m"]
    } for i,x in enumerate(selected)]).to_csv(LATEST_CSV,index=False,encoding="utf-8-sig")

    print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
