#!/usr/bin/env python3
"""Hyderabad regional business headline discovery: Google News RSS, not syndication.

Index credited headline, publisher and Google News click-through only.
'Hyderabad' includes verified company-name associations even when no city word
is in the headline; unrelated national coverage is not automatically local.
"""
import re
import sys
from datetime import datetime,timezone,timedelta
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup,first_text,feed_date,company_for
from desk_coverage import local_business_match,CORPORATE_EN,CORPORATE_TE

BASE="https://news.google.com/rss/search"
# All high-priority search themes run each cycle; extend coverage beyond exchanges.
QUERIES=(
  'Hyderabad (GCC OR "global capability centre" OR "global capability center" OR "India office")',
  'Hyderabad (startup OR funding OR investment OR venture capital OR acquisition)',
  'Hyderabad (pharma OR biotech OR vaccine OR biologics OR healthcare)',
  'Hyderabad (software OR IT OR AI OR technology OR semiconductor OR data center)',
  'Hyderabad (manufacturing OR factory OR industrial park OR aerospace OR airport)',
  'Hyderabad (real estate OR logistics OR retail OR hotel OR hospital)',
  '(Telangana OR Hyderabad) (business expansion OR investment OR jobs OR plant)',
  '("Biological E" OR "BE BioSol" OR "B E Biosol" OR "Bharat Biotech" OR Hetero) (agreement OR partnership OR launch OR investment OR Gates)',
  '("Dr Reddy" OR Aurobindo OR Cyient OR Laurus OR Granules OR Divis OR KIMS) (results OR acquisition OR partnership OR expansion)',
  '("Skyroot" OR "Dhruva Space" OR "Darwinbox" OR "Keka" OR "T-Hub" OR "CtrlS") (funding OR expansion OR partnership)',
  '("Telangana" OR "Hyderabad") (గ్లోబల్ OR జీసీసీ OR పెట్టుబడి OR కంపెనీ OR పరిశ్రమ OR స్టార్టప్)',
  '("హైదరాబాద్" OR "తెలంగాణ") (ఫార్మా OR ఒప్పందం OR విస్తరణ OR నిధులు OR వ్యాపారం)',
)
BUSINESS=re.compile(
 r'\b(?:business|company|companies|corporate|startup|funding|investment|invests?|'
 r'contract|agreement|partnership|collaborat|acquisition|merger|expansion|expand|'
 r'profit|revenue|results?|earnings|pharma|biotech|vaccine|manufactur|factory|'
 r'industr|\bgcc\b|global capability|office|software|technology|\bIT\b|'
 r'healthcare|hospital|airport|aviation|aerospace|defence|real estate|'
 r'data cent|jobs?|hiring|logistic|retail|product launch|facility|plant|'
 r'capital|supply chain|infrastructure|energy|renewable|order|market)\b|'
 r'పెట్టుబడ|ఒప్పంద|భాగస్వామ|ఫార్మా|వ్యాపార|కంపెనీ|సంస్థ|నిధులు|విస్తరణ|'
 r'పరిశ్రమ|జీసీసీ|స్టార్టప్|ఉద్యోగాలు|కర్మాగార|ఆర్థిక ఫలితాలు|లాభాలు|'
 r'టెక్నాలజీ|టెక్నాలజి|బయోసోల్|బయోలాజికల్',re.I)
TOPICS=(
 ("GCCs",r'\bgcc\b|global capability|global in.house|capability centre|capability center'),
 ("Startups",r'startup|start.up|venture capital|seed funding|series [a-f]|స్టార్టప్'),
 ("Pharma & Life Sciences",r'pharma|biotech|vaccine|biolog|biosol|biological e|drug|ఫార్మా|బయోసోల్'),
 ("Healthcare & Hospitals",r'hospital|healthcare|diagnostic|ఆసుపత్రి'),
 ("IT & AI",r'software|technology|semiconductor|artificial intelligence|data cent|\bIT\b|\bAI\b|ఐటీ'),
 ("Aviation & Airports",r'airport|airline|aerospace|aviation|space tech|satellite|rocket'),
 ("Real Estate",r'real estate|property|housing|commercial space'),
 ("Funding & Investments",r'investment|funding|raises? (?:rs|\\$)|పెట్టుబడి|నిధులు'),
 ("Corporate & Results",r'quarter|profit|revenue|result|earnings|లాభాలు|ఫలితాలు'),
)
def sector(title):
    for label,pattern in TOPICS:
        if re.search(pattern,title,re.I):return label
    return "Other Business"

def parse(xml,now=None):
    now=now or datetime.now(timezone.utc)
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    found=[]
    for node in root.findall(".//item")[:100]:
        source=node.find("source")
        if source is None:continue
        publisher=cleanup("".join(source.itertext()))
        origin=source.attrib.get("url","")
        host=(urlparse(origin).hostname or "").lower().removeprefix("www.")
        if not publisher or not host or "." not in host:continue
        title=cleanup(first_text(node,["title"]))
        if title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if not 15<=len(title)<=280:continue
        place=local_business_match(title)
        if not place or place not in ("hyderabad","telangana","andhra-pradesh"):continue
        if not (BUSINESS.search(title) or company_for(title)[0]):continue
        link=cleanup(first_text(node,["link"]))
        u=urlparse(link)
        if u.scheme!="https" or (u.hostname or "").lower()!="news.google.com":continue
        dt=feed_date(first_text(node,["pubDate"]))
        if not dt or dt>now+timedelta(hours=2) or dt<now-timedelta(days=7):continue
        found.append({
            "id":link,"url":link,"title":title,
            "source":publisher+" • Google News","domain":host,
            "region":place,"sector":sector(title),"desk":"regional-business",
            "seen":dt.isoformat(),"time_basis":"google_rss",
            "language":"Telugu/English","sourcecountry":"India",
            "origin":"google-news-rss","link_type":"google-news-redirect",
            "regional_business":True
        })
    return found

def collect_hyderabad_business(cycle=None):
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    # Six searches every half hour; all twelve search themes rotate hourly.
    selected=[QUERIES[(cycle*6+i)%len(QUERIES)] for i in range(6)]
    status={"queries":len(selected),"successful_feeds":0,"accepted":0,"by_source":{},"warnings":[]}
    out={}
    from concurrent.futures import ThreadPoolExecutor
    def fetch_topic(term):
        url=BASE+"?"+urlencode({"q":"("+term+") when:7d","hl":"en-IN","gl":"IN","ceid":"IN:en"})
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; attributed local business headline discovery)","Accept":"application/rss+xml,application/xml,text/xml;q=0.9"})
            with urlopen(req,timeout=12) as resp:xml=resp.read(1_600_000)
            return parse(xml),None
        except Exception as exc:
            return [],type(exc).__name__+": "+str(exc)[:90]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for items,error in pool.map(fetch_topic,selected):
            if error:
                status["warnings"].append(error)
                print("Hyderabad business RSS discovery unavailable",error,file=sys.stderr)
                continue
            status["successful_feeds"]+=1
            for item in items:
                out[item["url"]]=item
                status["by_source"][item["source"]]=status["by_source"].get(item["source"],0)+1
    status["accepted"]=len(out)
    return list(out.values()),status
