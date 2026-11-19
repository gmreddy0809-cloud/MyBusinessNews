#!/usr/bin/env python3
"""Global 'Avii Ivii' discovery from dated Google News RSS headline links.

Discovery, not publisher syndication. Store attributed titles, Google News links
and Google feed timestamps only, never third-party descriptions or story bodies.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup, first_text, feed_date
from avi_ivi import topic_for

RSS_BASE="https://news.google.com/rss/search"
# A rotating collection of worldwide, non-business editorial topics.
TOPIC_QUERIES=(
 ("Science & Space",'("scientific discovery" OR "space exploration" OR astronomy OR paleontology) when:7d'),
 ("Environment & Nature",'("wildlife conservation" OR biodiversity OR endangered species OR ecosystem) when:7d'),
 ("Health & Wellbeing",'("medical discovery" OR "public health" OR "health research" OR "medical research") when:7d'),
 ("Education & Careers",'("education innovation" OR "university research" OR "student achievement") when:7d'),
 ("Culture & Heritage",'("archaeological discovery" OR "cultural heritage" OR "ancient history") when:7d'),
 ("Lifestyle & Living",'("travel destinations" OR "food culture" OR "living traditions") when:7d'),
 ("People & Ideas",'("human interest" OR "community hero" OR "inspiring story") when:7d'),
 ("Science & Space",'("new species discovered" OR "scientists discover" OR "rare discovery") when:7d'),
 ("Environment & Nature",'("ocean discovery" OR "forest restoration" OR "animal rescue") when:7d'),
 ("Culture & Heritage",'("museum exhibition" OR "world heritage" OR "historic discovery") when:7d'),
 ("People & Ideas",'("remarkable people" OR "social innovation" OR "local community initiative") when:7d'),
 ("Lifestyle & Living",'("unusual places" OR "world travel" OR "cultural festival") when:7d'),
 ("Health & Wellbeing",'("nutrition research" OR "sleep science" OR "health breakthrough") when:7d'),
 ("Education & Careers",'("learning innovation" OR "school education" OR "skills training") when:7d'),
 ("Science & Space",'("technology breakthrough" OR "scientific innovation" OR "robotics research") when:7d'),
 ("People & Ideas",'("extraordinary story" OR "rare event" OR "unexpected discovery") when:7d'),
)
# Generic headlines and pure financial-market news are outside this desk.
EXCLUDE=re.compile(r'\b(?:stock price|share price|earnings per share|quarterly results|IPO allotment|mutual fund NAV|live updates|live blog)\b',re.I)
MAX_BYTES=1_500_000

def parse_feed(xml,category,now=None):
    now=now or datetime.now(timezone.utc)
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    found=[]
    for item in root.findall(".//item")[:100]:
        title=cleanup(first_text(item,["title"]))
        src=item.find("source")
        if src is None:continue
        publisher=cleanup("".join(src.itertext()))
        original=src.attrib.get("url","")
        hostname=(urlparse(original).hostname or "").lower().removeprefix("www.")
        if not publisher or not hostname or "." not in hostname:continue
        if title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if not 18<=len(title)<=280 or EXCLUDE.search(title):continue
        link=cleanup(first_text(item,["link"]))
        parsed=urlparse(link)
        if parsed.scheme!="https" or parsed.hostname!="news.google.com":continue
        stamp=feed_date(first_text(item,["pubDate"]))
        if not stamp or stamp>now+timedelta(hours=2) or stamp<now-timedelta(days=7):continue
        found.append({
            "id":link,"url":link,"title":title,
            "source":publisher+" • Google News","domain":hostname,
            "region":"world","sector":topic_for(title,"general") if topic_for(title,"general")!="World & Society" else category,
            "seen":stamp.isoformat(),"time_basis":"google_rss",
            "sourcecountry":"","origin":"google-news-rss",
            "desk":"avi-ivi","language":"English",
            "link_type":"google-news-redirect"
        })
    return found

def collect_world(cycle=None):
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    # Four topic searches per scheduled run, all 16 covered within two hours.
    chosen=[TOPIC_QUERIES[(cycle*4+i)%len(TOPIC_QUERIES)] for i in range(4)]
    report={"queries":len(chosen),"successful_feeds":0,"accepted":0,"by_topic":{},"warnings":[]}
    found={}
    for category,query in chosen:
        url=RSS_BASE+"?"+urlencode({"q":query,"hl":"en-US","gl":"US","ceid":"US:en"})
        try:
            req=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; worldwide headline discovery)",
                "Accept":"application/rss+xml,application/xml,text/xml;q=0.9"
            })
            with urlopen(req,timeout=14) as response:xml=response.read(MAX_BYTES)
            items=parse_feed(xml,category)
            report["successful_feeds"]+=1
            report["by_topic"][category]=report["by_topic"].get(category,0)+len(items)
            for item in items:found[item["url"]]=item
        except Exception as exc:
            report["warnings"].append(category+": "+type(exc).__name__+": "+str(exc)[:90])
            print("World discovery warning",category,type(exc).__name__,str(exc)[:90],file=sys.stderr)
    report["accepted"]=len(found)
    return list(found.values()),report
