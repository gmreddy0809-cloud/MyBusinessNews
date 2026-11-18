"""Regression checks for source-link news timestamps and local company matching."""
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import collect
import rss_sources

class FakeResponse:
    def __init__(self,content):self.content=content
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,max_size=None):return self.content

class NewsroomTests(unittest.TestCase):
    def test_regional_exchange_company(self):
        self.assertEqual(rss_sources.company_for("Zen Technologies Limited - Outcome of Board Meeting")[0],"hyderabad")
        self.assertEqual(rss_sources.company_for("Amara Raja Energy & Mobility Limited")[0],"andhra-pradesh")

    def test_rss_feed_time_and_first_seen_time_are_distinguished(self):
        feed_time=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        xml=("""<rss><channel>
          <item><title>Zen Technologies Limited - Board meeting</title><link>https://www.nseindia.com/test/meeting</link><pubDate>{feed_time}</pubDate></item>
          <item><title>Zen Technologies Limited - Disclosure</title><link>https://www.nseindia.com/test/disclosure</link></item>
        </channel></rss>""").format(feed_time=feed_time).encode("utf8")
        with patch.object(rss_sources,"urlopen",return_value=FakeResponse(xml)):
            rows=rss_sources.fetch_one("NSE","https://nsearchives.nseindia.com/test.xml","exchange")
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["time_basis"],"feed")
        self.assertEqual(rows[1]["time_basis"],"first_seen")

    def test_first_seen_is_not_reset_by_later_poll(self):
        now=datetime.now(timezone.utc).isoformat()
        old_time=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        link="https://www.bseindia.com/xml-data/corpfiling/AttachLive/example.pdf"
        base={"id":link,"url":link,"title":"Zen Technologies Ltd - Outcome of Board Meeting","source":"BSE • Official","domain":"bseindia.com","region":"hyderabad","sector":"Corporate & Results","seen":old_time,"time_basis":"first_seen","origin":"official-rss"}
        with tempfile.TemporaryDirectory() as dirname:
            index=Path(dirname)/"news.json"
            index.write_text(json.dumps({"generated_at":now,"articles":[base]}),encoding="utf8")
            fresh=dict(base,seen=now)
            with patch.object(collect,"DEST",index),patch.object(collect,"collect_official",return_value=[fresh]),patch.object(collect,"collect_publications",return_value=([],{"successful_feeds":0,"counts":{},"warnings":[]})),patch.object(collect,"request",return_value=[]):
                collect.main()
            data=json.loads(index.read_text(encoding="utf8"))
            match=[row for row in data["articles"] if row["url"]==link]
            self.assertEqual(len(match),1)
            self.assertEqual(match[0]["seen"],old_time)
            self.assertEqual(match[0]["time_basis"],"first_seen")

    def test_index_time_is_explicit(self):
        row={"url":"https://techcrunch.com/test","title":"Technology company invests in manufacturing expansion","seendate":datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),"domain":"techcrunch.com"}
        item=collect.keep(row,"world")
        self.assertEqual(item["time_basis"],"indexed")

if __name__=="__main__":
    unittest.main()
