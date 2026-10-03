import os

import databento as db
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from dotenv import load_dotenv

load_dotenv()

DATASET = "GLBX.MDP3"
END = "2026-10-01"
OOS_START = "2024-10-01"

# One request for the whole history stalls server-side, so ask in blocks of years.
CHUNK = 3

# RTY only moved to CME in mid-2017, so it starts later than the other two.
START = {"ES": "2010-06-06", "ZN": "2010-06-06", "RTY": "2017-07-10"}


def windows(start, end):
    a, end = pd.Timestamp(start), pd.Timestamp(end)
    while a < end:
        b = min(a + pd.DateOffset(years=CHUNK), end)
        yield a.date().isoformat(), b.date().isoformat()
        a = b


def get(client, sym, rank):
    path = f"data/raw/{sym}_c{rank}.parquet"
    # Databento bills per request, so the raw pull stays on disk.
    if os.path.exists(path):
        return pd.read_parquet(path)

    parts = []
    for a, b in windows(START[sym], END):
        part = f"data/raw/{sym}_c{rank}_{a[:4]}.parquet"
        if os.path.exists(part):
            parts.append(pd.read_parquet(part))
            continue

        args = dict(
            dataset=DATASET,
            symbols=[f"{sym}.c.{rank}"],
            stype_in="continuous",
            schema="ohlcv-1h",
            start=a,
            end=b,
        )
        print(f"{sym}.c.{rank}  {a} to {b}  ${client.metadata.get_cost(**args):.2f}", flush=True)
        df = client.timeseries.get_range(**args).to_df()
        df.to_parquet(part)
        parts.append(df)

    out = pd.concat(parts).sort_index()
    out.to_parquet(path)
    return out


def pick(bars):
    ny = bars.index.tz_convert("America/New_York")
    bars = bars.assign(date=ny.date, hour=ny.hour)
    # The decision price is the last close at or before 4 pm. On a holiday early
    # close that is the short session's final print, which keeps the day and the
    # T-4 counting with it. Capping at 4 pm also avoids the 6 pm reopen, which
    # carries the same calendar date but belongs to the next session.
    day = bars[bars.hour <= 15]
    decide = day.groupby("date").tail(1).set_index("date")
    trade = bars[bars.hour == 10].set_index("date")
    # Open to close over the hours we actually trade in, for candle charts only.
    # Nothing in the strategy may read these.
    sess = bars[(bars.hour >= 10) & (bars.hour <= 15)].groupby("date")
    out = pd.DataFrame(
        {
            "decide": decide.close,
            "trade": trade.open,
            "open": trade.open,
            "high": sess.high.max(),
            "low": sess.low.min(),
            "close": decide.close,
            "id": decide.instrument_id,
            "id_trade": trade.instrument_id,
        }
    )
    # Keep a day only if both prices came from the same contract.
    return out[out.id == out.id_trade].drop(columns="id_trade")


def prev(price, id_now, price_2, id_2):
    held = id_now == id_now.shift(1)
    rolled = id_now == id_2.shift(1)
    return np.where(held, price.shift(1), np.where(rolled, price_2.shift(1), np.nan))


def build(sym, front, second):
    d = pick(front).join(pick(second), rsuffix="_2")
    out = pd.DataFrame(
        {
            "decide": d.decide,
            "trade": d.trade,
            "ret_d": d.decide / prev(d.decide, d.id, d.decide_2, d.id_2) - 1,
            "ret_t": d.trade / prev(d.trade, d.id, d.trade_2, d.id_2) - 1,
            "roll": d.id != d.id.shift(1),
            "open": d.open,
            "high": d.high,
            "low": d.low,
            "close": d.close,
        }
    )
    return out.add_prefix(sym.lower() + "_")


os.makedirs("data/raw", exist_ok=True)
client = db.Historical(os.environ["DATABENTO_API_KEY"])

df = pd.concat([build(s, get(client, s, 0), get(client, s, 1)) for s in START], axis=1)
df.index = pd.to_datetime(df.index)
df.index.name = "date"

# ES and ZN are the traded legs, so a day without both is no use to us.
df = df.dropna(subset=["es_decide", "es_trade", "zn_decide", "zn_trade"]).sort_index()

# The flows come from stock investors, so count days on the stock market's calendar.
nyse = mcal.get_calendar("XNYS").schedule(start_date="2010-06-01", end_date=END).index
df = df[df.index.isin(nyse)]

ins = df[df.index < OOS_START]
oos = df[df.index >= OOS_START]
ins.to_parquet("data/in_sample.parquet")
oos.to_parquet("data/out_of_sample.parquet")

print(f"in sample      {ins.index[0].date()} to {ins.index[-1].date()}  {len(ins)} days")
print(f"out of sample  {oos.index[0].date()} to {oos.index[-1].date()}  {len(oos)} days")
