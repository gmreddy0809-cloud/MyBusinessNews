"""Regression tests for India/World all-topic news; business views stay untouched."""
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from all_general_news import parse

NOW=datetime(2026,11,20,10,tzinfo=timezone.utc)
DATE="Fri, 20 Nov 2026 08:00:00 GMT"
HTML=(ROOT/"index.html").read_text(encoding="utf-8")

def feed(title):
    return (
        "<rss><channel><item><title>"+escape(title)+"</title>"
        "<link>https://news.google.com/rss/articles/EXAMPLE</link>"
        "<pubDate>"+DATE+"</pubDate>"
        "<source url='https://example.org'>Regional Newspaper</source>"
        "</item></channel></rss>"
    ).encode("utf-8")

class IndiaWorldGeneralTests(unittest.TestCase):
    def test_india_accepts_every_news_topic(self):
        cases=[
            "India election commission publishes updated rules",
            "Hyderabad hospital opens new diabetes unit",
            "Kolkata police solve major robbery investigation",
            "Indian football squad wins international championship",
            "Mumbai movie festival announces film awards",
            "National weather department issues cyclone warning",
            "Indian scientists develop new satellite mission",
            "India central bank announces new guidance",
        ]
        for title in cases:
            with self.subTest(title=title):
                rows=parse(feed(title),"india-general",now=NOW)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["desk"],"india-general")
    def test_hyderabad_india_news_retains_state_tag(self):
        row=parse(feed("Hyderabad residents report heavy rain"),"india-general",now=NOW)[0]
        self.assertEqual(row["region"],"hyderabad")
    def test_world_general_accepts_any_topic(self):
        for title in ("World chess champion plays historic match",
                      "London hospital scientists announce new research",
                      "Global weather pattern changes temperatures"):
            with self.subTest(title=title):
                row=parse(feed(title),"world-general",now=NOW)[0]
                self.assertEqual(row["region"],"world")
                self.assertEqual(row["desk"],"world-general")
    def test_existing_business_views_remain_distinct(self):
        self.assertIn("'india':'India Business News'",HTML)
        self.assertIn("'world':'World Business News'",HTML)
        self.assertIn("'india-general':'India General News'",HTML)
        self.assertIn("'world-general':'World General News'",HTML)
    def test_finance_is_external_link_not_scraped_quote(self):
        self.assertIn('href="https://www.google.com/finance/beta"',HTML)
        self.assertIn('target="_blank" rel="noopener noreferrer"',HTML)
if __name__=="__main__":unittest.main()
