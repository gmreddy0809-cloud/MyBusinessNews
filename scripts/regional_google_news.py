#!/usr/bin/env python3
"""AP/TG regional headline discovery through Google News RSS, not syndication.

Only dated titles, credited publisher names and Google News click-through links.
No publisher story bodies, snippets, images or inferred original publication times.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup, first_text, feed_date

RSS_URL="https://news.google.com/rss/search"
SOURCES=(
    ("Eenadu","eenadu.net"),
    ("Sakshi","sakshi.com"),
    ("Andhra Jyothy","andhrajyothy.com"),
    ("Namasthe Telangana","ntnews.com"),
    ("Telangana Today","telanganatoday.com"),
    ("The Hans India","thehansindia.com"),
    ("Greatandhra","greatandhra.com"),
    ("TV9 Telugu","tv9telugu.com"),
    ("NTV Telugu","ntvtelugu.com"),
    ("10TV Telugu","10tv.in"),
    ("V6 News","v6velugu.com"),
    ("News18 Telugu","telugu.news18.com"),
    ("The Hindu","thehindu.com"),
    ("Deccan Chronicle","deccanchronicle.com"),
    ("New Indian Express","newindianexpress.com"),
    ("Times of India","timesofindia.indiatimes.com"),
)
REGIONS=(
    '(Andhra Pradesh OR Amaravati OR Vijayawada OR Visakhapatnam OR Tirupati OR "ఆంధ్రప్రదేశ్" OR "అమరావతి" OR "విజయవాడ" OR "విశాఖ")',
    '(Telangana OR Hyderabad OR Warangal OR "తెలంగాణ" OR "హైదరాబాద్" OR "వరంగల్")'
)
AP=re.compile(r'ఆంధ్రప్రదేశ్|ఆంధ్ర ప్రదేశ్|అమరావతి|విశాఖ|విజయవాడ|తిరుపతి|గుంటూరు|కాకినాడ|నెల్లూరు|కర్నూలు|చంద్రబాబు|పవన్ కళ్యాణ్|జగన్|andhra pradesh|amaravati|visakhapatnam|vijayawada|tirupati|guntur|kakinada|nellore|chandrababu|pawan kalyan',re.I)
TG=re.compile(r'తెలంగాణ|హైదరాబాద్|సికింద్రాబాద్|వరంగల్|కరీంనగర్|ఖమ్మం|నిజామాబాద్|రేవంత్|కేసీఆర్|కేటీఆర్|telangana|hyderabad|secunderabad|warangal|karimnagar|khammam|revanth reddy',re.I)
GEO_NOISE=re.compile(r'weather in hyderabad|hyderabad weather today',re.I)

def region(title):
    ap=bool(AP.search(title)); tg=bool(TG.search(title))
    if ap and tg:return None  # Ambiguous multi-region coverage: do not force a state.
    if ap:return "andhra-pradesh"
    if tg:return "hyderabad" if re.search(r'హైదరాబాద్|సికింద్రాబాద్|hyderabad|secunderabad',title,re.I) else "telangana"
    return None

def valid_link(link):
    p=urlparse(link)
    return p.scheme=="https" and (p.hostname or "").lower()=="news.google.com"

def parse(xml,expected_domain,now=None):
    now=now or datetime.now(timezone.utc)
    try: root=ET.fromstring(xml)
    except ET.ParseError:return []
    out=[]
    for node in root.findall(".//item")[:100]:
        source=node.find("source")
        if source is None:continue
        publisher=cleanup("".join(source.itertext()))
        src=source.attrib.get("url","")
        hostname=(urlparse(src).hostname or "").lower().removeprefix("www.")
        if hostname!=expected_domain and not hostname.endswith("."+expected_domain):continue
        title=cleanup(first_text(node,["title"]))
        if publisher and title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if len(title)<15 or GEO_NOISE.search(title):continue
        place=region(title)
        if not place:continue
        link=cleanup(first_text(node,["link"]))
        if not valid_link(link):continue
        published=feed_date(first_text(node,["pubDate"]))
        if not published or published>now+timedelta(hours=2) or published<now-timedelta(days=7):continue
        out.append({
            "id":link,"url":link,"title":title[:280],
            "source":publisher+" • Google News","domain":hostname,
            "region":place,"sector":"Regional General News",
            "seen":published.isoformat(),"time_basis":"google_rss",
            "origin":"google-news-rss","desk":"regional-general",
            "language":"Telugu/English","sourcecountry":"India",
            "link_type":"google-news-redirect"
        })
    return out

def collect_telanganatoday_rss(now=None):
    """Poll publisher's public RSS for attributed headlines and direct links only."""
    now=now or datetime.now(timezone.utc)
    endpoint="https://telanganatoday.com/feed"
    req=Request(endpoint,headers={
        "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; headline link reader)",
        "Accept":"application/rss+xml,application/xml,text/xml;q=0.9"
    })
    with urlopen(req,timeout=15) as response:
        xml=response.read(1_600_000)
    root=ET.fromstring(xml)
    found={}
    for node in root.findall(".//item")[:150]:
        title=cleanup(first_text(node,["title"]))
        link=cleanup(first_text(node,["link"]))
        hostname=(urlparse(link).hostname or "").lower().removeprefix("www.")
        if hostname!="telanganatoday.com" or not link.startswith("https://"):continue
        if not 15<=len(title)<=280:continue
        published=feed_date(first_text(node,["pubDate"]))
        if not published or published>now+timedelta(hours=2) or published<now-timedelta(days=7):continue
        place=region(title)
        # Headlines need explicit AP/TG evidence, or a clear publisher section path.
        path=urlparse(link).path.lower()
        if not place and re.search(r"/(?:hyderabad|telangana)/",path):place="hyderabad" if "/hyderabad/" in path else "telangana"
        if not place and re.search(r"/(?:andhra-pradesh|andhra)/",path):place="andhra-pradesh"
        if not place:continue
        found[link]={
            "id":link,"url":link,"title":title,"source":"Telangana Today • RSS",
            "domain":"telanganatoday.com","region":place,
            "sector":"Regional General News","desk":"regional-general",
            "seen":published.isoformat(),"time_basis":"feed","origin":"publisher-rss",
            "language":"English","sourcecountry":"India"
        }
    return list(found.values())

