#!/usr/bin/env python3
"""Avii Ivii: public official source headline discovery, not syndication of articles.

Editorial policy:
- Only title, original URL, source and accurately labelled timestamp are stored.
- Never present government/agency press releases as independent news reporting.
- Publisher/magazine and Telugu newspaper discovery is via reader-initiated site links.
"""
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup, first_text, feed_date

PUBLIC_FEEDS = [
    ("PIB India", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1", "india", "government"),
    ("NASA", "https://www.nasa.gov/news-release/feed/", "world", "science"),
    ("WHO", "https://www.who.int/rss-feeds/news-english.xml", "world", "health"),
    ("UN News", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "world", "general"),
    ("UN News Climate", "https://news.un.org/feed/subscribe/en/news/topic/climate-change/feed/rss.xml", "world", "environment"),
]
ALLOWED_DOMAINS = ("pib.gov.in", "nasa.gov", "science.nasa.gov", "who.int", "news.un.org")
AREAS = [
    ("hyderabad", re.compile(r"\b(?:Hyderabad|Secunderabad|Shamshabad|Gachibowli|Medchal)\b", re.I)),
    ("andhra-pradesh", re.compile(r"andhra pradesh|visakhapatnam|vizag|amaravati|vijayawada|tirupati|kakinada|guntur|nellore", re.I)),
    ("telangana", re.compile(r"\btelangana\b|warangal|karimnagar|sangareddy|khammam", re.I)),
]
TOPICS = [
    ("Health & Wellbeing", re.compile(r"health|medical|hospital|public health|cancer|diabetes|ebola|measles|pandemic|outbreak|malnutrition|disease|virus|vaccin|patient|nutrit|mental health|maternal|tuberculosis|medicine|drug safety|healthcare|epidemic|wellness|clinical", re.I)),
    ("Environment & Nature", re.compile(r"climate|pollution|environment|air quality|wildlife|forest|conservation|biodiversity|coral|weather|cyclone|flood|drought|sustainab|carbon|temperature|river|coastal|ecosystem", re.I)),
    ("Science & Space", re.compile(r"nasa|space|moon|mars|telescope|satellite|scientist|research|discovery|physics|astronom|galaxy|asteroid|rocket|artemis|spacecraft|laboratory|ai research|science", re.I)),
    ("Education & Careers", re.compile(r"school|university|college|student|teacher|education|scholarship|examination|literacy|skills|apprentice|research fellow|curriculum|employment|career|learning", re.I)),
    ("Culture & Heritage", re.compile(r"culture|heritage|museum|festival|\bart\b|literat|\bbooks?\b|author|creative|film|music|historic|tradition|archaeolog|cuisine|crafts|language", re.I)),
    ("Politics & Public Affairs", re.compile(r"parliament|cabinet|election|politic|governance|court|supreme court|legislation|law|policy|constitution|rights|assembly|minister|diplomacy|foreign affairs|democrac|bilateral|treaty", re.I)),
    ("Lifestyle & Living", re.compile(r"\blifestyle\b|\bwellbeing\b|\btravel tips\b|\bfood recipes?\b|\brecipe\b|\bcuisine\b|\bfitness\b|\bexercise\b|\bfashion\b|\btouris\w*\b|\bbeauty\b|\bhome decor\b|\bhousing design\b|\bsleep\b|\bdiet\b|\bparenting\b|\bwork.life\b", re.I)),
    ("People & Ideas", re.compile(r"women|youth|community|village|tribal|innovation|volunteer|inspir|empower|social|rural|local hero|people|citizen|livelihood|accessibility", re.I)),
]
LOW_SIGNAL = re.compile(r"^(\s*(?:minister|union minister|secretary|president)\s+(?:greets|congratulates|condoles|extends greetings|visits|attends)\b)|(?:special campaign \d+|swachhata pakhwada|birth anniversary greetings)", re.I)

def domain_ok(url):
    parts=urlparse(url)
    hostname=(parts.hostname or "").lower()
    return parts.scheme=="https" and any(hostname==d or hostname.endswith("."+d) for d in ALLOWED_DOMAINS)

def topic_for(title, mode):
    if mode=="science":
        if TOPICS[1][1].search(title):return "Environment & Nature"
        return "Science & Space"
    if mode=="health":return "Health & Wellbeing"
    if mode=="environment":return "Environment & Nature"
    for name,pattern in TOPICS:
        if pattern.search(title):return name
    return "World & Society" if mode=="general" else None

def region_for(title,base_region):
    for region,pattern in AREAS:
        if pattern.search(title):return region
    return base_region

def extract_items(xml):
    try:
        root=ET.fromstring(xml)
        return root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    except ET.ParseError:
        print("Avii Ivii RSS received partial XML; accepting only complete items",file=sys.stderr)
        found=[]
        wrapper=b'<root xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">'
        for raw in re.findall(rb"<item(?:\s[^>]*)?>[\s\S]*?</item>",xml,re.I):
            try:found.append(ET.fromstring(wrapper+raw+b"</root>")[0])
            except ET.ParseError:pass
        return found

def parse_feed(xml, name, region, mode, now=None):
    now=now or datetime.now(timezone.utc)
    found=[]
    for node in extract_items(xml)[:150]:
        title=cleanup(first_text(node,["title","{http://www.w3.org/2005/Atom}title"]))
        link=cleanup(first_text(node,["link","guid"]))
        if not link:
            atom=node.find("{http://www.w3.org/2005/Atom}link")
            if atom is not None:link=atom.attrib.get("href","")
        if len(title)<16 or len(title)>240 or not domain_ok(link) or LOW_SIGNAL.search(title):continue
        topic=topic_for(title,mode)
        if not topic:continue
        raw_date=first_text(node,["pubDate","{http://purl.org/dc/elements/1.1/}date","{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"])
        published=feed_date(raw_date)
        if published and (published>now+timedelta(hours=2) or published<now-timedelta(days=7)):continue
        source_domain=(urlparse(link).hostname or "").removeprefix("www.")
        found.append({
            "id":link,"url":link,"title":title,"source":name+" • Official",
            "domain":source_domain,"region":region_for(title,region),"sector":topic,
            "seen":published.isoformat() if published else now.isoformat(),
            "time_basis":"feed" if published else "first_seen",
            "sourcecountry":"India" if region=="india" else "",
            "origin":"official-rss","desk":"avi-ivi","language":"English"
        })
    return found

def collect_avi_ivi():
    found=[]
    report={"successful_feeds":0,"feed_matches":{},"warnings":[]}
    for name,url,region,mode in PUBLIC_FEEDS:
        try:
            req=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; source-linked public headlines)",
                "Accept":"application/rss+xml, application/xml, text/xml;q=0.9,*/*;q=0.2"})
            with urlopen(req,timeout=16) as response:
                payload=response.read(2_000_000)
            items=parse_feed(payload,name,region,mode)
            if not items:
                nodes=extract_items(payload)
                sample=[]
                for node in nodes[:2]:
                    sample.append({"title":cleanup(first_text(node,["title","{http://www.w3.org/2005/Atom}title"]))[:120],
                        "link":cleanup(first_text(node,["link","guid"]))[:160],
                        "date":first_text(node,["pubDate","{http://purl.org/dc/elements/1.1/}date"])[:60]})
                print("Avii Ivii source diagnostic",name,"bytes",len(payload),"rss_items",len(nodes),"sample",str(sample),flush=True)
            found.extend(items)
            report["successful_feeds"]+=1
            report["feed_matches"][name]=len(items)
            print("Avii Ivii official source",name,"selected",len(items),flush=True)
        except Exception as exc:
            report["warnings"].append(name+": "+str(exc)[:160])
            print("Avii Ivii official source warning",name,str(exc),file=sys.stderr,flush=True)
    return found,report

if __name__=="__main__":
    rows,report=collect_avi_ivi()
    print("Avii Ivii:",len(rows),"items",report)
