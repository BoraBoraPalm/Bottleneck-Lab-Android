"""Shared parsing, performance statistics and the Austrian tax model of the strategy audit."""
from __future__ import annotations
import json, math, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

KEST = 0.275          # Austrian capital-gains / dividend withholding tax
DIV_YIELD = 0.02      # protocol assumption for all equity portfolios
LAGS = 12             # Newey-West lags for monthly data


# ---------------------------------------------------------------- parsing
def french_sections(path) -> list[tuple[str, pd.DataFrame]]:
    """All tables of a Ken French CSV zip as (title, frame); index is the raw date key."""
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith((".csv", ".txt"))][0]
        text = z.read(name).decode("latin-1")
    out, title, header, rows = [], "", None, []

    def flush():
        nonlocal header, rows
        if header is not None and rows:
            df = pd.DataFrame(rows, columns=["key"] + header).set_index("key")
            df = df.apply(pd.to_numeric, errors="coerce")
            out.append((title.strip(), df.mask(df <= -99.99)))  # -99.99 / -999 mark missing
        header, rows = None, []

    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        first = parts[0]
        if header is not None and re.fullmatch(r"\d{4}|\d{6}|\d{8}", first) and len(parts) > len(header):
            rows.append([first] + parts[1:1 + len(header)])
        elif first == "" and len(parts) > 1 and any(parts[1:]):
            flush()
            header = [p for p in parts[1:] if p != ""]
        elif not line.strip():
            flush()
        else:
            flush()
            title = line
    flush()
    return out


def french_table(path, kind: str | None = None) -> pd.DataFrame:
    """One return table in decimals with a monthly PeriodIndex or a daily DatetimeIndex.

    kind=None: first table (factor files). kind="monthly"/"daily": first value-weighted return
    table of that frequency (the source spells the heading in several ways).
    """
    secs = french_sections(path)
    if kind is None:
        df = secs[0][1]
    else:
        hits = [d for t, d in secs if "value weight" in t.lower() and kind in t.lower()]
        if not hits:
            raise KeyError(f"{Path(path).name}: no value-weighted {kind} table; have {[t for t, _ in secs]}")
        df = hits[0]
    keys = list(df.index)
    if all(len(k) == 6 for k in keys):
        idx = pd.PeriodIndex([f"{k[:4]}-{k[4:]}" for k in keys], freq="M")
    elif all(len(k) == 8 for k in keys):
        idx = pd.to_datetime(keys, format="%Y%m%d")
    else:
        raise ValueError(f"{Path(path).name}: mixed date keys")
    out = df.copy() / 100.0
    out.index = idx
    return out[~out.index.duplicated()]


def pick(df: pd.DataFrame, *tokens: str) -> pd.Series:
    """The single column whose normalised name contains all tokens."""
    norm = {c: re.sub(r"[^A-Z0-9<=]", "", str(c).upper()) for c in df.columns}
    hits = [c for c, n in norm.items() if all(t in n for t in tokens)]
    exact = [c for c, n in norm.items() if n == "".join(tokens)]
    if len(exact) == 1:
        return df[exact[0]]
    if len(hits) != 1:
        raise KeyError(f"tokens {tokens}: matched {hits} in {list(df.columns)}")
    return df[hits[0]]


def yahoo_adjclose(path) -> pd.Series:
    """Dividend/split adjusted daily closes from a stored Yahoo chart response."""
    r = json.loads(Path(path).read_text())["chart"]["result"][0]
    idx = pd.to_datetime(r["timestamp"], unit="s").normalize()
    s = pd.Series(r["indicators"]["adjclose"][0]["adjclose"], index=idx, dtype=float).dropna()
    s = s[s > 0]
    return s[~s.index.duplicated(keep="last")].sort_index()


def to_monthly(prices: pd.Series) -> pd.Series:
    """Month-end to month-end total returns; the first and the running last month are dropped."""
    m = prices.resample("ME").last().dropna()
    last_day = prices.index[-1]
    if last_day < last_day + pd.offsets.MonthEnd(0) - pd.Timedelta(days=4):
        m = m.iloc[:-1]                      # incomplete current month
    r = m.pct_change().dropna()
    r.index = r.index.to_period("M")
    return r


