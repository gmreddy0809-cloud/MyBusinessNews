"""AP+TG general news remains a separate, sourced, non-corporate desk."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from regional_general import keep_general,REGIONAL_QUERIES,region_from_title_url
class RegionalGeneralTests(unittest.TestCase):
    def sample(self,title,url,language="English"):
        return {"title":title,"url":url,"domain":"example-news.com","seendate":"20261118T180000Z","language":language}
    def test_telangana_government_in_english(self):
        item=keep_general(self.sample("Telangana cabinet approves new welfare scheme for families",
            "https://example-news.com/states/telangana/new-scheme"))
        self.assertEqual(item["desk"],"regional-general")
        self.assertEqual(item["region"],"telangana")
        self.assertEqual(item["sector"],"Politics & Government")
        self.assertEqual(item["time_basis"],"indexed")
        self.assertEqual(item["url"],"https://example-news.com/states/telangana/new-scheme")
        self.assertNotIn("description",item)
    def test_andhra_pradesh_education_and_ministers(self):
        item=keep_general(self.sample("Andhra Pradesh Education Minister addresses school reform",
            "https://example-news.com/andhra-pradesh/minister-school-reform"))
        self.assertEqual(item["region"],"andhra-pradesh")
        self.assertEqual(item["sector"],"Politics & Government")
    def test_local_welfare_without_title_location_uses_explicit_article_path(self):
        item=keep_general(self.sample("New ration scheme for eligible families",
            "https://example-news.com/news/telangana/welfare"))
        self.assertEqual(item["region"],"telangana")
        self.assertEqual(item["sector"],"Public Issues & Welfare")
    def test_generic_news_rejected(self):
        self.assertIsNone(keep_general(self.sample("World leaders hold a press conference",
            "https://example-news.com/world/press-conference")))
    def test_corporate_results_rejected(self):
        self.assertIsNone(keep_general(self.sample("Telangana company quarterly net profit grows 21 percent",
            "https://example-news.com/telangana/earnings")))
    def test_wrong_language_not_mislabeled_english(self):
        self.assertIsNone(keep_general(self.sample("Telangana cabinet approves new welfare scheme",
            "https://example-news.com/telangana/cabinet","Telugu")))
    def test_moneycontrol_paywall_not_scraped(self):
        self.assertIsNone(keep_general(self.sample("Telangana government starts welfare programme",
            "https://www.business-standard.com/india-news/telangana-government-welfare")))
    def test_queries_bounded_and_explicit(self):
        self.assertEqual(len(REGIONAL_QUERIES),4)
        self.assertTrue(all("sourcelang:english" in q for _,q in REGIONAL_QUERIES))
if __name__=="__main__":unittest.main()
