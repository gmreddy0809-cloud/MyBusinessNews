#!/usr/bin/env python3
"""Hyderabad Mail: city-local and real-estate headline links via public RSS.

RSS is a discovery mechanism, not a syndicated-content licence. Only store
publisher-attributed title, direct article URL and RSS date/category metadata.
Never download/publish article body or copy snippets from the feed.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from rss_sources import cleanup, first_text, feed_date
from regional_google_news import region as tagged_region
from hyderabad_real_estate import HYD, classify as classify_realty

FEEDS = (
    ("latest", "https://hyderabadmail.com/feed/"),
    # Conventional WordPress category endpoint; may not be enabled by publisher.
    ("real-estate", "https://hyderabadmail.com/category/real-estate/feed/"),
)
DOMAIN = "hyderabadmail.com"
STRONG_BUSINESS = re.compile(
    r"real estate|realty|property|office leasing|office space|commercial lease|"
    r"land auction|property deal|developers?|construction projects?|"
    r"industrial park|GCC|global capability|startup|funding|"
    r"company (?:launch|invest|expand)|investment|acquisition|"
    r"commercial real estate|retail rentals?|"
    r"రియల్ ఎస్టేట్|ప్రాపర్టీ|భూముల వేలం|ఆఫీస్ లీజు|పెట్టుబడులు", re.I
)
AP_TAG = re.compile(
    r"andhra pradesh|visakhapatnam|vijayawada|tirupati|amaravati|"
    r"ఆంధ్రప్రదేశ్|విశాఖ|విజయవాడ|తిరుపతి|అమరావతి",re.I
)
TG_TAG = re.compile(
    r"telangana|rangareddy|ranga reddy|medchal|hyderabad|warangal|"
    r"siddipet|khammam|nizamabad|తెలంగాణ|రంగారెడ్డి|హైదరాబాద్|వరంగల్",re.I
)
CITY_CATEGORIES = re.compile(
    r"hyderabad|pakka local|gated communities|gachibowli|madhapur|"
    r"jubilee hills|banjara hills|ameerpet|charminar|kukatpally|"
    r"manikonda|miyapur|secunderabad|tarnaka|uppal|nagole|"
    r"nampally|koti|bachupally|nizampet|hitech|hitec|shaikpet",re.I
)

def _is_direct_source(link):
    parsed=urlparse(link)
    hostname=(parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme=="https" and hostname==DOMAIN

def _categories(node):
    return [cleanup("".join(e.itertext())) for e in node.findall("category") if cleanup("".join(e.itertext()))]

def _place(title,categories):
    title_region=tagged_region(title)
    if title_region:return title_region
    if HYD.search(title):return "hyderabad"
    cat=" ".join(categories)
    if AP_TAG.search(cat):return "andhra-pradesh"
    if CITY_CATEGORIES.search(cat):return "hyderabad"
    if TG_TAG.search(cat):return "telangana"
    return None

def parse_feed(xml,now=None,feed_name="latest"):
    now=now or datetime.now(timezone.utc)
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    found=[]
    for node in root.findall(".//item"):
        title=cleanup(first_text(node,["title"]))
        link=cleanup(first_text(node,["link"]))
        if not 12<=len(title)<=280 or not _is_direct_source(link):continue
        dt=feed_date(first_text(node,["pubDate"]))
        if not dt or dt<now-timedelta(days=7) or dt>now+timedelta(hours=2):continue
        categories=_categories(node)
        location=_place(title,categories)
        if location not in ("hyderabad","telangana","andhra-pradesh","ap-tg"):continue
        realty_category=(feed_name=="real-estate" or any(
            re.search(r"real[ -]?estate|property",category,re.I) for category in categories))
        # An explicitly tagged real-estate article is meaningful even when a
        # short headline lacks the generic word "property" or "housing".
        realty=bool(realty_category and location in ("hyderabad","telangana"))
        if not realty and location=="hyderabad":
            realty=classify_realty(title) is not None
        kind=(classify_realty(title) or "Market News") if realty else ""
        business=bool(realty or STRONG_BUSINESS.search(title))
        # Hyderabad business tab is business only, while city-local general
        # stories remain available through Telangana and AP+TG general tabs.
        desk="regional-business" if business else "regional-general"
        found.append({
            "id":link,"url":link,"title":title,
            "source":"Hyderabad Mail • RSS","domain":DOMAIN,
            "region":location,"sector":"Real Estate" if realty else (
                "Other Business" if business else "Regional General News"),
            "desk":desk,"real_estate_kind":kind,
            "regional_business":business,
            "seen":dt.isoformat(),"time_basis":"feed","origin":"publisher-rss",
            "sourcecountry":"India","language":"English",
            "hyderabad_mail_category":categories[0] if categories else "",
        })
    return found

def collect_hyderabad_mail():
    status={"feeds_configured":len(FEEDS),"successful_feeds":0,
            "accepted":0,"realty":0,"business":0,"general":0,
            "by_feed":{},"warnings":[]}
    found={}
    def fetch(pair):
        name,url=pair
        req=Request(url,headers={
            "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; source-linked headline reader)",
            "Accept":"application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.1",
        })
        try:
            with urlopen(req,timeout=12) as response:xml=response.read(1_500_000)
            return name,parse_feed(xml,feed_name=name),None
        except Exception as exc:
            return name,[],type(exc).__name__+": "+str(exc)[:130]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for name,rows,error in pool.map(fetch,FEEDS):
            if error:
                status["warnings"].append(name+": "+error)
                continue
            status["successful_feeds"]+=1
            status["by_feed"][name]=len(rows)
            for row in rows:
                prior=found.get(row["url"])
                # Preserve the explicit property category if a general feed
                # had a less informative classification for the same URL.
                if not prior or (row["real_estate_kind"] and not prior["real_estate_kind"]):
                    found[row["url"]]=row
    for row in found.values():
        if row["real_estate_kind"]:status["realty"]+=1
        elif row["desk"]=="regional-business":status["business"]+=1
        else:status["general"]+=1
    status["accepted"]=len(found)
    return list(found.values()),status

if __name__=="__main__":
    rows,status=collect_hyderabad_mail()
    print("Hyderabad Mail",len(rows),"headlines",status)
