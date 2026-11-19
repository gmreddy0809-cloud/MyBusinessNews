"""Hyderabad business headline categorization regression tests."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rss_sources import company_for
from hyderabad_business_news import parse

class HyderabadBusinessTests(unittest.TestCase):
    def test_biosol_is_hyderabad_company(self):
        for title in (
            "BE Biosol and Gates Foundation Collaborate to expand access to injection",
            "బీఈ బయోసోల్ గేట్స్ ఫౌండేషన్‌తో ఒప్పందం",
        ):
            self.assertEqual(company_for(title)[0],"hyderabad")

    def test_credible_source_headline_without_city_in_title(self):
        date="Thu, 19 Nov 2026 09:00:00 GMT"
        xml=('<rss><channel><item>'
             '<title>BE Biosol and Gates Foundation Collaborate to expand access</title>'
             '<link>https://news.google.com/rss/articles/CBMiEXAMPLE</link>'
             '<pubDate>'+date+'</pubDate>'
             '<source url="https://www.businessbriefingtoday.com">Business Briefing Today</source>'
             '</item></channel></rss>').encode()
        results=parse(xml,now=datetime(2026,11,19,12,tzinfo=timezone.utc))
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]["region"],"hyderabad")
        self.assertEqual(results[0]["desk"],"regional-business")
        self.assertEqual(results[0]["sector"],"Pharma & Life Sciences")
        self.assertEqual(results[0]["time_basis"],"google_rss")

    def test_unrelated_country_news_not_regional(self):
        xml=('<rss><channel><item>'
             '<title>International vaccine manufacturer expands production</title>'
             '<link>https://news.google.com/rss/articles/OTHER</link>'
             '<pubDate>Thu, 19 Nov 2026 09:00:00 GMT</pubDate>'
             '<source url="https://example.com">Example</source>'
             '</item></channel></rss>').encode()
        self.assertEqual(parse(xml,now=datetime(2026,11,19,12,tzinfo=timezone.utc)),[])

if __name__=="__main__":unittest.main()
