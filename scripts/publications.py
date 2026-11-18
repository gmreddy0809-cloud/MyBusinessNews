#!/usr/bin/env python3
"""Publisher-permitted title/link RSS aggregation for two reader desks.

Sources are deliberately allowlisted by a documented publisher grant, not by
mere RSS technical availability. Never store story bodies, descriptions,
publisher images, or logos. Articles always open on the original site.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup, first_text, feed_date
from avi_ivi import topic_for

# Licensing notes:
# - The Conversation publishes CC BY-ND and offers Atom feeds. Keep only
#   credited story titles and direct URLs, not full text or images.
# - Dharani News explicitly supports RSS for aggregators, with attribution
#   and original link. Public link-only, informational use; not for
#   unauthorized mass republication or future monetization.
# - Eenadu, Sakshi, Andhrajyothy, Samayam, India Today, TOI, IE etc.
#   intentionally excluded until explicit public display permission.
FEEDS=[
 ("The Conversation", "https://theconversation.com/articles.atom?language=en", "english-magazines", "general"),
 ("The Conversation Health", "https://theconversation.com/au/health/articles.atom", "english-magazines", "health"),
 ("The Conversation Arts", "https://theconversation.com/uk/arts/articles.atom", "english-magazines", "Culture & Heritage"),
 ("Dharani News", "https://dharaninews.com/feed/", "telugu-patrikalu", "general"),
]
DOMAINS={"english-magazines":("theconversation.com",),"telugu-patrikalu":("dharaninews.com",)}
ATOM="{http://www.w3.org/2005/Atom}"
RSS_MAX_BYTES=1_300_000

def allowed_url(url,desk):
    p=urlparse(url)
    if p.scheme!="https" or not p.hostname:return False
    hostname=p.hostname.lower()
    return any(hostname==domain or hostname.endswith("."+domain) for domain in DOMAINS[desk])

def extract(xml):
    try:
        root=ET.fromstring(xml)
    except ET.ParseError:
        return []
    return root.findall(".//item") or root.findall(".//"+ATOM+"entry")

def find_link(node):
    direct=first_text(node,["link"])
    if direct.startswith("https://"):return direct
    for link in node.findall(ATOM+"link"):
        href=link.attrib.get("href","").strip()
        rel=link.attrib.get("rel","alternate")
        if href.startswith("https://") and rel in ("alternate",""):
            return href
    guid=first_text(node,["guid","id",ATOM+"id"])
    return guid if guid.startswith("https://") else ""

def title_topic(title,kind,desk):
    if kind=="health":return "Health & Wellbeing"
    if kind=="Culture & Heritage":return kind
    if desk=="telugu-patrikalu":return "Telugu News"
    return topic_for(title,"general") or "World & Society"

def parse_feed(xml,source,desk,kind,now=None):
    now=now or datetime.now(timezone.utc)
    out=[]
    for item in extract(xml)[:125]:
        title=cleanup(first_text(item,["title",ATOM+"title"]))
        url=cleanup(find_link(item))
        if not 12<=len(title)<=260 or not allowed_url(url,desk):continue
        if re.search(r"<(?:script|iframe|style)\b",title,re.I):continue
        raw=first_text(item,["pubDate","{http://purl.org/dc/elements/1.1/}date",ATOM+"published",ATOM+"updated"])
        dt=feed_date(raw)
        # A missing date must not make an older magazine article look newly
        # published. Keep only feed-stamped items, no inferred publication date.
        if not dt or dt>now+timedelta(hours=2) or dt<now-timedelta(days=7):continue
        out.append({
            "id":url,"url":url,"title":title,"source":source+" • RSS",
            "domain":urlparse(url).hostname.lower().removeprefix("www."),
            "region":"india" if desk=="telugu-patrikalu" else "world",
            "sector":title_topic(title,kind,desk),
            "seen":dt.isoformat(),"time_basis":"feed",
            "language":"Telugu" if desk=="telugu-patrikalu" else "English",
            "origin":"permitted-rss","desk":desk,
            "sourcecountry":"India" if desk=="telugu-patrikalu" else ""
        })
    return out

def collect_publications():
    links=[]
    status={"successful_feeds":0,"counts":{},"warnings":[]}
    for name,url,desk,kind in FEEDS:
        try:
            req=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; source-attributed headline reader)",
                "Accept":"application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9"})
            with urlopen(req,timeout=16) as response:
                payload=response.read(RSS_MAX_BYTES)
            items=parse_feed(payload,name,desk,kind)
            links.extend(items)
            status["successful_feeds"]+=1
            status["counts"][name]=len(items)
            print("Permitted RSS",name,"items",len(items),"bytes",len(payload),flush=True)
        except Exception as exc:
            status["warnings"].append(name+": "+str(exc)[:150])
            print("Permitted RSS unavailable",name,str(exc),file=sys.stderr,flush=True)
    # A magazine's own topic feeds frequently repeat articles from its all-feed.
    by_url={row["url"]:row for row in links}
    return list(by_url.values()),status
