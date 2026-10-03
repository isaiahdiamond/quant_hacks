import numpy as np
import pandas as pd

VOL_TARGET = 0.10
LOOKBACK = 60
MAX_LEV = 3.0
COST = {"es": 1e-4, "zn": 2e-4, "rty": 1e-4}
YEAR = 252


def month_ends(dates):
    i = np.arange(len(dates))
    return pd.Series(i, index=pd.PeriodIndex(dates, freq="M")).groupby(level=0).max().to_numpy()


def calendar(dates, lo=-5, hi=4):
    me = month_ends(dates)
    off = np.full(len(dates), np.nan)
    ref = np.full(len(dates), -1)
    for k, t in enumerate(me):
        for o in range(lo, hi + 1):
            if 0 <= t + o < len(dates):
                off[t + o] = o
                ref[t + o] = k
    return off, ref, me


def signal(df, me, shift=0):
    # Compound returns rather than dividing prices, because the price series jumps
    # at every roll.
    es = 1 + df.es_ret_d.fillna(0).to_numpy()
    zn = 1 + df.zn_ret_d.fillna(0).to_numpy()
    out = np.full(len(me), np.nan)
    for k in range(1, len(me)):
        a, b = me[k - 1] + 1, me[k] - 4 + shift
        if a <= b:
            out[k] = es[a : b + 1].prod() - zn[a : b + 1].prod()
    return out


def scaled(sig):
    s = pd.Series(sig)
    # Shifted so a month's own signal never enters the scale it is divided by.
    sd = s.rolling(24, min_periods=12).std().shift(1)
    return (s / sd).clip(-1, 1).to_numpy()


def leverage(ret):
    vol = ret.rolling(LOOKBACK).std() * np.sqrt(YEAR)
    # Shifted because a position held from 10 am may only use yesterday's close.
    return (VOL_TARGET / vol).clip(upper=MAX_LEV).shift(1)


def positions(df, variant="primary", shift=0):
    off, ref, me = calendar(df.index)
    sig = signal(df, me, shift)
    size = scaled(sig) if variant == "primary_z" else np.sign(sig)

    s = np.full(len(df), np.nan)
    known = ref >= 0
    s[known] = size[ref[known]]
    live = ~np.isnan(s)
    s = np.nan_to_num(s)

    month_end = live & (off >= -3 + shift) & (off <= shift)
    new_month = live & (off >= 1 + shift) & (off <= 3 + shift)

    es = np.zeros(len(df))
    zn = np.zeros(len(df))
    rty = np.zeros(len(df))

    if variant in ("primary", "primary_z"):
        zn[month_end] = s[month_end]
        es[month_end] = (s[month_end] < 0) * 1.0
        es[new_month] = 1.0
    elif variant == "cash":
        es[month_end | new_month] = 1.0
    elif variant == "rebal":
        es[month_end] = -s[month_end]
        zn[month_end] = s[month_end]
    elif variant == "both":
        es[month_end | new_month] = 1.0
        es[month_end] -= s[month_end]
        zn[month_end] = s[month_end]
    elif variant == "cash_es_rty":
        # RTY starts in 2017, and needs 60 days before it has a size, so ES carries
        # the whole position until then.
        have = leverage(df.rty_ret_d).notna().to_numpy()
        win = month_end | new_month
        es[win & have] = 0.5
        rty[win & have] = 0.5
        es[win & ~have] = 1.0

    return {
        "es": (es * leverage(df.es_ret_d)).fillna(0),
        "zn": (zn * leverage(df.zn_ret_d)).fillna(0),
        "rty": (rty * leverage(df.rty_ret_d)).fillna(0),
    }


def backtest(df, variant="primary", cost_mult=1.0, shift=0):
    pos = positions(df, variant, shift)
    pnl = pd.Series(0.0, index=df.index)
    cost = pd.Series(0.0, index=df.index)
    for k, p in pos.items():
        if (p == 0).all():
            continue
        pnl += p.shift(1).fillna(0) * df[f"{k}_ret_t"].fillna(0)
        # The trade happens at 10 am on the same row whose return we are booking.
        cost += p.diff().abs().fillna(0) * COST[k]
    return pnl - cost * cost_mult, pos


def stats(r):
    ann = r.mean() * YEAR
    vol = r.std() * np.sqrt(YEAR)
    eq = (1 + r).cumprod()
    return {
        "annual return": ann,
        "volatility": vol,
        "sharpe": ann / vol,
        "max drawdown": (eq / eq.cummax() - 1).min(),
    }


def run(df, variant="primary", cost_mult=1.0, shift=0):
    r, pos = backtest(df, variant, cost_mult, shift)
    out = stats(r)
    out["turnover"] = sum(p.diff().abs().sum() for p in pos.values()) / (len(df) / YEAR)
    return r, out


def buy_hold(df):
    return df.es_ret_t.fillna(0)


VARIANTS = ("primary", "cash", "rebal", "both", "primary_z", "cash_es_rty")


def table(df, variants=VARIANTS, mults=(0.5, 1.0, 2.0)):
    rows = {}
    for v in variants:
        for m in mults:
            rows[f"{v} {m}x cost"] = run(df, v, m)[1]
    rows["es buy and hold"] = dict(stats(buy_hold(df)), turnover=0.0)
    return pd.DataFrame(rows).T


def trades(df, variant="primary", capital=1e6, cost_mult=1.0):
    out = []
    for name, p in positions(df, variant).items():
        if (p == 0).all():
            continue
        pnl = (p.shift(1).fillna(0) * df[f"{name}_ret_t"].fillna(0) * capital).to_numpy()
        cost = (p.diff().abs().fillna(0) * COST[name] * cost_mult * capital).to_numpy()
        side = np.sign(p.to_numpy())
        grp = np.r_[0, np.cumsum(side[1:] != side[:-1])]
        for g in np.unique(grp):
            rows = np.flatnonzero(grp == g)
            if side[rows[0]] == 0:
                continue
            # The position opens at 10 am on the first row and closes at 10 am on
            # the row after the last one, so returns land one row later than sizes.
            a = rows[0]
            b = min(rows[-1] + 1, len(df) - 1)
            out.append(
                {
                    "instrument": name.upper(),
                    "entry": df.index[a].date(),
                    "exit": df.index[b].date(),
                    "direction": "long" if side[rows[0]] > 0 else "short",
                    "pnl": pnl[a + 1 : b + 1].sum() - cost[a : b + 1].sum(),
                }
            )
    return pd.DataFrame(out).sort_values("entry").reset_index(drop=True)


def random_days(df, n=1000, seed=0):
    held = (positions(df, "cash")["es"] != 0).to_numpy()
    lev = leverage(df.es_ret_d).fillna(0).to_numpy()
    ret = df.es_ret_t.fillna(0)
    month = pd.PeriodIndex(df.index, freq="M")
    groups = [(np.flatnonzero(month == m), held[month == m].sum()) for m in month.unique()]
    rng = np.random.default_rng(seed)

    out = np.empty(n)
    for i in range(n):
        p = np.zeros(len(df))
        for rows, c in groups:
            if c:
                p[rng.choice(rows, c, replace=False)] = 1.0
        s = pd.Series(p * lev, index=df.index)
        r = (s.shift(1).fillna(0) * ret) - s.diff().abs().fillna(0) * COST["es"]
        out[i] = r.mean() * YEAR / (r.std() * np.sqrt(YEAR))
    return out
