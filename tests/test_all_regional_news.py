"""AP, TG and joint AP+TG desks must index news of EVERY kind."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
from regional_google_news import region,parse
from publications import telugu_region

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
DATE="Fri, 20 Nov 2026 07:30:00 GMT"
NOW=datetime(2026,11,20,12,tzinfo=timezone.utc)

def rss(title):
    import xml.sax.saxutils
    title=xml.sax.saxutils.escape(title)
    return (
        '<rss><channel><item><title>'+title+'</title>'
        '<link>https://news.google.com/rss/articles/EXAMPLE</link>'
        '<pubDate>'+DATE+'</pubDate>'
        '<source url="https://example.com">Example Regional Publisher</source>'
        '</item></channel></rss>').encode("utf-8")

class AllRegionalNewsTests(unittest.TestCase):
    def test_any_regional_subject_is_accepted(self):
        cases=[
            ("Hyderabad weather today: heavy rainfall expected","hyderabad"),
            ("Telangana district police arrest suspects after robbery","telangana"),
            ("Andhra Pradesh hospital opens emergency care ward","andhra-pradesh"),
            ("Vijayawada school students win national sport competition","andhra-pradesh"),
            ("Warangal medical college students complete examinations","telangana"),
            ("Hyderabad firm launches new manufacturing facility","hyderabad"),
            ("Telangana cinema festival attracts thousands","telangana"),
        ]
        for title,area in cases:
            with self.subTest(title=title):
                self.assertEqual(region(title),area)
                rows=parse(rss(title),expected_domain=None,now=NOW)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["region"],area)
                self.assertEqual(rows[0]["desk"],"regional-general")
    def test_story_covering_both_states_is_not_dropped(self):
        title="Andhra Pradesh and Telangana announce joint transport agreement"
        self.assertEqual(region(title),"ap-tg")
        results=parse(rss(title),expected_domain=None,now=NOW)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]["region"],"ap-tg")
    def test_telugu_rss_uses_same_district_recognition(self):
        self.assertEqual(telugu_region("చంద్రబాబు విజయవాడలో కొత్త ఆసుపత్రిని ప్రారంభించారు"),"andhra-pradesh")
        self.assertEqual(telugu_region("వరంగల్‌లో ప్రమాదం: ముగ్గురికి గాయాలు"),"telangana")
        self.assertEqual(telugu_region("ఆంధ్రప్రదేశ్, తెలంగాణ విద్యార్థుల సమావేశం"),"ap-tg")
    def test_all_three_tabs_accept_cross_state_news(self):
        self.assertIn("regardless of topic or original desk",HTML)
        self.assertIn("['andhra-pradesh','ap-tg'].includes(area)",HTML)
        self.assertIn("['telangana','hyderabad','ap-tg'].includes(area)",HTML)
        self.assertIn("['hyderabad','telangana','andhra-pradesh','ap-tg'].includes(area)",HTML)
    def test_other_desks_keep_specialist_filters(self):
        self.assertIn("else if(selectedDesk==='telugu-companies')",HTML)
        self.assertIn("else if(selectedDesk==='hyderabad')",HTML)
        self.assertIn("else if(selectedDesk==='personal-finance')",HTML)

if __name__=="__main__":unittest.main()
