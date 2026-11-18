"""Regression: index only dated source-linked PF and local business headlines."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from desk_coverage import (
    PF_START_UTC, pf_cutoff, pf_match, local_business_match,
    from_telugu_publisher, index_gdelt, PF_QUERIES,
    REGIONAL_BUSINESS_QUERIES
)
import rss_sources

class DeskCoverageTests(unittest.TestCase):
    def test_pf_cutoff_from_14_nov_ist(self):
        d=pf_cutoff(datetime(2026,11,18,17,tzinfo=timezone.utc))
        self.assertEqual(d,PF_START_UTC)
        self.assertEqual(d.isoformat(),"2026-11-13T18:30:00+00:00")

    def test_reader_finance_categories(self):
        positives=[
            "RBI revises gold loan repayment rules for borrowers",
            "Income tax return refund delay: steps to follow",
            "NPS retirement corpus withdrawal rule explained",
            "Health insurance policyholders face new cashless claims process",
            "Mutual fund SIP planning and withdrawal advice",
            "How does UPI fraud protection work for bank customers?",
            "వడ్డీ రేటు పెరిగితే హోమ్ లోన్ ఈఎంఐ ఎంత?",
        ]
        for title in positives:
            with self.subTest(title=title):self.assertTrue(pf_match(title))
        self.assertFalse(pf_match("Hyderabad pharma company reports record quarterly revenue"))

    def test_reject_generic_finance_market_data(self):
        self.assertFalse(pf_match("Nifty reaches new high, stock market investors rejoice"))
        self.assertFalse(pf_match("Bank reports quarterly net profit"))

    def test_regional_company_watchlist(self):
        for title,region in [
           ("Skyroot Aerospace signs new Hyderabad contract","hyderabad"),
           ("Bharat Biotech expansion in Hyderabad","hyderabad"),
           ("Amara Raja Group unveils factory investment","andhra-pradesh"),
           ("Sri City industrial park expansion","andhra-pradesh"),
           ("Telangana startups win funding","telangana"),
           ("Visakhapatnam port cargo handling expansion","andhra-pradesh"),
        ]:
           with self.subTest(title=title):self.assertEqual(local_business_match(title),region)

    def test_nonbusiness_politics_does_not_enter_company_news(self):
        self.assertIsNone(local_business_match("Telangana assembly discusses welfare bill"))
        self.assertIsNone(local_business_match("Hyderabad youth festival attracts students"))

    def test_gdelt_pf_is_indexed_not_alleged_published(self):
        row={"title":"New health insurance cashless claim process for policyholders",
             "url":"https://news.example.in/india/insurance-claim-rule",
             "domain":"news.example.in","language":"English",
             "seendate":"20261118T173501Z"}
        item=index_gdelt(row,"pf")
        self.assertEqual(item["desk"],"personal-finance")
        self.assertEqual(item["sector"],"Personal Finance")
        self.assertEqual(item["time_basis"],"indexed")
        self.assertNotIn("body",item)
        self.assertNotIn("description",item)

    def test_gdelt_index_rejects_unrelated_and_protected(self):
        row={"title":"Hyderabad minister launches new welfare programmes",
             "url":"https://example.in/news/minister"}
        self.assertIsNone(index_gdelt(row,"regional-business"))
        self.assertIsNone(index_gdelt(row,"pf"))
        protected={"title":"How to plan your retirement corpus",
                   "url":"https://www.livemint.com/money/retirement-tips"}
        self.assertIsNone(index_gdelt(protected,"pf"))

    def test_telugu_rss_is_one_url_with_multiple_flags(self):
        row={"url":"https://telugu.oneindia.com/news/telangana/finance-123.html",
             "title":"తెలంగాణ బ్యాంకు ఖాతా పొదుపు వడ్డీపై కొత్త మార్పు",
             "region":"telangana","desk":"telugu-patrikalu",
             "source":"Oneindia Telugu • RSS"}
        result=from_telugu_publisher([row])
        self.assertTrue(result[row["url"]]["reader_finance"])
        self.assertEqual(row["desk"],"telugu-patrikalu")
        self.assertEqual(len(result),1)

    def test_rbi_verified_official_feed_names(self):
        urls=[url for source,url,kind in rss_sources.FEEDS if source=="RBI"]
        self.assertIn("https://www.rbi.org.in/speeches_rss.xml",urls)
        self.assertIn("https://www.rbi.org.in/Publication_rss.xml",urls)

    def test_dedicated_queries_do_not_hammer_source(self):
        self.assertGreaterEqual(len(PF_QUERIES),6)
        self.assertGreaterEqual(len(REGIONAL_BUSINESS_QUERIES),6)
        self.assertTrue(all("sourcelang:english" in q for _,q in PF_QUERIES+REGIONAL_BUSINESS_QUERIES))

if __name__=="__main__":unittest.main()
