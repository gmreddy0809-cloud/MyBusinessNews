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
 ("Science & Space","(scientific discovery OR space research OR astronomy OR exoplanet) when:2d"),
 ("Science & Space","(new species discovered OR dinosaur fossil OR paleontology) when:2d"),
 ("Science & Space","(robotics research OR new invention OR breakthrough technology) when:2d"),
 ("Science & Space","(ocean exploration OR deep sea discovery OR polar expedition) when:2d"),
 ("Environment & Nature","(wildlife conservation OR endangered animals OR animal rescue) when:2d"),
 ("Environment & Nature","(biodiversity OR rainforest OR coral reef OR nature discovery) when:2d"),
 ("Environment & Nature","(climate science OR sustainable cities OR forest restoration) when:2d"),
 ("Environment & Nature","(unusual weather OR volcano research OR earthquake science) when:2d"),
 ("Health & Wellbeing","(medical discovery OR health research OR public health) when:2d"),
 ("Health & Wellbeing","(nutrition study OR sleep science OR mental wellbeing) when:2d"),
 ("Health & Wellbeing","(new treatment research OR disease prevention OR healthcare innovation) when:2d"),
 ("Health & Wellbeing","(global health initiative OR community healthcare OR vaccination) when:2d"),
 ("Culture & Heritage","(archaeological discovery OR ancient artifacts OR heritage conservation) when:2d"),
 ("Culture & Heritage","(museum exhibition OR ancient civilization OR historical finding) when:2d"),
 ("Culture & Heritage","(traditional crafts OR cultural festival OR indigenous heritage) when:2d"),
 ("Culture & Heritage","(literature festival OR contemporary art OR world culture) when:2d"),
 ("Lifestyle & Living","(travel destinations OR hidden places OR nature tourism) when:2d"),
 ("Lifestyle & Living","(food traditions OR local cuisine OR culinary culture) when:2d"),
 ("Lifestyle & Living","(traditional lifestyle OR interesting architecture OR home design) when:2d"),
 ("Lifestyle & Living","(unusual travel OR cultural tourism OR unique festivals) when:2d"),
 ("People & Ideas","(human interest OR inspiring community OR local hero) when:2d"),
 ("People & Ideas","(social innovation OR volunteer rescue OR acts of kindness) when:2d"),
 ("People & Ideas","(extraordinary achievement OR remarkable people OR everyday heroes) when:2d"),
 ("People & Ideas","(unusual story OR world record OR remarkable discovery) when:2d"),
 ("Education & Careers","(education innovation OR school experiment OR student invention) when:2d"),
 ("Education & Careers","(university research OR science education OR learning initiative) when:2d"),
 ("Education & Careers","(scholarship program OR rural education OR educational access) when:2d"),
 ("Education & Careers","(skills training OR vocational education OR student achievement) when:2d"),
 ("World & Society","(interesting world news OR unusual global events OR surprising news) when:2d"),
 ("World & Society","(international human interest OR social change OR society) when:2d"),
 ("World & Society","(cities around the world OR urban innovations OR remarkable places) when:2d"),
 ("World & Society","(global discoveries OR extraordinary events OR unusual happenings) when:2d"),
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
    # Twelve varied searches each half-hour; all 32 themes within 90 minutes.
    per_run=12
    chosen=[TOPIC_QUERIES[(cycle*per_run+i)%len(TOPIC_QUERIES)] for i in range(per_run)]
    report={"queries":len(chosen),"successful_feeds":0,"accepted":0,"by_topic":{},"by_source":{},"warnings":[]}
    found={}
    locales=(("en-US","US","US:en"),("en-GB","GB","GB:en"),("en-IN","IN","IN:en"),("en-AU","AU","AU:en"),("en-CA","CA","CA:en"),("en-SG","SG","SG:en"),("en-ZA","ZA","ZA:en"))
    from concurrent.futures import ThreadPoolExecutor
    def fetch_topic(entry):
        i,(category,query)=entry
        hl,gl,ceid=locales[(cycle+i)%len(locales)]
        url=RSS_BASE+"?"+urlencode({"q":query,"hl":hl,"gl":gl,"ceid":ceid})
        try:
            req=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; worldwide headline discovery)",
                "Accept":"application/rss+xml,application/xml,text/xml;q=0.9"
            })
            with urlopen(req,timeout=12) as response:xml=response.read(MAX_BYTES)
            return category,parse_feed(xml,category),None
        except Exception as exc:
            return category,[],type(exc).__name__+": "+str(exc)[:90]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for category,items,error in pool.map(fetch_topic,enumerate(chosen)):
            if error:
                report["warnings"].append(category+": "+error)
                print("World discovery warning",category,error,file=sys.stderr)
                continue
            report["successful_feeds"]+=1
            report["by_topic"][category]=report["by_topic"].get(category,0)+len(items)
            for item in items:
                found[item["url"]]=item
                report["by_source"][item["source"]]=report["by_source"].get(item["source"],0)+1
    report["accepted"]=len(found)
    return list(found.values()),report
