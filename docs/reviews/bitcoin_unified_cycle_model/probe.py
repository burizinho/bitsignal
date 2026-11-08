import sys, requests, pandas as pd, numpy as np
sys.path.insert(0, r"D:/Projetos Gui/BitSignal")
from bitsignal.engine.indicators import calculate_rsi
from bitsignal.engine.normalizer import normalize_linear
url="https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
p=dict(assets="btc",metrics="PriceUSD,CapMrktCurUSD,CapMVRVCur,IssTotUSD,HashRate",frequency="1d",start_time="2010-07-18",page_size=10000)
rows=[];u=url
while u:
    r=requests.get(u,params=p if u==url else None,timeout=60).json(); rows+=r["data"]; u=r.get("next_page_url")
df=pd.DataFrame(rows); df["date"]=pd.to_datetime(df["time"]).dt.tz_localize(None)
for c in ["PriceUSD","CapMrktCurUSD","CapMVRVCur","IssTotUSD","HashRate"]: df[c]=pd.to_numeric(df[c])
df=df.set_index("date"); print("rows",len(df),df.index.min().date(),df.index.max().date())
px=df.PriceUSD; mc=df.CapMrktCurUSD; rc=mc/df.CapMVRVCur
df["mvrv_z"]=(mc-rc)/mc.expanding().std()
df["puell"]=df.IssTotUSD/df.IssTotUSD.rolling(365).mean()
wk=px.resample("W-SUN").last()
sma200w=wk.rolling(200).mean().reindex(df.index,method="ffill")
rsi=calculate_rsi(wk,14).reindex(df.index,method="ffill")
s111=px.rolling(111).mean(); s350=px.rolling(350).mean(); s471=px.rolling(471).mean(); e150=px.ewm(span=150,adjust=False).mean()
pib=(e150 < s471*0.745)
pit=s111/(2*s350)
h30=df.HashRate.rolling(30).mean(); h60=df.HashRate.rolling(60).mean()
cap=h30<h60; rec=(h30>h60)&(h30.shift()<=h60.shift())
hs=np.where(rec,10,np.where(cap,20,50))
def n(v,a,b): return v.apply(lambda x: normalize_linear(None if pd.isna(x) else x,a,b))
sc=(0.25*n(df.mvrv_z,.15,5)+0.20*n(px/sma200w,1,3.5)+0.20*n(df.puell,.45,2.2)
    +0.15*np.where(pib,0,n(pit,.7,1))+0.10*n(rsi,32,80)+0.10*hs)
df["score"]=sc
win={"top2013":("2013-10-01","2013-12-31"),"top2017":("2017-11-01","2018-01-15"),"top2021a":("2021-03-01","2021-05-15"),"top2021b":("2021-10-01","2021-12-15"),
     "bot2015":("2014-12-01","2015-09-30"),"bot2018":("2018-11-01","2019-02-28"),"bot2022":("2022-06-01","2023-01-31")}
for k,(a,b) in win.items():
    w=df.loc[a:b]; print(f"{k}: max {w.score.max():.1f}  min {w.score.min():.1f}  maxdate {w.score.idxmax().date()} pxmax {w.PriceUSD.max():,.0f}")
print("days>=80 by year:", df[df.score>=80].groupby(df[df.score>=80].index.year).size().to_dict())
print("days<=20 by year:", df[df.score<=20].groupby(df[df.score<=20].index.year).size().to_dict())
print("latest:", df.score.iloc[-1].round(1), "mvrv_z", round(df.mvrv_z.iloc[-1],2), "puell", round(df.puell.iloc[-1],2), "px/200w", round((px/sma200w).iloc[-1],2))
print("picycle bottom true-share (buggy formula):", ((e150*0.745)<=s471).loc["2019":].mean().round(2), " correct:", pib.loc["2019":].mean().round(2))
print("--- first crossings per cycle")
for k,(a,b) in {"c2013":("2013-01-01","2014-01-31"),"c2017":("2016-06-01","2018-02-28"),"c2021":("2020-06-01","2022-01-31")}.items():
    w=df.loc[a:b]; pk=w.PriceUSD.idxmax()
    for t in (75,80,85,90):
        x=w[w.score>=t]
        if len(x): d=x.index[0]; print(f"{k} >= {t}: first {d.date()} px {w.PriceUSD[d]:,.0f} ({w.PriceUSD[d]/w.PriceUSD.max():.0%} of peak, {(pk-d).days}d before peak {pk.date()})")
for k,(a,b) in {"b2015":("2014-06-01","2016-01-31"),"b2018":("2018-06-01","2019-06-30"),"b2022":("2022-03-01","2023-06-30"),"now":("2025-01-01","2026-12-31")}.items():
    w=df.loc[a:b]; lo=w.PriceUSD.idxmin(); x=w[w.score<=20]
    if len(x): d=x.index[0]; print(f"{k} <=20 first {d.date()} px {w.PriceUSD[d]:,.0f} (low {w.PriceUSD.min():,.0f} on {lo.date()})")
w=df.loc["2025-06-01":]; print("2025-26 monthly score:", w.score.resample("ME").mean().round(0).to_dict())
print("--- hybrid: armed if score>=80 in last 120d; sell on weekly close < EMA21w / < SMA50w")
wk_close=wk; ema21=wk.ewm(span=21,adjust=False).mean(); sma50=wk.rolling(50).mean()
scw=df.score.resample("W-SUN").max()
armed=scw.rolling(17).max()>=80
for k,(a,b) in {"c2013":("2013-01-01","2014-06-30"),"c2017":("2016-06-01","2018-06-30"),"c2021":("2020-06-01","2022-06-30")}.items():
    pk=px.loc[a:b].max()
    for name,line in (("EMA21w",ema21),("SMA50w",sma50)):
        hit=wk_close.loc[a:b][(wk_close.loc[a:b]<line.loc[a:b])&armed.loc[a:b]]
        if len(hit): d=hit.index[0]; print(f"{k} {name}: {d.date()} px {wk_close[d]:,.0f} = {wk_close[d]/pk:.0%} of peak {pk:,.0f}")
print("--- false exits: armed & <EMA21w in weeks where price later went >1.5x")
x=wk_close[(wk_close<ema21)&armed]
for d in x.index:
    fut=wk_close.loc[d:].iloc[1:53].max()
    if fut>1.5*wk_close[d]: print("  ",d.date(), f"{wk_close[d]:,.0f} -> max next yr {fut:,.0f}")
