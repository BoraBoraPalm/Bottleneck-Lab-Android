"""Global primary-stock discovery with exchange-specific Yahoo symbol conversion.

Not a completeness claim. Uses Adanos MIT ticker reference as a *security
directory*, not as a verified live quote. A symbol is only eligible for market
ranking after a real recent Yahoo/Stooq price and EUR FX/volume verification.
Canonical primary keys are venue::ticker. Ambiguous/unsupported venues are
skipped rather than guessed.
"""
import csv
import io
import re
from collections import Counter
from build_snapshot import read_url

SOURCE="https://raw.githubusercontent.com/adanos-software/free-ticker-database/main/data/core_listings.csv"
# Every supported exchange code has a documented exchange-specific Yahoo suffix.
# Codes are exact source exchange identifiers, never inferred from issuer names.
VENUES={
    "XETRA":".DE","FSX":".F","LSE":".L","TSE":".T","TPEX":".TWO",
    "TWSE":".TW","HKEX":".HK","SSE":".SS","SZSE":".SZ",
    "KRX":".KS","KOSDAQ":".KQ","NSE_IN":".NS","BSE_IN":".BO",
    "TSX":".TO","TSXV":".V","ASX":".AX","B3":".SA",
    "SIX":".SW","OMX_STO":".ST","OMX_CPH":".CO","OMX_HEL":".HE",
    "NASDAQ_STO":".ST","NASDAQ_CPH":".CO","NASDAQ_HEL":".HE",
    "BME":".MC","BIST":".IS","BVL":".LM","WSE":".WA",
    "SGX":".SI","NZX":".NZ","JSE":".JO","TASE":".TA",
    "BMV":".MX","BVC":".CL","BCBA":".BA","IDX":".JK",
    "SET":".BK","MYX":".KL","PSE":".PS","HOSE":".VN"
}
# Vendor names change; source exchanges that are ambiguous (e.g. generic
# Euronext) deliberately require extra market metadata before using a suffix.
US_VENUES={"NASDAQ","NYSE","NYSE ARCA","NYSE MKT","AMEX","BATS","CBOE"}
SYMBOL=re.compile(r"^[A-Z0-9][A-Z0-9 ._-]{0,13}$")
COUNTRIES={
    "US":"Nordamerika","CA":"Nordamerika",
    "MX":"Lateinamerika","BR":"Lateinamerika","CL":"Lateinamerika","AR":"Lateinamerika",
    "PE":"Lateinamerika","CO":"Lateinamerika",
    "AU":"Ozeanien","NZ":"Ozeanien",
    "ZA":"Afrika","EG":"Afrika","NG":"Afrika","MA":"Afrika",
    "SA":"Naher Osten","AE":"Naher Osten","QA":"Naher Osten","KW":"Naher Osten",
    "IL":"Naher Osten","TR":"Naher Osten",
}
ASIA={"JP","KR","TW","CN","HK","IN","SG","ID","MY","TH","PH","VN","PK","BD",
      "LK","NP","MM","KH","MO","MN"}
EUROPE={"AT","DE","FR","IT","NL","BE","ES","PT","IE","GB","CH","SE","NO","DK","FI",
        "PL","CZ","HU","RO","GR","LT","LV","EE","LU","SI","SK","HR","RS","BG",
        "CY","MT","IS","UA","RU"}
REGIONS=("Europa","Asien","Nordamerika","Lateinamerika","Ozeanien","Naher Osten","Afrika","Unbekannt")

def region_of(country):
    code=(country or "").upper()
    if code in COUNTRIES:return COUNTRIES[code]
    if code in ASIA:return "Asien"
    if code in EUROPE:return "Europa"
    return "Unbekannt"

