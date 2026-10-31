"""Conservative Trade Republic Austria instrument-universe verifier.

Requires same ISIN in Trade Republic's official Austrian stock PDF and a
single matching ticker/venue identifier from an independent reference file.
This verifies inclusion in a published universe, not current orderability.
Unknowns deliberately remain unknown rather than inferred as available.
"""
import csv
import io
import re
import time
from datetime import datetime, timezone
from build_snapshot import read_url

TR_AT_PDF="https://assets.traderepublic.com/assets/files/AT/Instrument_Universe_AT_en.pdf"
IDENTIFIERS="https://raw.githubusercontent.com/adanos-software/free-ticker-database/main/data/listings.csv"
ISIN=re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
CAPTURE=re.compile(r"^\s*([A-Z]{2}[A-Z0-9]{10})(?:\s+|$)")
PRIMARY_US={"NASDAQ","NYSE","NYSE AMERICAN","NYSEAMERICAN","NYSE MKT","AMEX","NYSE ARCA","NYSEARCA"}
SUFFIX_EXCH={
    ".PA":("PARIS","EURONEXT","EPA"),".DE":("XETRA","DEUTSCHE","FRANKFURT","GERMANY"),
    ".SW":("SIX","SWISS","ZURICH"),".MI":("MILAN","BORSA ITALIANA"),
    ".AS":("AMSTERDAM","EURONEXT"),".L":("LONDON","LSE"),
    ".AX":("ASX","AUSTRALIA"),".T":("TOKYO","TSE","JPX"),
    ".ST":("STOCKHOLM","NASDAQ NORDIC"),".CO":("COPENHAGEN","NASDAQ NORDIC"),
    ".KS":("KOREA","KRX"),".TW":("TAIWAN","TWSE"),
    ".SS":("SHANGHAI","SSE"),".SZ":("SHENZHEN","SZSE")
}
def isin_values_from_pdf(blob):
    from pypdf import PdfReader
    reader=PdfReader(io.BytesIO(blob))
    result=set()
    for page in reader.pages:
        txt=page.extract_text() or ""
        for line in txt.splitlines():
            m=CAPTURE.match(line)
            if m:
                result.add(m.group(1))
    if len(result)<3000:
        raise ValueError("Trade Republic official PDF extraction too small: "+str(len(result)))
    return result

def decode_identifiers(blob):
    content=blob.decode("utf-8-sig",errors="replace")
    reader=csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or not {"ticker","isin","exchange","asset_type"}.issubset(set(reader.fieldnames)):
        raise ValueError("Identifier columns missing")
    by_key={}
    for row in reader:
        if row.get("asset_type")!="Stock":continue
        ticker=(row.get("ticker") or "").upper().strip()
        isin=(row.get("isin") or "").upper().strip()
        exchange=(row.get("exchange") or "").upper().strip()
        if not ticker or not ISIN.fullmatch(isin):continue
        by_key.setdefault(ticker,[]).append((isin,exchange))
    if len(by_key)<10000:
        raise ValueError("Too few ISIN-backed tickers from independent dataset: "+str(len(by_key)))
    return by_key

def candidate_isins(ticker, identifiers):
    ticker=ticker.upper()
    candidates=identifiers.get(ticker, [])
    # Only apply suffix normalization when an exact ticker identifier is absent.
    # Never extrapolate a match from company name alone.
    if not candidates:
        suffix=next((k for k in SUFFIX_EXCH if ticker.endswith(k)),None)
        if suffix:
            base=ticker[:-len(suffix)]
            src=identifiers.get(base,[])
            candidates=[(isin,xchg) for isin,xchg in src
                 if any(w in xchg for w in SUFFIX_EXCH[suffix])]
    elif not any(ticker.endswith(s) for s in SUFFIX_EXCH):
        candidates=[(i,e) for i,e in candidates if e in PRIMARY_US]
    unique={i for i,_ in candidates}
    if len(unique)==1:return unique.pop()
    return None

def apply_tr_filter(stocks, fetch=read_url):
    timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    status={"source":TR_AT_PDF,"mapping_source":IDENTIFIERS,"checked_at":timestamp,
            "list_loaded":False,"mapping_loaded":False,"verified":0,"unknown":0,
            "coverage_note":"AT instrument universe published by Trade Republic; no real-time tradability guarantee"}
    pdf_isins=None
    try:
        pdf_isins=isin_values_from_pdf(fetch(TR_AT_PDF,timeout=35,max_bytes=32_000_000))
        status["list_loaded"]=True
        status["official_list_count"]=len(pdf_isins)
    except Exception as exc:
        status["error_pdf"]=type(exc).__name__+": "+str(exc)[:200]
    ids=None
    try:
        ids=decode_identifiers(fetch(IDENTIFIERS,timeout=35,max_bytes=24_000_000))
        status["mapping_loaded"]=True
    except Exception as exc:
        status["error_mapping"]=type(exc).__name__+": "+str(exc)[:200]
    for row in stocks:
        row["tr_at_listed"]=False
        row["tr_verification"]="unverified"
        row.pop("tr_isin",None)
        if pdf_isins is None or ids is None:continue
        isin=(row.get("reference_isin") or "").upper()
        if not ISIN.fullmatch(isin):
            isin=candidate_isins(row.get("ticker",""),ids)
        if not isin:continue
        row["tr_isin"]=isin
        if isin in pdf_isins:
            row["tr_at_listed"]=True
            row["tr_verification"]="official_AT_list_ISIN"
            status["verified"]+=1
        else:
            row["tr_verification"]="ISIN_not_in_AT_list"
    status["unknown"]=len(stocks)-status["verified"]
    return status
