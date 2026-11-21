#!/usr/bin/env python3
"""Regression checks for Feedspot-derived Telugu regional discovery candidates."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from regional_google_news import SOURCES, region

class FeedspotSourcesTest(unittest.TestCase):
    def test_source_domains_unique(self):
        domains=[domain for name,domain in SOURCES]
        self.assertEqual(len(domains),len(set(domains)))
        self.assertGreaterEqual(len(domains),70)

    def test_major_telugu_candidates_present(self):
        sites={domain for name,domain in SOURCES}
        for domain in (
            "ntvtelugu.com","10tv.in","v6velugu.com","ntnews.com",
            "visalaandhra.com","prajatantranews.com","vaartha.com",
            "manalokam.com","telugustop.com","netidhatri.com",
            "janamsakshi.org","telugu.gulte.com","sakshipost.com",
            "telugu.webdunia.com"
        ):
            with self.subTest(domain=domain):
                self.assertIn(domain,sites)

    def test_state_routing_still_requires_headline_location(self):
        self.assertEqual(region("తెలంగాణలో కొత్త ప్రభుత్వ ఆసుపత్రి"),"telangana")
        self.assertEqual(region("Visakhapatnam airport new flights"),"andhra-pradesh")
        self.assertEqual(region("Hyderabad local rainfall alert"),"hyderabad")
        self.assertIsNone(region("National movie review roundup"))

if __name__=="__main__":
    unittest.main()
