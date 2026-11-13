#!/usr/bin/env python3
"""Turn the raw downloads into the frozen, compact input bundle of the study (run once in CI).

French zip files are kept byte-identical. The two large OSAP parquet files are reduced to the
extreme value-weighted portfolios per signal, Yahoo responses to month-end total returns.
The manifest keeps the SHA-256 of every original download.
"""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402


def osap_compact(src: Path, dst: Path) -> dict:
    import pyarrow.parquet as pq
    info = {}
    for name, tag in (("PredictorAltPorts_QuintilesVW.parquet", "vw"),
                      ("PredictorAltPorts_LiqScreen_ME_gt_NYSE20pct.parquet", "liq")):
        t = pq.read_table(src / name).to_pandas()
        info[tag] = {"columns": list(t.columns), "rows": int(len(t)), "signals": int(t.signalname.nunique()),
                     "ports": sorted(t.port.astype(str).unique().tolist())[:30]}
        t["port"] = t["port"].astype(str)
        t = t[t.port != "LS"].copy()
        t["month"] = pd.PeriodIndex(pd.to_datetime(t["date"]), freq="M").astype(str)
        g = t.groupby("signalname")["port"]
        hi, lo = t[t.port == g.transform("max")], t[t.port == g.transform("min")]
        piv = lambda d, v: d.pivot_table(index="month", columns="signalname", values=v, aggfunc="first")
        piv(hi, "ret").astype("float32").to_parquet(dst / f"long_{tag}.parquet", compression="zstd")
        if tag == "vw":
            piv(lo, "ret").astype("float32").to_parquet(dst / "short_vw.parquet", compression="zstd")
            if "Nlong" in t.columns:
                piv(hi, "Nlong").astype("float32").to_parquet(dst / "nlong_vw.parquet", compression="zstd")
        info[tag]["long_port_by_signal_sample"] = hi.groupby("signalname").port.first().head(8).to_dict()
    shutil.copy2(src / "SignalDoc.csv", dst / "SignalDoc.csv")
    return info


def yahoo_compact(src: Path, dst: Path) -> dict:
    audit, cols = {}, {}
    for f in sorted(src.glob("*.json")):
        sym = f.stem
        try:
            meta = json.loads(f.read_text())["chart"]["result"][0].get("meta", {})
            px = lib.yahoo_adjclose(f)
            daily = px.pct_change().dropna()
            cols[sym] = lib.to_monthly(px)
            audit[sym] = {"currency": meta.get("currency"), "type": meta.get("instrumentType"),
                          "name": meta.get("longName") or meta.get("shortName"),
                          "first": str(px.index[0].date()), "last": str(px.index[-1].date()), "days": int(len(px)),
                          "max_abs_daily_move": float(daily.abs().max()),
                          "moves_over_25pct": [str(d.date()) for d in daily.index[daily.abs() > 0.25]][:20]}
        except Exception as e:  # noqa: BLE001 - recorded, symbol skipped
            audit[sym] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    pd.DataFrame(cols).sort_index().to_csv(dst / "monthly_returns.csv", float_format="%.8f")
    (dst / "audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False))
    return {"symbols": len(cols), "errors": [s for s, a in audit.items() if "error" in a]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    for sub in ("french", "osap", "yahoo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    for f in sorted((raw / "french").glob("*.zip")):
        shutil.copy2(f, out / "french" / f.name)
    manifest = json.loads((raw / "manifest.json").read_text())
    manifest["compact"] = {"osap": osap_compact(raw / "osap", out / "osap"),
                           "yahoo": yahoo_compact(raw / "yahoo", out / "yahoo")}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(json.dumps(manifest["compact"], indent=1, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
