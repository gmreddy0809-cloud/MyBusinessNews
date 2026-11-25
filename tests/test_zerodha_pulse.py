import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from zerodha_pulse import parse_feed

NOW = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
def item(title, url, date="Wed, 25 Nov 2026 09:00:00 GMT"):
    return f"<item><title>{title}</title><link>{url}</link><pubDate>{date}</pubDate></item>"

class PulseFeedTests(unittest.TestCase):
    def test_desk_routing_and_original_publisher_links(self):
        xml = ("<rss><channel>" +
               item("How mutual fund SIP taxation works", "https://example.com/sip") +
               item("Nifty stock market gains today", "https://finance.example.com/markets") +
               item("Cricket match latest score", "https://example.com/sports") +
               "</channel></rss>")
        rows = parse_feed(xml.encode(), NOW)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["desk"], "personal-finance")
        self.assertEqual(rows[1]["desk"], "business")
        self.assertEqual(rows[0]["url"], "https://example.com/sip")
        self.assertEqual(rows[0]["time_basis"], "feed")

    def test_drops_outdated_and_pulse_internal_links(self):
        xml = ("<rss><channel>" +
               item("Nifty market in October", "https://example.com/old", "Wed, 11 Nov 2026 09:00:00 GMT") +
               item("Nifty market update", "https://pulse.zerodha.com/story/1") +
               "</channel></rss>")
        self.assertEqual(parse_feed(xml.encode(), NOW), [])

if __name__ == "__main__":
    unittest.main()
