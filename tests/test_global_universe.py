"""Offline reproducibility tests for worldwide stock market discovery and ranking."""
import csv,io,sys,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import global_universe as g
import market_pipeline as v4

HEAD=["listing_key","ticker","exchange","name","asset_type","stock_sector",
      "etf_category","country","country_code","isin","aliases","instrument_group_key","scope_reason"]
def make(rows):
    text=io.StringIO()
    writer=csv.DictWriter(text,fieldnames=HEAD)
    writer.writeheader()
    for row in rows:writer.writerow(row)
    return text.getvalue().encode()

def row(ticker,exchange,country="US",isin="US0378331005",kind="Stock"):
    return {"listing_key":exchange+"::"+ticker,
            "ticker":ticker,"exchange":exchange,"name":ticker+" Example plc",
            "asset_type":kind,"country_code":country,"country":"Test country",
            "isin":isin,"stock_sector":"Industrials"}

class WorldCoverageTest(unittest.TestCase):
    def test_native_yahoo_symbols_and_no_unsupported_guessing(self):
        expected={("7203","TSE"):"7203.T",("700","HKEX"):"0700.HK",
                  ("2330","TWSE"):"2330.TW",("005930","KRX"):"005930.KS",
                  ("600519","SSE"):"600519.SS",("INFY","NSE_IN"):"INFY.NS",
                  ("VOW3","XETRA"):"VOW3.DE",("BHP","ASX"):"BHP.AX",
                  ("SHOP","TSX"):"SHOP.TO",("PETR4","B3"):"PETR4.SA",
                  ("TCS","BSE_IN"):"TCS.BO"}
        for (ticker,ex),want in expected.items():
            self.assertEqual(g.yahoo_ticker(ticker,ex),want,(ticker,ex))
        self.assertIsNone(g.yahoo_ticker("MC","Euronext")) # ambiguous Paris/Amsterdam
        # Home-market Euronext listings only: country and ISIN country agree.
        self.assertEqual(g.yahoo_ticker("SAN","Euronext","FR","FR0000120578"),"SAN.PA")
        self.assertEqual(g.yahoo_ticker("ABI","Euronext","BE","BE0974293251"),"ABI.BR")
        self.assertEqual(g.yahoo_ticker("EDP","Euronext","PT","PTEDP0AM0009"),"EDP.LS")
        self.assertIsNone(g.yahoo_ticker("XYZ","Euronext","FR","NL0000000001"))
        self.assertIsNone(g.yahoo_ticker("XYZ","Euronext","NL","NL0000000001"))
        self.assertIsNone(g.yahoo_ticker("XYZ","Euronext","ES","ES0000000001"))
        self.assertIsNone(g.yahoo_ticker("SAN","Euronext","FR",""))
        for (ticker,ex),want in {("VOE","VSE"):"VOE.VI",("ASML","AMS"):"ASML.AS",("CEZ","PSE_CZ"):"CEZ.PR",
                                 ("OTP","BSE_HU"):"OTP.BD",("SNP","BVB"):"SNP.RO"}.items():
            self.assertEqual(g.yahoo_ticker(ticker,ex),want,(ticker,ex))
        self.assertIsNone(g.yahoo_ticker("ABCD","UNKNOWN"))
        self.assertIsNone(g.yahoo_ticker("123","SSE"))
        self.assertIsNone(g.yahoo_ticker("ABC","NASDAQXX"))

    def test_global_identity_and_etf_prohibition(self):
        sample=[
            row("AAPL","NASDAQ","US"),
            row("7203","TSE","JP"),
            row("NOVN","SIX","CH"),
            row("WMT","BMV","MX"),
            row("XYZ","UNSUPPORTED","US"),
            row("SPY","NYSE ARCA","US",kind="ETF")]
        found,status=g.ingest_global_csv(make(sample),minimum=3)
        self.assertEqual(status["listed_stocks"],5)
        self.assertIn("AAPL",found)
        self.assertIn("7203.T",found)
        self.assertIn("NOVN.SW",found)
        self.assertIn("WMT.MX",found)
        self.assertNotIn("SPY",found)
        self.assertEqual(found["7203.T"]["region"],"Asien")
        self.assertEqual(found["NOVN.SW"]["region"],"Europa")
        self.assertEqual(status["unsupported_exchange_stock_count"],1)

    def test_same_mapped_symbol_different_id_removed(self):
        sample=[
            row("A.B","NASDAQ",isin="US1111111111"),
            row("A-B","NASDAQ",isin="US2222222222"),
            row("NOVN","SIX","CH")]
        found,status=g.ingest_global_csv(make(sample),minimum=1)
        self.assertNotIn("A-B",found)
        self.assertEqual(status["ambiguous_collisions"],1)

    def test_batch_geographically_balanced_without_repeats(self):
        known={}
        for region in ("Nordamerika","Europa","Asien","Ozeanien"):
            for i in range(70):
                t=region[0]+str(i).zfill(3)+region[-2:]
                known[t]={"region":region}
        curated={"MU":"Halbleiter","7203.T":"Global"}
        known.update({"MU":{"region":"Nordamerika"},"7203.T":{"region":"Asien"}})
        request=g.grouped_batch(known,curated,slot=128,batch_size=80)
        self.assertEqual(len(request),82)
        self.assertEqual(len(set(request)),len(request))
        self.assertTrue(set(curated).issubset(request))
        discovered=[x for x in request if x not in curated]
        regions={known[t]["region"] for t in discovered}
        self.assertEqual(len(regions),4)
        other=g.grouped_batch(known,curated,slot=129,batch_size=80)
        self.assertNotEqual(request,other)

    def test_existing_us_directory_survives_global_failure(self):
        # No external calls — fallback still retains US and curated names.
        with patch.object(v4,"discover_global",side_effect=RuntimeError("offline")), \
             patch.object(v4,"parse_directory",side_effect=RuntimeError("offline")):
            found,cov,errors=v4.discover({})
        self.assertIn("MU",found)
        self.assertIn("7203.T",found)
        self.assertEqual(cov["status"],"unavailable")
        self.assertTrue(errors)

if __name__=="__main__":unittest.main()
