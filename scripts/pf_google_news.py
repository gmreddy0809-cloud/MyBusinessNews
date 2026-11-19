#!/usr/bin/env python3
"""Discover recent India personal-finance HEADLINES with public Google News RSS.

This is a discovery feed, NOT a licensed publisher syndication feed.
Only the title, credited source, Google News click-through and dated RSS metadata
are retained. We never copy Google snippets, publisher bodies or images.
RSS may not index every publisher article; source links remain separately available.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup, first_text, feed_date
from desk_coverage import pf_match, pf_cutoff

RSS_BASE="https://news.google.com/rss/search"
ATOM="{http://www.w3.org/2005/Atom}"
MAX_BYTES=1_600_000
# Publishers with identifiable source domains. A source directory is NOT
# a claim that the publisher permits article syndication.
PF_SOURCES=(
 ("CNBC-TV18","cnbctv18.com"),
 ("Zee Business","zeebiz.com"),
 ("Upstox","upstox.com"),
 ("Moneycontrol","moneycontrol.com"),
 ("Financial Express","financialexpress.com"),
 ("Business Standard","business-standard.com"),
 ("Economic Times","economictimes.indiatimes.com"),
 ("Mint","livemint.com"),
 ("NDTV Profit","ndtvprofit.com"),
 ("BusinessLine","thehindubusinessline.com"),
 ("Business Today","businesstoday.in"),
 ("Outlook Money","outlookmoney.com"),
 ("Goodreturns","goodreturns.in"),
 ("Money9","money9live.com"),
 ("Value Research","valueresearchonline.com"),
 ("Freefincal","freefincal.com"),
 ("ClearTax","cleartax.in"),
 ("Paisabazaar","paisabazaar.com"),
 ("BankBazaar","bankbazaar.com"),
 ("ET Money","etmoney.com"),
 ("Groww","groww.in"),
 ("Zerodha","zerodha.com"),
)
PF_TOPICS=(
 '("personal finance" OR "income tax" OR "tax refund" OR "tax saving" OR "tax return" OR ITR)',
 '("mutual fund" OR SIP OR "NFO" OR "stock investing" OR "financial planning" OR "retirement")',
 '("fixed deposit" OR "savings account" OR "bank deposit" OR "PPF" OR "EPF" OR "NPS" OR "pension")',
 '("health insurance" OR "life insurance" OR "term insurance" OR "credit card" OR "home loan" OR "gold loan" OR EMI)',
)
# Every run: 8 source/topic searches + 2 broad India discovery searches.
# All source/topic combinations rotate within 11 hours at twice-hourly polling.
PER_RUN=8
GLOBAL_QUERIES=(
 '("personal finance" OR "tax saving" OR "mutual funds" OR "fixed deposit") India when:7d',
 '("health insurance" OR "home loan" OR "credit card" OR "retirement planning") India when:7d',
)
def rss_url(query):
    return RSS_BASE+"?"+urlencode({"q":query,"hl":"en-IN","gl":"IN","ceid":"IN:en"})
def domain_matches(url,domain):
    host=(urlparse(url).hostname or "").lower().removeprefix("www.")
    return host==domain or host.endswith("."+domain)
def allowed_link(url):
    parsed=urlparse(url)
    host=(parsed.hostname or "").lower()
    return parsed.scheme=="https" and (host=="news.google.com" or host.endswith(".news.google.com"))
def topic_query(domain,topic):
    return "site:"+domain+" "+topic+" when:7d"
def clean_title(title,source_name):
    title=cleanup(title)
    # Google appends source labels after a hyphen in RSS headings.
    if source_name and title.lower().endswith(" - "+source_name.lower()):
        title=title[:-(len(source_name)+3)].strip()
    return title[:280]
def parse_google_news(xml, now=None, expected_domain=None):
    now=now or datetime.now(timezone.utc)
    try: root=ET.fromstring(xml)
    except ET.ParseError:return []
    rows=[]
    for node in root.findall(".//item")[:100]:
        raw_title=first_text(node,["title"])
        source_el=node.find("source")
        publisher=cleanup("".join(source_el.itertext())) if source_el is not None else ""
        source_url=source_el.attrib.get("url","") if source_el is not None else ""
        source_domain=(urlparse(source_url).hostname or "").lower().removeprefix("www.")
        if expected_domain and not domain_matches(source_url,expected_domain):
            continue
        if not source_domain or not publisher:
            continue
        # Only known Indian PF publisher domains; broad query can also return
        # unlisted relevant sources, but not unrelated unknown outlets.
        if not any(domain_matches(source_url,d) for _,d in PF_SOURCES):
            continue
        title=clean_title(raw_title,publisher)
        if len(title)<15 or not pf_match(title):
            continue
        link=cleanup(first_text(node,["link"]))
        if not allowed_link(link):
            continue
        d=feed_date(first_text(node,["pubDate"]))
        if not d or d>now+timedelta(hours=2) or d<max(pf_cutoff(now),now-timedelta(days=7)):
            continue
        rows.append({
            "id":link, "url":link, "title":title,
            "source":publisher+" • Google News", "domain":source_domain,
            "region":"india","sector":"Personal Finance","desk":"personal-finance",
            "seen":d.isoformat(),"time_basis":"google_rss",
            "language":"English","origin":"google-news-rss",
            "link_type":"google-news-redirect","sourcecountry":"India"
        })
    return rows
def fetch_feed(query,expected_domain=None,opener=None,now=None):
    opener=opener or urlopen
    req=Request(rss_url(query),headers={
        "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; attributed RSS headline discovery)",
        "Accept":"application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.1"
    })
    with opener(req,timeout=14) as response:
        xml=response.read(MAX_BYTES)
    return parse_google_news(xml,now=now,expected_domain=expected_domain)
def collect_personal_finance(cycle=None):
    if cycle is None:
        cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    combinations=[(source,domain,topic) for source,domain in PF_SOURCES for topic in PF_TOPICS]
    start=(cycle*PER_RUN)%len(combinations)
    batch=[combinations[(start+i)%len(combinations)] for i in range(PER_RUN)]
    # Rotate the two broad topic searches and avoid more than nine calls/run.
    selected=[(topic_query(domain,topic),domain,source) for source,domain,topic in batch]
    selected.append((GLOBAL_QUERIES[cycle%len(GLOBAL_QUERIES)],None,"India-wide PF"))
    status={"queries":len(selected),"successful_feeds":0,"accepted":0,
            "by_source":{},"warnings":[],"discovery":"google-news-rss"}
    found={}
    for query,domain,source in selected:
        try:
            items=fetch_feed(query,expected_domain=domain)
            status["successful_feeds"]+=1
            status["by_source"][source]=status["by_source"].get(source,0)+len(items)
            for item in items:
                found[item["url"]]=item
        except Exception as exc:
            status["warnings"].append(source+": "+type(exc).__name__+": "+str(exc)[:85])
            print("PF Google News RSS unavailable",source,type(exc).__name__,str(exc)[:85],file=sys.stderr)
    status["accepted"]=len(found)
    return list(found.values()),status
if __name__=="__main__":
    rows,status=collect_personal_finance()
    print("PF indexed:",len(rows),status)
