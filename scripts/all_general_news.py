#!/usr/bin/env python3
"""India and World ALL-TOPIC headline discovery (separate from business desks).

Uses public Google News RSS topic/top-story feeds. Saves credited headlines,
Google News click-through URLs, and RSS dates, not copyrighted article bodies.
The provider's feed selection is finite; it does NOT guarantee every story.
"""
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from rss_sources import cleanup, first_text, feed_date
from regional_google_news import region as ap_tg_region

BASE="https://news.google.com/rss"
TOPICS=("WORLD","NATION","TECHNOLOGY","ENTERTAINMENT","SPORTS","SCIENCE","HEALTH","BUSINESS")
LOCALES=(
    ("IN","en-IN","IN:en"),
    ("IN","hi-IN","IN:hi"),
    ("IN","te","IN:te"),
    ("US","en-US","US:en"),
    ("GB","en-GB","GB:en"),
    ("AU","en-AU","AU:en"),
    ("CA","en-CA","CA:en"),
    ("SG","en-SG","SG:en"),
    ("ZA","en-ZA","ZA:en"),
)
TOPIC_LABELS={
    "WORLD":"World & Society","NATION":"National News",
    "TECHNOLOGY":"Technology","ENTERTAINMENT":"Entertainment",
    "SPORTS":"Sports","SCIENCE":"Science","HEALTH":"Health",
    "BUSINESS":"Business & Economy","TOP":"Top Stories",
}
def parse(xml,desk,topic="TOP",now=None):
    """No subject/content keyword filtering: every dated, valid headline qualifies."""
    now=now or datetime.now(timezone.utc)
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    out=[]
    for node in root.findall(".//item"):
        source=node.find("source")
        if source is None:continue
        publisher=cleanup("".join(source.itertext()))
        hostname=(urlparse(source.attrib.get("url","")).hostname or "").lower().removeprefix("www.")
        if not publisher or not hostname or "." not in hostname:continue
        title=cleanup(first_text(node,["title"]))
        if publisher and title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if not 10<=len(title)<=300:continue
        link=cleanup(first_text(node,["link"]))
        parsed=urlparse(link)
        if parsed.scheme!="https" or (parsed.hostname or "").lower()!="news.google.com":continue
        published=feed_date(first_text(node,["pubDate"]))
        if not published or published>now+timedelta(hours=2) or published<now-timedelta(days=7):continue
        location=(ap_tg_region(title) or "india") if desk=="india-general" else "world"
        out.append({
            "id":link,"url":link,"title":title,"source":publisher+" • Google News",
            "domain":hostname,"region":location,"desk":desk,
            "sector":TOPIC_LABELS.get(topic,"General News"),
            "seen":published.isoformat(),"time_basis":"google_rss",
            "language":"Mixed","sourcecountry":"India" if desk=="india-general" else "",
            "origin":"google-news-rss","link_type":"google-news-redirect",
        })
    return out

def collect_general_news(cycle=None):
    """Every run includes all-topic top stories; rotates other country/topic feeds."""
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    jobs=[]
    for region in ("india-general","world-general"):
        if region=="india-general":
            locales=[LOCALES[0],LOCALES[1],LOCALES[2]]
            topic="NATION"
        else:
            locales=[LOCALES[3],LOCALES[4],LOCALES[5],LOCALES[6],LOCALES[7],LOCALES[8]]
            topic="WORLD"
        # Home/top stories and local/national news always; rotate every other topic.
        core_locale=locales[0]
        country,hl,ceid=core_locale
        params=urlencode({"hl":hl,"gl":country,"ceid":ceid})
        jobs.append((region,"TOP",BASE+"?"+params))
        jobs.append((region,topic,BASE+"/headlines/section/topic/"+topic+"?"+params))
        for i in range(5):
            loc=locales[(cycle+i)%len(locales)]
            section=TOPICS[(cycle*5+i)%len(TOPICS)]
            c,h,ce=loc
            args=urlencode({"hl":h,"gl":c,"ceid":ce})
            jobs.append((region,section,BASE+"/headlines/section/topic/"+section+"?"+args))
        # One broad search per region with no category terms, for fresh local/global headlines.
        query="India when:2d" if region=="india-general" else '("World news" OR "international news") when:2d'
        jobs.append((region,"TOP",BASE+"/search?"+urlencode({
            "q":query,"hl":hl,"gl":country,"ceid":ceid
        })))
    status={"queries":len(jobs),"successful_feeds":0,"accepted":0,
            "by_desk":{"india-general":0,"world-general":0},"warnings":[]}
    found={}
    def fetch(job):
        desk,topic,url=job
        try:
            request=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; credited headline index)",
                "Accept":"application/rss+xml,application/xml,text/xml;q=0.9",
            })
            with urlopen(request,timeout=12) as resp:xml=resp.read(1_800_000)
            return desk,parse(xml,desk,topic),None
        except Exception as exc:
            return desk,[],type(exc).__name__+": "+str(exc)[:100]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for desk,rows,error in pool.map(fetch,jobs):
            if error:
                status["warnings"].append(desk+": "+error)
                continue
            status["successful_feeds"]+=1
            status["by_desk"][desk]+=len(rows)
            for row in rows:found[row["url"]]=row
    status["accepted"]=len(found)
    return list(found.values()),status

if __name__=="__main__":
    rows,status=collect_general_news()
    print("All-topic headlines",len(rows),status)
