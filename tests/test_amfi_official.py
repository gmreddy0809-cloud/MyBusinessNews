"""Test official AMFI RSS discovery, strict URL validation and real dates."""
import sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from amfi_official import discover_feeds,parse_amfi

class OfficialAmfiTests(unittest.TestCase):
    def test_find_official_nfo_feeds_only(self):
        html=("""
        <a href="https://www.amfiindia.com/rss/new-fund-offer.xml">New Fund Offer RSS</a>
        <a href="/rss/latest-fundwise-aum.xml">Latest Fundwise AUM RSS</a>
        <a href="https://evil.example/rss/nfo.xml">New Fund Offer RSS</a>
        <a href="/contact">Contact AMFI</a>
        """)
        links=discover_feeds(html)
        self.assertEqual(links,["https://www.amfiindia.com/rss/new-fund-offer.xml",
                                "https://www.amfiindia.com/rss/latest-fundwise-aum.xml"])
    def test_real_date_and_amfi_host_required(self):
        date="Wed, 18 Nov 2026 08:00:00 GMT"
        xml=(f'<rss><channel>'
             f'<item><title>Official New Fund Offer scheme announcement for investors</title>'
             f'<link>https://www.amfiindia.com/nfo/notice123</link><pubDate>{date}</pubDate></item>'
             f'<item><title>Undated AMFI mutual fund item from archive</title>'
             f'<link>https://www.amfiindia.com/nfo/undated</link></item>'
             f'<item><title>Misleading third-party mutual fund redirect</title>'
             f'<link>https://evil.example/nfo/notice</link><pubDate>{date}</pubDate></item>'
             f'</channel></rss>').encode()
        out=parse_amfi(xml,datetime(2026,11,18,18,tzinfo=timezone.utc))
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["seen"],"2026-11-18T08:00:00+00:00")
        self.assertEqual(out[0]["time_basis"],"feed")
        self.assertEqual(out[0]["desk"],"personal-finance")
        self.assertEqual(out[0]["source"],"AMFI • Official")
        self.assertNotIn("body",out[0])
        self.assertNotIn("summary",out[0])
    def test_before_fourteenth_excluded(self):
        date="Thu, 12 Nov 2026 08:00:00 GMT"
        xml=(f'<rss><channel><item><title>Older mutual fund announcement before requested start</title>'
             f'<link>https://amfiindia.com/nfo/old</link><pubDate>{date}</pubDate>'
             f'</item></channel></rss>').encode()
        self.assertEqual(parse_amfi(xml,datetime(2026,11,18,tzinfo=timezone.utc)),[])
if __name__=="__main__":unittest.main()
