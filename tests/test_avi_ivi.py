"""Offline regression tests for original-source general-interest desk."""
import sys
import tempfile
import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import avi_ivi
import collect

class GeneralInterestTests(unittest.TestCase):
    def test_nasa_science_rss_original_link(self):
        now=datetime.now(timezone.utc)
        xml=b"<rss><channel><item><title>NASA Scientists Explore a New Moon Discovery</title><link>https://www.nasa.gov/new-moon-discovery/</link></item></channel></rss>"
        rows=avi_ivi.parse_feed(xml,"NASA","world","science",now)
        self.assertEqual(len(rows),1)
        item=rows[0]
        self.assertEqual(item["desk"],"avi-ivi")
        self.assertEqual(item["sector"],"Science & Space")
        self.assertEqual(item["region"],"world")
        self.assertEqual(item["time_basis"],"first_seen")
        self.assertEqual(item["url"],"https://www.nasa.gov/new-moon-discovery/")

    def test_who_health_rss(self):
        xml=b"<rss><channel><item><title>WHO Announces Global Vaccination Programme</title><link>https://www.who.int/news/item/health-programme</link></item></channel></rss>"
        rows=avi_ivi.parse_feed(xml,"WHO","world","health")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["sector"],"Health & Wellbeing")
        self.assertEqual(rows[0]["source"],"WHO \u2022 Official")

    def test_pib_local_public_affairs(self):
        xml=b"<rss><channel><item><title>Cabinet approves Andhra Pradesh education policy</title><link>https://pib.gov.in/PressReleasePage.aspx?PRID=10001</link></item></channel></rss>"
        rows=avi_ivi.parse_feed(xml,"PIB India","india","government")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["region"],"andhra-pradesh")
        self.assertEqual(rows[0]["sector"],"Education & Careers")

    def test_un_news_world_society(self):
        xml=b"<rss><channel><item><title>Global food aid response to humanitarian crisis continues</title><link>https://news.un.org/en/story/2026/11/1234567</link></item></channel></rss>"
        rows=avi_ivi.parse_feed(xml,"UN News","world","general")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["sector"],"World & Society")
        self.assertEqual(rows[0]["region"],"world")
        self.assertEqual(rows[0]["source"],"UN News • Official")

    def test_reject_unapproved_domains(self):
        xml=b"<rss><channel><item><title>Untrusted Copy of a Magazine Story</title><link>https://example.com/article</link></item></channel></rss>"
        self.assertEqual(avi_ivi.parse_feed(xml,"NASA","world","science"),[])

    def test_separate_business_and_avii_desks_and_keep_first_seen(self):
        now=datetime.now(timezone.utc)
        earlier=(now-timedelta(hours=2)).isoformat()
        link="https://www.nasa.gov/new-moon-discovery/"
        saved={"id":link,"url":link,"title":"NASA Scientists Explore a New Moon Discovery","source":"NASA \u2022 Official","domain":"nasa.gov","region":"world","sector":"Science & Space","seen":earlier,"desk":"avi-ivi","time_basis":"first_seen","origin":"official-rss"}
        business={"id":"https://www.nseindia.com/example","url":"https://www.nseindia.com/example","title":"Zen Technologies Result","source":"NSE \u2022 Official","region":"hyderabad","sector":"Corporate & Results","seen":now.isoformat()}
        with tempfile.TemporaryDirectory() as dirname:
            target=Path(dirname)/"news.json"
            target.write_text(json.dumps({"generated_at":now.isoformat(),"articles":[business,saved]}),encoding="utf8")
            with patch.object(collect,"DEST",target),patch.object(collect,"collect_official",return_value=[]),patch.object(collect,"collect_avi_ivi",return_value=([dict(saved,seen=now.isoformat())],{"successful_feeds":1,"feed_matches":{"NASA":1},"warnings":[]})),patch.object(collect,"collect_publications",return_value=([],{"successful_feeds":0,"counts":{},"warnings":[]})),patch.object(collect,"request",return_value=[]):
                collect.main()
            result=json.loads(target.read_text(encoding="utf8"))
            feed={x["url"]:x for x in result["articles"]}
            self.assertEqual(feed[link]["seen"],earlier)
            self.assertEqual(feed[link]["desk"],"avi-ivi")
            self.assertNotIn("desk",feed[business["url"]])
            self.assertEqual(result["source_status"]["avi_ivi"]["successful_feeds"],1)

if __name__=="__main__":
    unittest.main()