def collect_regional(cycle=None):
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    # Six source/state checks every half hour; all 32 combinations rotate.
    total=len(SOURCES)*len(REGIONS)
    chosen=[(SOURCES[((cycle*6+i)%total)//len(REGIONS)],REGIONS[(cycle*6+i)%len(REGIONS)]) for i in range(6)]
    status={"queries":len(chosen),"successful_feeds":0,"accepted":0,"by_source":{},"warnings":[]}
    found={}
    # Dedicated Telangana Today RSS every run; Google News remains a backup.
    try:
        direct=collect_telanganatoday_rss()
        status["successful_feeds"]+=1
        status["by_source"]["Telangana Today RSS"]=len(direct)
        for item in direct:found[item["url"]]=item
    except Exception as exc:
        status["warnings"].append("Telangana Today RSS: "+type(exc).__name__+": "+str(exc)[:80])
        print("Telangana Today RSS unavailable",type(exc).__name__,str(exc)[:80],file=sys.stderr)
    for (name,domain),location in chosen:
        query="site:"+domain+" "+location+" when:7d"
        url=RSS_URL+"?"+urlencode({"q":query,"hl":"en-IN","gl":"IN","ceid":"IN:en"})
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; attributed regional headline discovery)","Accept":"application/rss+xml,application/xml,text/xml;q=0.9"})
            with urlopen(req,timeout=14) as response:xml=response.read(1_600_000)
            rows=parse(xml,domain)
            status["successful_feeds"]+=1
            status["by_source"][name]=status["by_source"].get(name,0)+len(rows)
            for item in rows:found[item["url"]]=item
        except Exception as exc:
            status["warnings"].append(name+": "+type(exc).__name__+": "+str(exc)[:80])
            print("Regional Google News discovery warning",name,type(exc).__name__,str(exc)[:80],file=sys.stderr)
    status["accepted"]=len(found)
    return list(found.values()),status
