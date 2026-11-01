"""Search publishes names independently of strategy eligibility and quote coverage."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from search_catalog import catalog_payload, write_catalog


class SearchCatalogTests(unittest.TestCase):
    def test_unknown_prices_and_ineligible_titles_remain_searchable(self):
        known={"MSFT":{"name":"Microsoft Corporation","eligible_global_ranking":False},
               "NEW":{"name":"New Company","exchange":"NASDAQ"}}
        rows=catalog_payload(known)["stocks"]
        self.assertEqual({row["ticker"] for row in rows},{"MSFT","NEW"})
        self.assertEqual(next(r for r in rows if r["ticker"]=="MSFT")["name"],"Microsoft Corporation")

    def test_only_public_identity_fields_are_published(self):
        row=catalog_payload({"NVDA":{"name":"NVIDIA","reference_isin":"US67066G1040",
            "reference_close_eur":100,"fundamentals":{"private":True},"eligible_global_ranking":False}})["stocks"][0]
        self.assertEqual(set(row),{"ticker","name","reference_isin"})

    def test_invalid_rows_and_missing_names_are_handled(self):
        rows=catalog_payload({"A":{},"B":None,"":{},"LONG":{"name":"x"*1000}})["stocks"]
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["name"],"A")
        self.assertEqual(len(rows[1]["name"]),160)

    def test_atomic_json_output_preserves_unicode_names(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"nested"/"search-index.json"
            count=write_catalog({"DEMO.DE":{"name":"Müller & Söhne"}},target)
            self.assertEqual(count,1)
            self.assertEqual(json.loads(target.read_text())["stocks"][0]["name"],"Müller & Söhne")
            self.assertFalse(target.with_suffix(".tmp").exists())


if __name__=="__main__":unittest.main()
