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
# - Oneindia Telugu maintains publisher-operated RSS subscriptions at
#   https://telugu.oneindia.com/rss.html. Extract only the source-attributed
#   headline and direct link, never text, photos, feed descriptions or snippets.
#   Its RSS availability is not permission to republish full stories.
# - Eenadu, Sakshi, Andhrajyothy, Samayam, Namasthe Telangana etc.
#   excluded from RSS ingestion without clear external-display permission.
FEEDS=[
 ("The Conversation", "https://theconversation.com/articles.atom?language=en", "english-magazines", "general"),
 ("The Conversation Health", "https://theconversation.com/au/health/articles.atom", "english-magazines", "health"),
 ("The Conversation Arts", "https://theconversation.com/uk/arts/articles.atom", "english-magazines", "Culture & Heritage"),
 ("The Conversation US", "https://theconversation.com/us/articles.atom", "english-magazines", "general"),
 ("The Conversation Australia", "https://theconversation.com/au/articles.atom", "english-magazines", "general"),
 ("The Conversation Environment", "https://theconversation.com/au/environment/articles.atom", "english-magazines", "Environment & Nature"),
 ("The Conversation Education", "https://theconversation.com/uk/education/articles.atom", "english-magazines", "Education & Careers"),
 ("Oneindia Telugu", "https://telugu.oneindia.com/rss/feeds/oneindia-telugu-fb.xml", "telugu-patrikalu", "general"),
 ("Oneindia Telugu", "https://telugu.oneindia.com/rss/feeds/telugu-news-fb.xml", "telugu-patrikalu", "general"),
 ("Oneindia Telugu", "https://telugu.oneindia.com/rss/feeds/telugu-health-fb.xml", "telugu-patrikalu", "health"),
 ("Oneindia Telugu", "https://telugu.oneindia.com/rss/feeds/telugu-science-technology-fb.xml", "telugu-patrikalu", "Science & Space"),
 ("Oneindia Telugu", "https://telugu.oneindia.com/rss/feeds/education-jobs-fb.xml", "telugu-patrikalu", "Education & Careers"),
 ("Oneindia Telugu", "https://telugu.oneindia.com/rss/feeds/telugu-entertainment-fb.xml", "telugu-patrikalu", "Culture & Heritage"),
 ("Dharani News", "https://dharaninews.com/feed/", "telugu-patrikalu", "general"),
]
DOMAINS={"english-magazines":("theconversation.com",),"telugu-patrikalu":("dharaninews.com","telugu.oneindia.com")}
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
    if kind in ("Culture & Heritage","Education & Careers","Environment & Nature","Science & Space"):return kind
    if desk=="telugu-patrikalu":return "Telugu News"
    if re.search(r"\b(?:acupuncture|weight loss|nutrition|acne|vaccine|vaccination|blood pressure|mental health|diabetes|medical|health|disease|heart health|gut bacteria)\b",title,re.I):
        return "Health & Wellbeing"
    if re.search(r"\b(?:sleep|recipes?|cooking|eating|foods?|groceries|meal|organic|holiday|travel|backpackers?|tourism|parents?|parenting|families|family|baby|garden|hobbies|fashion|wellness|diet|fitness|beauty tips|vacation|work.life|healthy living)\b",title,re.I):
        return "Lifestyle & Living"
    return topic_for(title,"general") or "World & Society"

def telugu_region(title,url=''):
    """Assign regional tag only when a place is explicitly mentioned."""
    if re.search(r"హైదరాబాద్|హైద‌రాబాద్|సికింద్రాబాద్|గచ్చిబౌలి|Hyderabad|Secunderabad",title,re.I):
        return "hyderabad"
    if re.search(r"ఆంధ్రప్రదేశ్|ఆంధ్ర ప్రదేశ్|అమరావతి|విశాఖపట్నం|విజయవాడ|తిరుపతి|Andhra Pradesh",title,re.I):
        return "andhra-pradesh"
    if re.search(r"తెలంగాణ|వరంగల్|కరీంనగర్|ఖమ్మం|Telangana",title,re.I):
        return "telangana"
    path=urlparse(url).path.lower()
    if "/andhra-pradesh/" in path or "/ap/" in path:return "andhra-pradesh"
    if "/telangana/" in path:return "telangana"
    if "/hyderabad/" in path:return "hyderabad"
    return "india"

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
        if not dt or dt>now+timedelta(hours=2) or dt<now-timedelta(days=30 if source=="Dharani News" else 7):continue
        out.append({
            "id":url,"url":url,"title":title,"source":source+" • RSS",
            "domain":urlparse(url).hostname.lower().removeprefix("www."),
            "region":telugu_region(title,url) if desk=="telugu-patrikalu" else "world",
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
            status["counts"][name]=status["counts"].get(name,0)+len(items)
            print("Permitted RSS",name,"items",len(items),"bytes",len(payload),flush=True)
            if not items and desk=="telugu-patrikalu":
                sample=[]
                for node in extract(payload)[:3]:
                    sample.append({"title":cleanup(first_text(node,["title",ATOM+"title"]))[:90],
                        "url":find_link(node)[:120],
                        "date":first_text(node,["pubDate",ATOM+"updated"])[:65]})
                print("Telugu RSS diagnostic",name,"rss_nodes",len(extract(payload)),"sample",sample,flush=True)
        except Exception as exc:
            status["warnings"].append(name+": "+str(exc)[:150])
            print("Permitted RSS unavailable",name,str(exc),file=sys.stderr,flush=True)
    # A magazine's own topic feeds frequently repeat articles from its all-feed.
    by_url={row["url"]:row for row in links}
    return list(by_url.values()),status
