#!/usr/bin/env python3
"""Reuters discovery: publisher validation, desk routing and safe metadata."""
import sys
import unittest
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reuters_google_news import parse_reuters, collect_reuters

def item(title, link, source="Reuters", domain="https://www.reuters.com"):
    stamp = format_datetime(datetime.now(timezone.utc))
    return (
        "<item><title>" + escape(title) + "</title>"
        "<link>" + escape(link) + "</link>"
        "<pubDate>" + stamp + "</pubDate>"
        '<source url="' + escape(domain) + '">' + escape(source) + "</source></item>"
    )

def feed(*rows):
    return ('<?xml version="1.0"?><rss version="2.0"><channel>' +
            "".join(rows) + "</channel></rss>").encode("utf-8")

class ReutersTest(unittest.TestCase):
    def test_only_reuters_source_accepted(self):
        payload = feed(
            item("Indian election officials announce new voting process",
                 "https://news.google.com/rss/articles/reuters-vote"),
            item("India election coverage from another news outlet",
                 "https://news.google.com/rss/articles/not-reuters",
                 "Example Publisher", "https://example.com"),
        )
        rows = parse_reuters(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "Reuters • Google News")
        self.assertEqual(rows[0]["desk"], "india-general")
        self.assertEqual(rows[0]["time_basis"], "google_rss")
        self.assertEqual(rows[0]["link_type"], "google-news-redirect")

    def test_reuters_business_and_regions(self):
        payload = feed(
            item("Hyderabad pharma company reports profit growth",
                 "https://news.google.com/rss/articles/reuters-pharma"),
            item("Global oil markets react to new supply projections",
                 "https://news.google.com/rss/articles/reuters-oil"),
            item("Scientists discover an unusual new ocean species",
                 "https://news.google.com/rss/articles/reuters-science"),
        )
        rows = parse_reuters(payload)
        by_url = {r["url"].rsplit("/", 1)[-1]: r for r in rows}
        self.assertEqual(by_url["reuters-pharma"]["region"], "hyderabad")
        self.assertEqual(by_url["reuters-pharma"]["desk"], "regional-business")
        self.assertEqual(by_url["reuters-oil"]["region"], "world")
        self.assertEqual(by_url["reuters-oil"]["desk"], "business")
        self.assertEqual(by_url["reuters-science"]["desk"], "world-general")

    def test_no_invalid_links(self):
        rows = parse_reuters(feed(
            item("Reuters India headline with invalid link", "https://reuters.com/abc")
        ))
        self.assertEqual(rows, [])

if __name__ == "__main__":
    unittest.main()
