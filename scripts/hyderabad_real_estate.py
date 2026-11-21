#!/usr/bin/env python3
"""Hyderabad real-estate headline discovery; source-linked, no syndicated content.

Monitors consultancy research, recorded office/property deals, residential
markets and official regulatory developments using Google News RSS discovery.
Stores a headline, publisher, link, Google RSS time and editorial classification.
Not a licensed feed from consultancies or an X/Twitter timeline.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from rss_sources import cleanup, first_text, feed_date

BASE = "https://news.google.com/rss/search"
# Strong city/location requirement: national reports without a stated Hyderabad
# angle stay in the primary news indexes, not the Hyderabad-specific desk.
HYD = re.compile(
    r"hyderabad|cyberabad|secunderabad|hitech city|hi.tech city|madhapur|"
    r"gachibowli|nanakramguda|financial district|kokapet|narsingi|tellapur|"
    r"kondapur|raidurg|shamshabad|nallagandla|bachupally|patancheru|"
    r"uppal|medchal|pocharam|mokila|kollur|kompally|shankarpally|"
    r"rangareddy|ranga reddy|neopolis|"
    r"హైదరాబాద్|సికింద్రాబాద్|గచ్చిబౌలి|మాదాపూర్|కోకాపేట|నార్సింగి|"
    r"కొండాపూర్|తెల్లాపూర్|శంషాబాద్|రంగారెడ్డి|నానక్‌రామ్‌గూడ|"
    r"రాయదుర్గం|పటాన్‌చెరు", re.I
)
PROPERTY = re.compile(
    r"real estate|realty|property|properties|housing|apartments?|"
    r"residential|office (?:space|leasing|market|rent|rentals?|building|transactions?)|"
    r"commercial (?:realty|real estate|property|office|space|leasing)|"
    r"office space|office leasing|commercial rent|rental yield|"
    r"land (?:deal|parcel|sale|auction|purchase|allotment|bank)|"
    r"plots?\b|floor space|built.up area|sq\.?\s?ft|square feet|"
    r"warehous(?:e|ing)|industrial parks?|retail spaces?|"
    r"real estate developer|property developers?|home builders?|housing construction|residential projects? launch|"
    r"rera\b|hmda\b|property registration(?:s)?\b|stamp duty|"
    r"ప్రాపర్టీ|రియల్ ఎస్టేట్|రియాల్టీ|ఇళ్ల|ఇళ్లు|గృహ|ఫ్లాట్లు|"
    r"భూమి|స్థలం|నిర్మాణ|లీజు|రిజిస్ట్రేషన్|ఇంటి ధర", re.I
)
REPORT = re.compile(
    r"jll|cbre|cushman|knight frank|colliers|savills|anarock|"
    r"propequity|prop.?tiger|cre matrix|propstack|vestian|"
    r"liases foras|report|survey|study|marketbeat|market dynamics|"
    r"market watch|market monitor|market snapshot|data shows|"
    r"quarterly|q[1-4][ -]?20\d\d|h[12][ -]?20\d\d", re.I
)
DEAL = re.compile(
    r"leases?|leased|pre.leases?|lease renewal|lease deal|"
    r"acquires?|acquisition|buys?|purchases?|sells?|sold|"
    r"land deals?|land auction|land sale|transaction|deal worth|"
    r"office deal|rent(?:al)? agreement|pre.?commitment|"
    r"లీజు|కొనుగోలు|విక్రయం|ఒప్పందం|భూముల వేలం", re.I
)
RULES = re.compile(
    r"tg.?rera|rera|hmda|ghmc|government order|"
    r"building permission|building permit|approval|"
    r"master plan|zoning|stamp duty|registration fee|"
    r"notice|penalty|court order|రెరా|అనుమతులు|ఆదేశాలు|నోటీసు", re.I
)
RESIDENTIAL = re.compile(
    r"residential|housing|homes?|apartments?|flats?|villas?|"
    r"homebuyers?|house prices?|home sales|new launches|"
    r"unsold inventory|గృహ|ఫ్లాట్లు|ఇళ్లు|ఇళ్ల|ఇంటి ధర", re.I
)

# Core Hyderabad coverage is checked every run. Rotating targeted searches
# expand research/deals coverage without relying on a single 100-result feed.
CORE = (
  '(Hyderabad OR Gachibowli OR Kokapet) ("real estate" OR property OR residential OR housing) when:7d',
  '(Hyderabad OR Madhapur OR "Financial District") ("office lease" OR "office space" OR "commercial real estate") when:7d',
  '(Hyderabad OR Kokapet OR Narsingi) (land deal OR land auction OR realty deal OR property transaction) when:7d',
  '("హైదరాబాద్" OR "గచ్చిబౌలి" OR "కోకాపేట") ("రియల్ ఎస్టేట్" OR "ప్రాపర్టీ" OR "ఫ్లాట్లు" OR "భూమి") when:7d',
  '(Hyderabad OR Telangana) (RERA OR HMDA OR residential registrations OR property prices) when:7d',
  '(Hyderabad OR Cyberabad) (JLL OR CBRE OR "Cushman" OR "Knight Frank" OR Colliers OR Savills) when:7d',
)
ROTATE = (
  '(Hyderabad OR Telangana) (ANAROCK OR "PropTiger" OR PropEquity OR "CRE Matrix" OR Propstack) when:7d',
  '(Hyderabad OR Telangana) (Vestian OR "Liases Foras" OR "NAREDCO" OR "CREDAI") when:7d',
  '(Hyderabad OR Gachibowli) (GCC OR coworking OR REIT OR data centre) (lease OR space OR rent) when:7d',
  '(Hyderabad OR Kokapet OR Tellapur) (villas OR apartments OR launches OR home sales) when:7d',
  '(Hyderabad OR Shamshabad OR Medchal) (warehouse OR industrial real estate OR logistics parks) when:7d',
  '(Hyderabad OR Telangana) (property registrations OR stamp duty OR land records OR TGRERA) when:7d',
  '(Hyderabad OR Madhapur OR Nanakramguda) (office supply OR vacancy OR absorption OR rentals) when:7d',
  '(Hyderabad OR Gachibowli OR Kollur) (developer OR builder OR construction project) when:7d',
)
CONSULTANT_DOMAINS=(
    "jll.com","cbre.co.in","cushmanwakefield.com","knightfrank.co.in",
    "colliers.com","savills.com","anarock.com"
)

def classify(title):
    if not HYD.search(title) or not PROPERTY.search(title):
        return None
    if RULES.search(title):
        kind="Regulation"
    elif DEAL.search(title):
        kind="Deals"
    elif REPORT.search(title):
        kind="Reports"
    elif RESIDENTIAL.search(title):
        kind="Residential"
    else:
        kind="Market News"
    return kind

def parse(xml,now=None):
    now=now or datetime.now(timezone.utc)
    try: root=ET.fromstring(xml)
    except ET.ParseError: return []
    out=[]
    for node in root.findall(".//item"):
        src=node.find("source")
        if src is None:continue
        publisher=cleanup("".join(src.itertext()))
        hostname=(urlparse(src.attrib.get("url","")).hostname or "").lower().removeprefix("www.")
        if not publisher or not hostname or "." not in hostname:continue
        title=cleanup(first_text(node,["title"]))
        if title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if not 15 <= len(title) <= 280:continue
        kind=classify(title)
        if not kind:continue
        link=cleanup(first_text(node,["link"]))
        u=urlparse(link)
        if u.scheme!="https" or (u.hostname or "").lower()!="news.google.com":continue
        when=feed_date(first_text(node,["pubDate"]))
        if not when or when<now-timedelta(days=7) or when>now+timedelta(hours=2):continue
        out.append({
          "id":link,"url":link,"title":title,
          "source":publisher+" • Google News","domain":hostname,
          "region":"hyderabad","sector":"Real Estate","desk":"regional-business",
          "real_estate_kind":kind,"regional_business":True,
          "seen":when.isoformat(),"time_basis":"google_rss",
          "language":"Telugu/English","sourcecountry":"India",
          "origin":"google-news-rss","link_type":"google-news-redirect"
        })
    return out

def collect_hyderabad_real_estate(cycle=None):
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    terms=list(CORE)
    terms.extend(ROTATE[(cycle*3+i)%len(ROTATE)] for i in range(3))
    # One publication-scoped research check per run, including those that do
    # not supply RSS; Google News indexing may be sparse or absent.
    for i in (cycle%len(CONSULTANT_DOMAINS),(cycle+3)%len(CONSULTANT_DOMAINS)):
        terms.append('site:'+CONSULTANT_DOMAINS[i]+' (Hyderabad OR Cyberabad) (office OR residential OR property OR real estate) when:7d')
    status={"queries":len(terms),"successful_feeds":0,"accepted":0,
            "by_kind":{},"by_source":{},"warnings":[]}
    by_url={}
    def fetch(query):
        url=BASE+"?"+urlencode({"q":query,"hl":"en-IN","gl":"IN","ceid":"IN:en"})
        try:
            req=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; source-linked property headlines)",
                "Accept":"application/rss+xml,application/xml,text/xml;q=0.9"
            })
            with urlopen(req,timeout=12) as response: xml=response.read(1_800_000)
            return parse(xml),None
        except Exception as exc:
            return [],type(exc).__name__+": "+str(exc)[:110]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for items,error in pool.map(fetch,terms):
            if error:
                status["warnings"].append(error)
                continue
            status["successful_feeds"]+=1
            for item in items:by_url[item["url"]]=item
    for item in by_url.values():
        kind=item["real_estate_kind"];status["by_kind"][kind]=status["by_kind"].get(kind,0)+1
        source=item["domain"];status["by_source"][source]=status["by_source"].get(source,0)+1
    status["accepted"]=len(by_url)
    return list(by_url.values()),status

if __name__=="__main__":
    rows,status=collect_hyderabad_real_estate()
    print("Hyderabad property headlines",len(rows),status)
