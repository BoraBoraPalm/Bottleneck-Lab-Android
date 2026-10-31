"""Research stock candidates must fail closed on missing/late data and unproven bottlenecks."""
import sys,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_candidates as rc

TODAY="2026-10-31T09:00:00Z"

def company(i,**kw):
    base={
        "ticker":f"X{i:02d}","name":f"Example Firm {i}",
        "currency":"USD","close":50+i,"atr":2.0,
        "momentum_12_2":0.03*i,"price_date":"2026-10-30",
        "last_checked_at":"2026-10-31T00:00:00Z","eligible_for_ranking":True,
        "eur_per_unit":0.9,"fx_date":"2026-10-30",
        "theme":"Stromnetze" if i%2 else "Nicht klassifiziert",
        "theme_source":"Curated" if i%2 else "Unknown",
        "source":"Test price provider","tr_at_listed":i%3==0,
        "tr_verification":"official_AT_list_ISIN" if i%3==0 else "unverified",
        "tr_isin":"US1234567890" if i%3==0 else None,
        "fundamentals":{"assets_usd":1000000,"gross_profit_usd":400000+i*100,
        "op_cashflow_usd":100000+i*110,"net_income_usd":70000+i*150,
        "fiscal_year_end":"2025-12-31","filed":"2026-03-15",
        "source_url":"https://data.sec.gov/api/xbrl/companyfacts/CIK0000123456.json"},
        "multifactor":{"score":i*4,"momentum_score":i*5,
          "quality_score":i*3,"value_score":i*4,
          "filing_date":"2026-03-15","cohort_size":10}
    }
    base.update(kw)
    return base

class CandidatesTest(unittest.TestCase):
    def test_excludes_missing_annual_facts_and_future_filing(self):
        rows=[company(i) for i in range(1,11)]
        rows[0]["fundamentals"]=None
        rows[1]["fundamentals"]["filed"]="2026-11-10"
        rows[2]["momentum_12_2"]=None
        out=rc.current_candidates(rows,[],TODAY,required_min=2)
        qms={x["ticker"] for x in out["lists"]["quality_momentum"]}
        self.assertNotIn("X01",qms)
        self.assertNotIn("X02",qms)
        self.assertNotIn("X03",qms)
        # Underlying QVM scores are precomputed; they must also exclude future filings
        self.assertNotIn("X02",{x["ticker"] for x in out["lists"]["quality_value_momentum"]})

    def test_no_synthetic_quality_zero_score(self):
        rows=[company(i) for i in range(1,11)]
        for r in rows:r["fundamentals"]=None;r.pop("multifactor")
        result=rc.current_candidates(rows,[],TODAY)
        self.assertEqual(result["quality_momentum_coverage"],0)
        self.assertEqual(result["lists"]["quality_momentum"],[])
        self.assertEqual(result["lists"]["quality_value_momentum"],[])

    def test_bottleneck_is_thematic_hypothesis_only(self):
        rows=[company(i) for i in range(1,11)]
        news=[{"topic":"Stromnetze","title":"Transformer lead times",
               "url":"https://news.example/article","published":"Fri, 30 Oct 2026"}]
        result=rc.current_candidates(rows,news,TODAY)
        hypotheses=result["lists"]["bottleneck_hypotheses"]
        self.assertTrue(hypotheses)
        self.assertTrue(all(x["category_confidence"]=="thematic_hypothesis_only" for x in hypotheses))
        self.assertTrue(all(x["research_validated"] is False for x in hypotheses))
        self.assertTrue(all(x["theme_evidence_level"]=="sector_news_only" for x in hypotheses))
        self.assertEqual(result["methodology"]["bottleneck_hypotheses"].split(";")[0][:11],"Hand-curate")

    def test_fx_and_stop_math_and_verified_tr(self):
        out=rc.current_candidates([company(i) for i in range(1,11)],[],TODAY)
        item=out["lists"]["quality_value_momentum"][0]
        stock=next(company(i) for i in range(1,11) if f"X{i:02d}"==item["ticker"])
        self.assertAlmostEqual(item["close_eur"],stock["close"]*.9)
        self.assertAlmostEqual(item["illustrative_buy_eur"],(stock["close"]-2)*.9)
        self.assertAlmostEqual(item["illustrative_stop_eur"],(stock["close"]-7)*.9)
        self.assertEqual(item["tr_at_listed"],(int(item["ticker"][1:])%3==0))
        self.assertTrue(item["sec_source_url"].startswith("https://data.sec.gov/"))

    def test_no_stale_quotes_or_quote_without_eur(self):
        rows=[company(i) for i in range(1,11)]
        rows[1]["price_date"]="2026-10-01"
        rows[2]["eur_per_unit"]=None
        result=rc.current_candidates(rows,[],TODAY,required_min=2)
        self.assertFalse(any(x["ticker"] in {"X02","X03"} for xs in result["lists"].values() for x in xs))

    def test_qm_independent_of_missing_value(self):
        rows=[company(i) for i in range(1,11)]
        for r in rows:r.pop("multifactor")
        out=rc.current_candidates(rows,[],TODAY)
        self.assertEqual(out["quality_momentum_coverage"],10)
        self.assertEqual(out["qvm_coverage"],0)
        self.assertEqual(len(out["lists"]["quality_momentum"]),10)
        self.assertEqual(out["lists"]["quality_value_momentum"],[])

if __name__=="__main__":unittest.main()