def yahoo_ticker(symbol,exchange):
    """Convert *supported venue* native symbol, never a generic same-ticker match."""
    ticker=str(symbol or "").strip().upper()
    venue=str(exchange or "").strip().upper()
    if not SYMBOL.fullmatch(ticker):return None
    if ticker.isdigit() and len(ticker)>6:return None
    # Disallow unsupported symbols instead of constructing a potentially
    # *different company's* Yahoo quote.
    base=ticker.replace(" ","-").replace(".","-").replace("_","-")
    if venue in US_VENUES:
        return base if base[0].isalpha() and len(base)<=11 else None
    suffix=VENUES.get(venue)
    if not suffix:return None
    if venue=="HKEX" and ticker.isdigit():
        base=ticker.zfill(4) if len(ticker)<=4 else ticker
    if venue in ("SSE","SZSE") and (not ticker.isdigit() or len(ticker)!=6):
        return None
    if venue in ("TSE","TWSE","KRX","KOSDAQ","NSE_IN","BSE_IN","B3","XETRA","LSE","ASX") and len(base)>12:
        return None
    return base+suffix

def ingest_global_csv(blob,minimum=2000):
    """Returns primary Yahoo quote candidates and honest discovery coverage."""
    records=csv.DictReader(io.StringIO(blob.decode("utf-8-sig",errors="replace")))
    headers=set(records.fieldnames or [])
    required={"listing_key","ticker","exchange","name","asset_type","country_code","isin"}
    if not required.issubset(headers):
        raise ValueError("Unexpected global reference schema: "+str(sorted(headers)))
    listed=Counter();unsupported=Counter();found={}
    collisions=0
    known_keys=set()
    for row in records:
        if row.get("asset_type")!="Stock":continue
        exchange=(row.get("exchange") or "").strip().upper()
        original=(row.get("ticker") or "").strip()
        name=(row.get("name") or "").strip()
        identity=(row.get("listing_key") or "").strip()
        if not identity or not name or not original:continue
        if identity in known_keys:continue
        known_keys.add(identity)
        listed[exchange]+=1
        converted=yahoo_ticker(original,exchange)
        if not converted:
            unsupported[exchange]+=1
            continue
        country=(row.get("country_code") or "").upper().strip()
        info={
           "name":name[:130],
           "exchange":exchange,
           "country":(row.get("country") or "")[:75],
           "country_code":country,
           "region":region_of(country),
           "listing_key":identity,
           "reference_isin":(row.get("isin") or "").strip().upper(),
           "stock_sector":(row.get("stock_sector") or "").strip()[:80],
           "reference_source":"Adanos primary listing dataset",
           "reference_url":SOURCE
        }
        if converted in found:
            # Multiple venue keys mapping to one Yahoo symbol means that the
            # instrument identity is ambiguous. Never silently overwrite it.
            if found[converted].get("listing_key")!=identity:
                collisions+=1
                found.pop(converted,None)
            continue
        found[converted]=info
    if len(found)<minimum:
        raise ValueError(f"Only {len(found)} global primary stocks mapped (required {minimum})")
    return found,{
       "source":SOURCE,"listed_stocks":sum(listed.values()),
       "mapped_symbol_count":len(found),
       "ambiguous_collisions":collisions,
       "unsupported_exchange_stock_count":sum(unsupported.values()),
       "unsupported_by_exchange":dict(unsupported.most_common(15)),
       "note":"Coverage is a directory, not a guarantee of Yahoo quotes or broker tradability"
    }

def discover_global(fetch=read_url):
    return ingest_global_csv(fetch(SOURCE,timeout=40,max_bytes=18_000_000))

def grouped_batch(known,curated,slot,batch_size=205):
    """Rotating, geographically balanced selection; curations always included.

    Every region represented when it has eligible noncurated listings; rotates
    through stable sorted tickers per region. No repetition in a single run.
    """
    regions={r:[] for r in REGIONS}
    for ticker,meta in known.items():
        if ticker in curated:continue
        region=meta.get("region") or "Unbekannt"
        regions.setdefault(region,[]).append(ticker)
    for arr in regions.values():arr.sort()
    active=[r for r in REGIONS if regions.get(r)]
    if not active or batch_size<=0:return list(curated)
    quota,rem=divmod(batch_size,len(active))
    picks=[]
    for j,r in enumerate(active):
        arr=regions[r]
        take=min(len(arr),quota+(1 if j<rem else 0))
        if not take:continue
        # Even with fixed batch_size every subsequent slot visits a new slice.
        begin=((slot*max(1,take))+j*13)%len(arr)
        picks.extend((arr+arr)[begin:begin+take])
    return list(dict.fromkeys(list(curated)+picks))
