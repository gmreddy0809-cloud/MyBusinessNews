#!/usr/bin/env python3
"""Discover AMFI's official NFO and fundwise AUM RSS; only dated source links.

AMFI publicly lists RSS feed subscriptions at https://www.amfiindia.com/rss-feeds.
Do not copy NAV tables, fund performance data, summaries or article bodies.
"""
from datetime import datetime,timezone,timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from xml.etree import ElementTree as ET
import re,sys
from rss_sources import cleanup,first_text,feed_date
from desk_coverage import pf_cutoff

DIRECTORY="https://www.amfiindia.com/rss-feeds"
ATOM="{http://www.w3.org/2005/Atom}"
TOPICS=re.compile(r'new fund offer|\bnfo\b|fundwise aum|fund.?wise aum',re.I)
MAX_BYTES=1_800_000

def is_amfi_url(url):
    parsed=urlparse(url)
    domain=(parsed.hostname or '').lower()
    return parsed.scheme=="https" and (domain=="amfiindia.com" or domain.endswith(".amfiindia.com"))

class FeedLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.found=[];self.href=None;self.title=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a':
            self.href=attrs.get('href');self.title=[]
        elif tag=='link':
            href=attrs.get('href')
            if href and 'rss' in str(attrs.get('type','')).lower():
                self.found.append((href,attrs.get('title','RSS')))
    def handle_data(self,data):
        if self.href is not None:self.title.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:
            self.found.append((self.href,' '.join(self.title)))
            self.href=None;self.title=[]

def discover_feeds(html):
    parser=FeedLinks()
    parser.feed(html)
    urls=[]
    for href,label in parser.found:
        target=urljoin(DIRECTORY,href.strip())
        if not is_amfi_url(target):continue
        combined=(href+' '+label).lower()
        if TOPICS.search(combined) and ('rss' in combined or 'xml' in combined):
            if target not in urls:urls.append(target)
    return urls[:3]

def parse_amfi(xml,now=None):
    now=now or datetime.now(timezone.utc)
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    nodes=root.findall(".//item") or root.findall(".//"+ATOM+"entry")
    out=[]
    for node in nodes[:150]:
        title=cleanup(first_text(node,["title",ATOM+"title"]))
        link=first_text(node,["link"])
        if not link:
            for el in node.findall(ATOM+"link"):
                if el.get("rel","alternate")=="alternate":
                    link=el.get("href","").strip();break
        raw=first_text(node,["pubDate","{http://purl.org/dc/elements/1.1/}date",ATOM+"published",ATOM+"updated"])
        dated=feed_date(raw)
        if not (len(title)>=12 and is_amfi_url(link) and dated and pf_cutoff(now)<=dated<=now+timedelta(hours=2)):continue
        domain=(urlparse(link).hostname or '').lower().removeprefix('www.')
        out.append({"id":link,"url":link,"title":title,"source":"AMFI • Official",
                    "domain":domain,"region":"india","sector":"Personal Finance",
                    "desk":"personal-finance","origin":"official-rss",
                    "seen":dated.isoformat(),"time_basis":"feed",
                    "language":"English","sourcecountry":"India"})
    return out

def collect_amfi():
    status={"directory_checked":False,"feeds_found":0,"accepted":0,"warnings":[]}
    try:
        req=Request(DIRECTORY,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; RSS discovery)","Accept":"text/html"})
        with urlopen(req,timeout=9) as response:
            html=response.read(500_000).decode("utf-8","replace")
        status["directory_checked"]=True
        links=discover_feeds(html)
        status["feeds_found"]=len(links)
        found=[]
        for link in links:
            try:
                request=Request(link,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; official RSS reader)","Accept":"application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9"})
                with urlopen(request,timeout=10) as response:xml=response.read(MAX_BYTES)
                found.extend(parse_amfi(xml))
            except Exception as exc:
                status["warnings"].append(type(exc).__name__+": AMFI feed unavailable")
        result={item["url"]:item for item in found}
        status["accepted"]=len(result)
        return list(result.values()),status
    except Exception as exc:
        status["warnings"].append(type(exc).__name__+": AMFI directory unavailable")
        print("AMFI RSS discovery unavailable",type(exc).__name__,file=sys.stderr)
        return [],status
