import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from fortune_india import parse_feed

NOW=datetime(2026,11,27,12,tzinfo=timezone.utc)
def sample(source_url,title,date="Fri, 27 Nov 2026 09:00:00 GMT"):
    return ('<item><title>'+title+'</title><link>https://news.google.com/rss/articles/abc</link>'
            '<pubDate>'+date+'</pubDate><source url="'+source_url+'">Fortune India</source></item>')

class FortuneIndiaTests(unittest.TestCase):
    def test_only_fortune_business_and_finance(self):
        xml=('<rss><channel>'+sample("https://www.fortuneindia.com","India companies report quarterly profits")+
             sample("https://example.com","India companies report quarterly profits")+
             sample("https://www.fortuneindia.com","Cricket match score today")+'</channel></rss>').encode()
        rows=parse_feed(xml,NOW)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["domain"],"fortuneindia.com")
        self.assertEqual(rows[0]["desk"],"business")
    def test_older_than_archive_skipped(self):
        xml=('<rss><channel>'+sample("https://www.fortuneindia.com","India companies report quarterly profits","Fri, 13 Nov 2026 09:00:00 GMT")+'</channel></rss>').encode()
        self.assertEqual(parse_feed(xml,NOW),[])

if __name__=="__main__":
    unittest.main()
