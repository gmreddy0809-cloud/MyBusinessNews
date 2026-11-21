#!/usr/bin/env python3
"""Regression tests for Hyderabad Mail: RSS provenance, region and desk routing."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hyderabad_mail import parse_feed, _place

NOW=datetime.now(timezone.utc)

def item(title,slug="example",categories=("Hyderabad",),domain="hyderabadmail.com",days=0):
    link="https://"+domain+"/"+slug+"/"
    cat="".join("<category>"+escape(c)+"</category>" for c in categories)
    return (
      "<item><title>"+escape(title)+"</title><link>"+escape(link)+"</link>"
      "<pubDate>"+format_datetime(NOW-timedelta(days=days))+"</pubDate>"
      +cat+"</item>"
    )

def feed(*items):
    return ('<?xml version="1.0"?><rss version="2.0"><channel>'+
            "".join(items)+"</channel></rss>").encode("utf-8")

class TestHyderabadMail(unittest.TestCase):
    def test_retail_ranking_reaches_hyderabad_realty(self):
        rows=parse_feed(feed(item(
            "Jubilee Hills ranks 51st in Asia-Pacific retail rental list",
            "jubilee-hills-asia-pacific-retail-rent-ranking-2026",
            ("Madhapur / Jubilee hills","Top News"))),now=NOW)
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row["region"],"hyderabad")
        self.assertEqual(row["desk"],"regional-business")
        self.assertEqual(row["sector"],"Real Estate")
        self.assertEqual(row["real_estate_kind"],"Retail")
        self.assertEqual(row["source"],"Hyderabad Mail • RSS")
        self.assertEqual(row["time_basis"],"feed")
        self.assertTrue(row["url"].startswith("https://hyderabadmail.com/"))

    def test_property_category_makes_relevant_headline_realty(self):
        rows=parse_feed(feed(
            item("TGRERA orders Alpine Infratech to refund ₹54 lakh to homebuyers",
                 "tgrera-refund",("Real Estate",)),
            item("From HMDA auction to Rs 400 crore: Hyderabad developers shift to JDAs",
                 "hmda-developers",("Real Estate","Hyderabad"))
        ),now=NOW)
        self.assertEqual(len(rows),2)
        data={x["url"].split("/")[-2]:x for x in rows}
        self.assertEqual(data["tgrera-refund"]["region"],"telangana")
        self.assertEqual(data["tgrera-refund"]["real_estate_kind"],"Regulation")
        self.assertEqual(data["hmda-developers"]["region"],"hyderabad")
        self.assertEqual(data["hmda-developers"]["sector"],"Real Estate")

    def test_city_general_does_not_pollute_hyderabad_business(self):
        rows=parse_feed(feed(item("Hyderabad traffic diversions announced for Sunday",
                 "traffic-diversions",("Hyderabad",)),
                 item("Andhra Pradesh college schedules new exams",
                 "ap-schools",("Andhra Pradesh",))),now=NOW)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["desk"],"regional-general")
        self.assertEqual(rows[0]["region"],"hyderabad")
        self.assertEqual(rows[1]["region"],"andhra-pradesh")
        self.assertEqual(rows[1]["desk"],"regional-general")

    def test_invalid_hosts_old_or_unrelated_titles_ignored(self):
        rows=parse_feed(feed(
            item("Hyderabad new property launch", "wrong-host",domain="other.example"),
            item("Hyderabad new property launch", "stale",days=10),
            item("London fashion week announces runway", "unrelated",("Top News",))
        ),now=NOW)
        self.assertEqual(rows,[])

if __name__=="__main__":
    unittest.main()
