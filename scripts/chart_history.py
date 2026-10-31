"""Compact, per-ticker historical price charts for static GitHub Pages.

A chart is loaded by the browser only when a stock is expanded. The series is
Yahoo's dividend/split-adjusted close rescaled to the last quoted native close,
so a single *current* EUR-to-local FX rate can locate today's EUR limit lines.
It is NOT a historical EUR total-return chart or a broker quote.
"""
import json
import math
import os
import re
from pathlib import Path

ROOT=Path("docs/charts")
SYMBOL=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,19}$")

def chart_file(symbol):
    if not isinstance(symbol,str) or not SYMBOL.fullmatch(symbol) or symbol in (".",".."):
        raise ValueError("Unsafe symbol")
    return ROOT/(symbol+".json")

def chart_payload(symbol,bars,currency,source):
    if source!="Yahoo Finance" or len(bars)<30:
        return None
    last=bars[-1]
    if len(last)<6:return None
    try:
        last_close=float(last[3]);last_adjusted=float(last[5])
        scale=last_close/last_adjusted
        if not math.isfinite(scale) or scale<=0:return None
    except (TypeError,ValueError,ZeroDivisionError):
        return None
    points=[]
    for bar in bars:
        try:
            adjusted=float(bar[5])
            value=adjusted*scale
            if math.isfinite(value) and value>0 and isinstance(bar[0],str):
                points.append([bar[0],round(value,6)])
        except (IndexError,TypeError,ValueError):
            continue
    if len(points)<30:return None
    if any(a[0]>=b[0] for a,b in zip(points,points[1:])):
        return None
    return {"version":1,"ticker":symbol,"currency":currency,"asof":last[0],
            "source":source,"basis":"adjusted close normalized to latest raw close",
            "points":points}

def write_chart(chart):
    if not chart:return False
    filename=chart_file(chart["ticker"])
    filename.parent.mkdir(parents=True,exist_ok=True)
    tmp=filename.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8") as f:
        json.dump(chart,f,ensure_ascii=False,separators=(",",":"))
    os.replace(tmp,filename)
    return True

def chart_is_current(symbol,price_date):
    try:
        with chart_file(symbol).open("r",encoding="utf-8") as f:
            head=json.load(f)
        return head.get("asof")==price_date and len(head.get("points",[]))>=30
    except (ValueError,OSError,TypeError,KeyError):
        return False

def chart_count():
    if not ROOT.is_dir():return 0
    return len(list(ROOT.glob("*.json")))
