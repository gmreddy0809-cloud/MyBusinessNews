#!/usr/bin/env python3
"""Discover source-attributed Reuters headlines through Google News RSS.

Not an official Reuters feed or a licensed Reuters wire service. Index only
headline, publisher credit, Google News click-through and RSS index time.
Never fetch Reuters article bodies or assume a Google News timestamp is the
original Reuters publication time.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from all_general_news import parse as parse_google_news
from regional_google_news import region as state_region

BASE = "https://news.google.com/rss/search"
QUERIES = (
    ("all-world", "site:reuters.com when:2d", "en-US", "US", "US:en"),
    ("all-india", "site:reuters.com when:2d", "en-IN", "IN", "IN:en"),
    ("india", 'site:reuters.com (India OR Indian OR Delhi OR Mumbai OR Bengaluru OR Hyderabad) when:2d', "en-IN", "IN", "IN:en"),
    ("business-india", 'site:reuters.com (India OR Indian) (economy OR markets OR companies OR business OR banking) when:2d', "en-IN", "IN", "IN:en"),
    ("business-world", 'site:reuters.com (markets OR economy OR business OR finance OR earnings) when:2d', "en-US", "US", "US:en"),
    ("tech-world", 'site:reuters.com (technology OR pharma OR energy OR artificial intelligence) when:2d', "en-US", "US", "US:en"),
    ("ap-tg", 'site:reuters.com (Telangana OR Hyderabad OR "Andhra Pradesh" OR Visakhapatnam OR Amaravati) when:7d', "en-IN", "IN", "IN:en"),
)

INDIA = re.compile(
    r"\b(?:India|Indian|New Delhi|Delhi|Mumbai|Bengaluru|Bangalore|Chennai|"
    r"Hyderabad|Telangana|Andhra Pradesh|Visakhapatnam|Amaravati|"
    r"Kolkata|Gujarat|Maharashtra|Pune|Odisha|rupee|RBI|SEBI|"
    r"Modi|Infosys|Reliance|Tata|HDFC|ICICI)\b", re.I
)
BUSINESS = re.compile(
    r"\b(?:economy|economic|finance|financial|banks?|banking|business|"
    r"markets?|stocks?|shares?|earnings|profit|revenue|companies|company|"
    r"corporate|merger|acquisition|investment|investors?|IPO|exports?|"
    r"imports?|trade|tariffs?|inflation|oil|gas|energy|rates?|"
    r"manufacturing|startup|funding|dollar|rupee|billion|million|"
    r"semiconductor|pharma|drugmaker|sales|GDP|central bank|"
    r"bond yields?|interest rates?)\b", re.I
)

def _is_reuters(row):
    domain = str(row.get("domain") or "").lower()
    return domain == "reuters.com" or domain.endswith(".reuters.com")

def _classify(row):
    title = row["title"]
    local = state_region(title)
    india = bool(INDIA.search(title)) or bool(local)
    business = bool(BUSINESS.search(title))
    result = dict(row)
    result["source"] = "Reuters • Google News"
    result["region"] = local or ("india" if india else "world")
    result["desk"] = ("regional-business" if local else "business") if business else (
        "india-general" if india else "world-general"
    )
    result["sector"] = "Business & Economy" if business else (
        "National News" if india else "World & Society"
    )
    result["sourcecountry"] = "India" if india else ""
    result["reuters_discovery"] = True
    return result

def parse_reuters(xml, now=None):
    """Keep only headlines whose RSS source URL belongs to Reuters."""
    rows = parse_google_news(xml, "world-general", "TOP", now=now)
    return [_classify(row) for row in rows if _is_reuters(row)]

def collect_reuters(cycle=None):
    """Run independently from other desks, preserving prior news when unavailable."""
    jobs = list(QUERIES)
    # Add two rotating targeted searches to increase category coverage.
    variations = (
        'site:reuters.com (India OR Indian) (politics OR court OR election OR health) when:2d',
        'site:reuters.com (world OR global) (politics OR diplomacy OR security) when:2d',
        'site:reuters.com (India OR Indian) (technology OR startups OR investment) when:2d',
        'site:reuters.com (health OR science OR climate OR sports) when:2d',
    )
    if cycle is None:
        cycle = int(datetime.now(timezone.utc).timestamp() // 1800)
    for i in (cycle % len(variations), (cycle+2) % len(variations)):
        jobs.append(("rotating", variations[i], "en-IN", "IN", "IN:en"))

    status = {"queries": len(jobs), "successful_feeds": 0,
              "accepted": 0, "by_region": {}, "warnings": []}
    found = {}
    def fetch(job):
        name, query, hl, gl, ceid = job
        url = BASE + "?" + urlencode({"q": query, "hl": hl, "gl": gl, "ceid": ceid})
        request = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MyBusinessNews/1.0; Reuters headline discovery)",
            "Accept": "application/rss+xml,application/xml,text/xml;q=0.9",
        })
        try:
            with urlopen(request, timeout=12) as response:
                xml = response.read(1_800_000)
            return name, parse_reuters(xml), None
        except Exception as exc:
            return name, [], type(exc).__name__ + ": " + str(exc)[:100]

    with ThreadPoolExecutor(max_workers=6) as pool:
        for name, items, error in pool.map(fetch, jobs):
            if error:
                status["warnings"].append(name + ": " + error)
                continue
            status["successful_feeds"] += 1
            for item in items:
                found[item["url"]] = item
    for row in found.values():
        key = row["region"]
        status["by_region"][key] = status["by_region"].get(key, 0) + 1
    status["accepted"] = len(found)
    return list(found.values()), status

if __name__ == "__main__":
    rows, info = collect_reuters()
    print("Reuters-linked headlines:", len(rows), info)
