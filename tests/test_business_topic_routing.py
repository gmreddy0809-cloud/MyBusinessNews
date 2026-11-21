#!/usr/bin/env python3
"""Promote Google News business-topic items to the correct specialist tabs."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from quick_refresh import route_general_business_topic

class BusinessTopicRoutingTests(unittest.TestCase):
    def row(self,title,desk="india-general",sector="Business & Economy"):
        return {"title":title,"url":"https://news.google.com/rss/articles/test",
                "desk":desk,"sector":sector,"region":"india"}

    def test_business_feed_story_never_disappears_between_tabs(self):
        row=self.row("Indian companies report record revenue and profit")
        self.assertEqual(route_general_business_topic(row),"business")
        self.assertEqual(row["desk"],"business")
        self.assertEqual(row["sector"],"Business & Economy")

    def test_pf_story_goes_to_pf(self):
        row=self.row("Bank credit card interest rates explained")
        self.assertEqual(route_general_business_topic(row),"personal_finance")
        self.assertEqual(row["desk"],"personal-finance")
        self.assertEqual(row["sector"],"Personal Finance")
        self.assertTrue(row["reader_finance"])

    def test_world_business_is_retained(self):
        row=self.row("Global oil market prices rise",desk="world-general")
        self.assertEqual(route_general_business_topic(row),"business")
        self.assertEqual(row["desk"],"business")

    def test_nonbusiness_general_and_regional_stories_untouched(self):
        for row in (
            self.row("India national election",sector="Politics"),
            self.row("Hyderabad bank unveils a new digital service",desk="regional-general"),
            self.row("Hyderabad pharma factory expands",desk="regional-business")
        ):
            original=dict(row)
            self.assertIsNone(route_general_business_topic(row))
            self.assertEqual(row,original)

if __name__=="__main__":unittest.main()
