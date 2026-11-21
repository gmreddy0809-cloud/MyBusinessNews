#!/usr/bin/env python3
"""Hyderabad real-estate discovery headline and source safety tests."""
import sys
import unittest
from datetime import datetime,timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hyderabad_real_estate import parse, classify

NOW=datetime.now(timezone.utc)
def item(title,link="https://news.google.com/rss/articles/example",source="Example News",domain="https://example.com"):
    stamp=format_datetime(NOW)
    return ('<item><title>'+escape(title)+'</title><link>'+escape(link)+
            '</link><pubDate>'+stamp+'</pubDate><source url="'+escape(domain)+'">'+
            escape(source)+'</source></item>')
def rss(*items):
    return ('<?xml version="1.0"?><rss version="2.0"><channel>'+''.join(items)+
            '</channel></rss>').encode("utf-8")

class TestHyderabadRealEstate(unittest.TestCase):
    def test_market_reports_and_deals(self):
        rows=parse(rss(
          item("JLL Hyderabad office market report Q3 2026",
               "https://news.google.com/rss/articles/market"),
          item("Bank leases 200000 sq ft Hyderabad office space",
               "https://news.google.com/rss/articles/deal"),
          item("Hyderabad apartment sales increase in Q3",
               "https://news.google.com/rss/articles/housing")
        ),now=NOW)
        byurl={r["url"].rsplit("/",1)[-1]:r for r in rows}
        self.assertEqual(byurl["market"]["real_estate_kind"],"Reports")
        self.assertEqual(byurl["deal"]["real_estate_kind"],"Deals")
        self.assertEqual(byurl["housing"]["real_estate_kind"],"Residential")
        for row in rows:
            self.assertEqual(row["region"],"hyderabad")
            self.assertEqual(row["desk"],"regional-business")
            self.assertEqual(row["sector"],"Real Estate")
            self.assertEqual(row["time_basis"],"google_rss")
            self.assertEqual(row["link_type"],"google-news-redirect")

    def test_regulatory(self):
        self.assertEqual(classify("Telangana RERA Hyderabad property project notices"),"Regulation")

    def test_no_false_hyderabad_label_without_city(self):
        self.assertIsNone(classify("India residential property market Q3 report"))
        self.assertIsNone(classify("Gujarat office leasing rises by 4 percent"))
        self.assertIsNone(classify("Hyderabad cricket team wins at home"))

    def test_source_and_google_news_link_required(self):
        self.assertFalse(parse(rss(item("Hyderabad housing property prices",
                  "https://example.com/own-story")),now=NOW))
        self.assertFalse(parse(rss(item("Hyderabad housing property prices",
                  "https://news.google.com/rss/articles/invalid",domain="https://fake")),now=NOW))

if __name__=="__main__":
    unittest.main()
