#!/usr/bin/env python3
"""Business fallback from broad AP/TG feeds and partial Telangana RSS recovery."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hyderabad_business_news import eligible_regional_business
from regional_google_news import extract_complete_rss_items

class RecoveryTests(unittest.TestCase):
    def test_hyderabad_business_headlines_from_general_discovery(self):
        cases=[
          ("Hyderabad pharma facility expands production capacity",True),
          ("USFDA issues seven observations to NATCO Pharma Hyderabad facility",True),
          ("Zurich to expand Hyderabad global capability centre",True),
          ("Telangana startup funding surges to 726 million",True),
          ("Hyderabad youth protest at Meta office, police detain workers",False),
          ("Telangana college students await basic infrastructure",False),
          ("Hyderabad commuters face airport traffic disruptions",False),
          ("Hyderabad rainstorm damages roads near pharma plant",False),
          ("Hyderabad housing colony celebrates festival",False),
        ]
        for title,expected in cases:
            row={"title":title,"desk":"regional-general","region":"hyderabad"}
            self.assertEqual(eligible_regional_business(row),expected,title)

    def test_no_world_stories_or_non_general_items_promoted(self):
        row={"title":"Global pharma earnings improve","desk":"regional-general","region":"world"}
        self.assertFalse(eligible_regional_business(row))
        row["region"]="hyderabad"
        row["desk"]="regional-business"
        self.assertFalse(eligible_regional_business(row))

    def test_malformed_feed_keeps_only_complete_items(self):
        good=(b"<item><title>Hyderabad city rainfall update</title>"
              b"<link>https://telanganatoday.com/sample</link>"
              b"<pubDate>Sat, 21 Nov 2026 07:30:00 GMT</pubDate></item>")
        broken=(b"<item><title><![CDATA[incomplete text"
                b"<link>https://telanganatoday.com/broken</link>")
        xml=b"<rss><channel>"+good+broken
        nodes=extract_complete_rss_items(xml)
        self.assertEqual(len(nodes),1)
        self.assertEqual(nodes[0].findtext("title"),"Hyderabad city rainfall update")

    def test_valid_xml_unchanged(self):
        xml=b"<rss><channel><item><title>Hyderabad news</title></item></channel></rss>"
        self.assertEqual(len(extract_complete_rss_items(xml)),1)

if __name__=="__main__":
    unittest.main()
