"""Unit tests for date-safe, source-verified PF Google News RSS discovery."""
import sys, unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from xml.sax.saxutils import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from pf_google_news import parse_google_news, rss_url, topic_query, PF_SOURCES, PF_TOPICS, collect_personal_finance

NOW=datetime(2026,11,19,6,0,tzinfo=timezone.utc)
def item(title,source,source_url,when,link):
    return (f"<item><title>{escape(title)}</title>"
            f"<link>{escape(link)}</link>"
            f"<pubDate>{escape(when)}</pubDate>"
            f"<source url='{escape(source_url)}'>{escape(source)}</source></item>")
def feed(*items):
    return ("<?xml version='1.0'?><rss><channel>"+''.join(items)+"</channel></rss>").encode()

class PFNewsFeedTests(unittest.TestCase):
    def test_source_specific_positive(self):
        xml=feed(item("Best fixed deposit rates in India - CNBC-TV18",
            "CNBC-TV18","https://www.cnbctv18.com",
            "Thu, 19 Nov 2026 05:00:00 GMT","https://news.google.com/rss/articles/id123"))
        rows=parse_google_news(xml,now=NOW,expected_domain="cnbctv18.com")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["title"],"Best fixed deposit rates in India")
        self.assertEqual(rows[0]["desk"],"personal-finance")
        self.assertEqual(rows[0]["time_basis"],"google_rss")
    def test_skip_wrong_publisher_and_expired(self):
        xml=feed(
          item("Mutual fund SIP guide - Zee Business","Zee Business",
               "https://www.zeebiz.com","Thu, 19 Nov 2026 04:00:00 GMT",
               "https://news.google.com/rss/articles/abc"),
          item("Fixed deposit tax rules - CNBC-TV18","CNBC-TV18",
               "https://www.cnbctv18.com","Thu, 05 Nov 2026 04:00:00 GMT",
               "https://news.google.com/rss/articles/old"))
        self.assertEqual(parse_google_news(xml,now=NOW,expected_domain="cnbctv18.com"),[])
    def test_no_guessed_dates_or_external_links(self):
        xml=feed(item("Tax refund status for taxpayers - Upstox","Upstox",
            "https://upstox.com","", "https://evil.example/story"))
        self.assertEqual(parse_google_news(xml,now=NOW),[])
    def test_source_search_does_not_admit_unrelated_news(self):
        xml=feed(
          item("Van Gogh painting sells for $190.4 million - Livemint","Livemint",
               "https://www.livemint.com","Thu, 19 Nov 2026 04:00:00 GMT",
               "https://news.google.com/rss/articles/art"),
          item("Fixed deposit interest rates increase - Livemint","Livemint",
               "https://www.livemint.com","Thu, 19 Nov 2026 04:00:00 GMT",
               "https://news.google.com/rss/articles/pf"))
        rows=parse_google_news(xml,now=NOW,expected_domain="livemint.com")
        self.assertEqual(len(rows),1)
        self.assertIn("Fixed deposit",rows[0]["title"])
    def test_query_locale_and_topics(self):
        self.assertIn("ceid=IN%3Aen",rss_url(topic_query("zeebiz.com",PF_TOPICS[0])))
        self.assertIn("when%3A7d",rss_url(topic_query("zeebiz.com",PF_TOPICS[0])))
        self.assertGreaterEqual(len(PF_SOURCES),20)
    def test_safe_partial_failure(self):
        with patch("pf_google_news.fetch_feed",side_effect=RuntimeError("unavailable")):
            rows,status=collect_personal_finance(cycle=3)
        self.assertEqual(rows,[])
        self.assertEqual(status["successful_feeds"],0)
        self.assertTrue(status["warnings"])
if __name__=="__main__":unittest.main()