def osap_long_legs(path) -> pd.DataFrame:
    """Monthly returns (decimal) of the favourable extreme portfolio of every signal."""
    import pyarrow.parquet as pq
    t = pq.read_table(path).to_pandas()
    t = t[t["port"].astype(str) != "LS"].copy()
    t["port"] = t["port"].astype(str)
    t = t[t["port"] == t.groupby("signalname")["port"].transform("max")]
    t["month"] = pd.PeriodIndex(pd.to_datetime(t["date"]), freq="M")
    return t.pivot_table(index="month", columns="signalname", values="ret", aggfunc="first") / 100.0


# ---------------------------------------------------------------- statistics
def nw_mean(x, lags: int = LAGS) -> tuple[float, float]:
    """Mean and its Newey-West t value (Bartlett kernel)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 24:
        return (float(np.mean(x)) if n else math.nan), math.nan
    m = x.mean()
    e = x - m
    L = min(lags, n - 1)
    s = e @ e / n
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / n
    se = math.sqrt(max(s, 1e-300) / n)
    return float(m), float(m / se)


def nw_ols(y, x, lags: int = LAGS):
    """OLS y = a + b x with Newey-West t values; returns (coef, t)."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(x, float)])
    n = len(y)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    Xu = X * (y - X @ b)[:, None]
    S = Xu.T @ Xu / n
    L = min(lags, n - 1)
    for l in range(1, L + 1):
        G = Xu[l:].T @ Xu[:-l] / n
        S += (1 - l / (L + 1)) * (G + G.T)
    XXi = np.linalg.inv(X.T @ X / n)
    V = XXi @ S @ XXi / n
    return b, b / np.sqrt(np.diag(V))


def holm(p) -> np.ndarray:
    p = np.asarray(p, float)
    adj = np.full(len(p), np.nan)
    ok = np.where(np.isfinite(p))[0]
    order = ok[np.argsort(p[ok])]
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (len(order) - k) * p[i])
        adj[i] = min(1.0, run)
    return adj


def bh(p) -> np.ndarray:
    """Benjamini-Hochberg adjusted p values."""
    p = np.asarray(p, float)
    adj = np.full(len(p), np.nan)
    ok = np.where(np.isfinite(p))[0]
    order = ok[np.argsort(p[ok])]
    m = len(order)
    run = 1.0
    for k in range(m - 1, -1, -1):
        run = min(run, p[order[k]] * m / (k + 1))
        adj[order[k]] = run
    return adj


def perf(r: pd.Series, rf: pd.Series, ppy: int = 12) -> dict:
    r = r.dropna()
    n = len(r)
    w = np.concatenate([[1.0], np.cumprod(1 + r.values)])
    vol = r.std(ddof=1) * math.sqrt(ppy)
    ex = (r - rf.reindex(r.index).fillna(0)).mean() * ppy
    return {"months": n, "cagr": w[-1] ** (ppy / n) - 1, "vol": vol,
            "sharpe": ex / vol if vol > 0 else math.nan,
            "maxdd": float((w / np.maximum.accumulate(w) - 1).min())}


def _share(a: pd.Series, window: int, ending_from=None) -> float:
    c = a.rolling(window).sum().dropna()
    if ending_from is not None:
        c = c[c.index >= ending_from]
    return float((c > 0).mean()) if len(c) else math.nan


def versus(r: pd.Series, m: pd.Series, rf: pd.Series, cost: float = 0.0, start=None, end=None) -> dict:
    """Strategy net of an annual cost haircut against the benchmark over the common months."""
    df = pd.concat([r, m, rf], axis=1, keys=["r", "m", "rf"]).dropna()
    if start is not None:
        df = df[df.index >= pd.Period(start, "M")]
    if end is not None:
        df = df[df.index <= pd.Period(end, "M")]
    if len(df) < 36:
        return {"months": len(df)}
    net = (1 + df.r) * (1 - cost) ** (1 / 12) - 1
    a = np.log1p(net) - np.log1p(df.m)
    mean, t = nw_mean(a.values)
    b, tb = nw_ols((net - df.rf).values, (df.m - df.rf).values)
    s, bm = perf(net, df.rf), perf(df.m, df.rf)
    gross = float((np.log1p(df.r) - np.log1p(df.m)).mean() * 12)
    worst10 = a.rolling(120).sum().min() / 10 if len(a) >= 120 else math.nan
    return {**s, "first": str(df.index[0]), "last": str(df.index[-1]), "cost": cost,
            "bench_cagr": bm["cagr"], "bench_vol": bm["vol"], "bench_sharpe": bm["sharpe"], "bench_maxdd": bm["maxdd"],
            "active": mean * 12, "t": t, "p": float(1 - stats.norm.cdf(t)) if math.isfinite(t) else math.nan,
            "gross_active": gross, "breakeven_cost": 1 - math.exp(-gross),
            "alpha": b[0] * 12, "t_alpha": tb[0], "beta": b[1],
            "te": a.std(ddof=1) * math.sqrt(12),
            "win5": _share(a, 60), "win10": _share(a, 120), "win20": _share(a, 240),
            "win10_recent": _share(a, 120, pd.Period("2010-01", "M")), "worst10": worst10}


