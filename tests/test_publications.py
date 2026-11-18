"""Publication RSS: explicitly allowlisted, credited original article links only."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import publications

class PublicationTests(unittest.TestCase):
    def test_permitted_conversation_atom(self):
        now=datetime.now(timezone.utc)
        stamp=now.isoformat()
        xml=('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
          '<entry><title>How shared meals and healthy food habits bring communities together</title>'
          '<link href="https://theconversation.com/healthy-food-habits-98765" rel="alternate"/>'
          '<updated>'+stamp+'</updated></entry></feed>').encode("utf8")
        rows=publications.parse_feed(xml,"The Conversation","english-magazines","general",now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["desk"],"english-magazines")
        self.assertTrue(rows[0]["url"].startswith("https://theconversation.com/"))
        self.assertEqual(rows[0]["time_basis"],"feed")
        self.assertEqual(rows[0]["source"],"The Conversation • RSS")

    def test_telugu_republication_only_with_authorised_source(self):
        now=datetime.now(timezone.utc)
        date=now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        xml=('<rss><channel><item><title>తెలంగాణలో ఆరోగ్య కార్యక్రమాలు – కొత్త సమాచారం</title>'
            '<link>https://dharaninews.com/latest-telangana-health/</link>'
            '<pubDate>'+date+'</pubDate></item></channel></rss>').encode("utf8")
        rows=publications.parse_feed(xml,"Dharani News","telugu-patrikalu","general",now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["desk"],"telugu-patrikalu")
        self.assertEqual(rows[0]["source"],"Dharani News • RSS")

    def test_oneindia_official_rss_headline(self):
        now=datetime.now(timezone.utc)
        date=now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        xml=('<rss><channel><item><title>తెలంగాణలో ఆరోగ్యంపై కొత్త కార్యక్రమం వివరాలు</title>'
          '<link>https://telugu.oneindia.com/news/telangana/health-123456.html</link>'
          '<pubDate>'+date+'</pubDate><description>Do not store or republish content</description>'
          '</item></channel></rss>').encode("utf8")
        rows=publications.parse_feed(xml,"Oneindia Telugu","telugu-patrikalu","health",now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["source"],"Oneindia Telugu • RSS")
        self.assertEqual(rows[0]["region"],"telangana")
        self.assertEqual(rows[0]["sector"],"Health & Wellbeing")
        self.assertNotIn("description",rows[0])
        self.assertNotIn("image",rows[0])

    def test_oneindia_category_path_tags_ap_without_place_in_headline(self):
        now=datetime.now(timezone.utc)
        date=now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        xml=('<rss><channel><item><title>రాష్ట్రంలో విద్యుత్ డిమాండ్ పెరిగినట్లు అధికారుల వెల్లడి</title>'
             '<link>https://telugu.oneindia.com/news/andhra-pradesh/energy-review-1234.html</link>'
             '<pubDate>'+date+'</pubDate></item></channel></rss>').encode("utf8")
        rows=publications.parse_feed(xml,"Oneindia Telugu","telugu-patrikalu","general",now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["region"],"andhra-pradesh")

    def test_dharani_recent_archive_is_dated_not_first_seen(self):
        now=datetime.now(timezone.utc)
        past=now-timedelta(days=15)
        xml=('<rss><channel><item><title>హైదరాబాద్‌ వార్తలు: తాజా అంశాల విశ్లేషణ</title>'
          '<link>https://dharaninews.com/hyderabad-story-2341/</link>'
          '<pubDate>'+past.strftime("%a, %d %b %Y %H:%M:%S +0000")+'</pubDate>'
          '</item></channel></rss>').encode("utf8")
        rows=publications.parse_feed(xml,"Dharani News","telugu-patrikalu","general",now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["time_basis"],"feed")
        self.assertEqual(rows[0]["region"],"hyderabad")
        self.assertEqual(rows[0]["seen"][:10],past.date().isoformat())

    def test_unlicensed_publisher_links_rejected(self):
        now=datetime.now(timezone.utc)
        xml=('<rss><channel><item><title>Latest Telugu newspaper health story</title>'
          '<link>https://www.eenadu.net/story/12345</link>'
          '<pubDate>'+now.strftime("%a, %d %b %Y %H:%M:%S +0000")+'</pubDate>'
          '</item></channel></rss>').encode("utf8")
        self.assertEqual(publications.parse_feed(xml,"Eenadu","telugu-patrikalu","general",now),[])

    def test_old_magazine_stories_not_misrepresented_as_latest(self):
        then=datetime.now(timezone.utc)-timedelta(days=30)
        xml=('<rss><channel><item><title>Why lifestyle and living trends matter more than ever</title>'
          '<link>https://theconversation.com/living-trends-12345</link>'
          '<pubDate>'+then.strftime("%a, %d %b %Y %H:%M:%S +0000")+'</pubDate>'
          '</item></channel></rss>').encode("utf8")
        self.assertEqual(publications.parse_feed(xml,"The Conversation","english-magazines","general"),[])

    def test_missing_date_does_not_invent_publication_time(self):
        xml=b'<rss><channel><item><title>New lifestyle and wellness story available today</title><link>https://theconversation.com/wellness-story-23451</link></item></channel></rss>'
        self.assertEqual(publications.parse_feed(xml,"The Conversation","english-magazines","general"),[])

if __name__=="__main__":
    unittest.main()