# ---------------------------------------------------------------- Austrian tax model
def after_tax(eq, cash, w, years, ppy: int = 12, cost: float = 0.0, turnover: float = 0.0,
              div: float = DIV_YIELD, kest: float = KEST) -> float:
    """After-tax terminal value of 1 unit, liquidated at the end.

    eq/cash: period returns of the risky sleeve and of cash; w: equity share targeted for each
    period (traded only when the target changes); turnover: yearly share of the risky sleeve that
    is sold and rebought (realises gains pro rata). Dividends, interest and realised gains are
    netted within a calendar year and taxed at kest; losses are not carried forward.
    """
    e_mv = e_basis = pool = 0.0
    c_mv = 1.0
    f = min(1.0, turnover / ppy)
    n = len(eq)
    for i in range(n):
        if i == 0 or w[i] != w[i - 1]:
            tot = e_mv + c_mv
            want = w[i] * tot
            if want < e_mv - 1e-12:                      # sell part of the risky sleeve
                frac = 1 - want / e_mv
                pool += frac * (e_mv - e_basis)
                sold = e_mv - want
                e_basis *= 1 - frac
                e_mv = want
                c_mv += sold * (1 - cost)
            elif want > e_mv + 1e-12:                    # buy
                buy = want - e_mv
                e_mv += buy * (1 - cost)
                e_basis += buy * (1 - cost)
                c_mv -= buy
        d = e_mv * div / ppy                             # dividend inside the total return
        e_mv *= 1 + eq[i]
        e_basis += d
        pool += d
        interest = c_mv * cash[i]
        c_mv += interest
        pool += interest
        if f > 0 and e_mv > 0:
            g = f * (e_mv - e_basis)
            pool += g
            e_basis += g
        if i == n - 1 or years[i + 1] != years[i]:
            tax = kest * max(0.0, pool)
            pool = 0.0
            if tax > 0:
                if c_mv >= tax:
                    c_mv -= tax
                else:
                    rest = tax - c_mv
                    c_mv = 0.0
                    e_basis -= rest * e_basis / e_mv
                    e_mv -= rest
    return e_mv + c_mv - kest * max(0.0, e_mv - e_basis)


def tax_windows(r: pd.Series, m: pd.Series, rf: pd.Series, turnover: float, w: pd.Series | None = None,
                cost: float = 0.0, years_window: int = 20) -> dict:
    """After-tax terminal wealth of the strategy relative to buy-and-hold over rolling windows.

    r: risky-sleeve return of the strategy (already net of haircut costs), w: optional equity share.
    """
    df = pd.concat([r, m, rf], axis=1, keys=["r", "m", "rf"]).dropna()
    if w is not None:
        df["w"] = w.reindex(df.index)
        df = df.dropna()
    else:
        df["w"] = 1.0
    n = years_window * 12
    yrs = df.index.year.values
    ratios = []
    for s in [i for i in range(len(df) - n + 1) if df.index[i].month == 1]:
        sl = slice(s, s + n)
        a = after_tax(df.r.values[sl], df.rf.values[sl], df.w.values[sl], yrs[sl], 12, cost, turnover)
        b = after_tax(df.m.values[sl], df.rf.values[sl], np.ones(n), yrs[sl], 12, 0.0, 0.0)
        ratios.append(a / b)
    if not ratios:
        return {"tax_windows": 0}
    ratios = np.array(ratios)
    return {"tax_windows": len(ratios), "tax_median_ratio": float(np.median(ratios)),
            "tax_median_pa": float(np.median(ratios) ** (1 / years_window) - 1),
            "tax_win_share": float((ratios > 1).mean())}
