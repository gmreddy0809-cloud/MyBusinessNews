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
from rss_sources import cleanup,first_text,feed_date,company_for,TRACKED
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
# Local listed-company coverage from editorial reporting, not only exchange notices.
LISTED_NEWS_QUERIES=(
 '("Dr Reddy" OR "Aurobindo Pharma" OR "Divis Laboratories" OR "Laurus Labs") (partnership OR investment OR result OR approval OR expansion)',
 '("Cyient" OR "Zen Technologies" OR "Astra Microwave" OR "MTAR Technologies") (deal OR contract OR investment OR revenue OR order)',
 '("Granules India" OR "Natco Pharma" OR "Neuland Laboratories" OR "Suven Pharma") (business OR approval OR profit OR deal)',
 '("KIMS Hospitals" OR "Medplus" OR "Vijaya Diagnostic" OR "Rainbow Children") (business OR expansion OR results)',
 '("Amara Raja" OR "Avanti Feeds" OR "Andhra Paper" OR "Apex Frozen") (investment OR result OR expansion)',
 '("Bharat Dynamics" OR "NMDC" OR "NCC Limited" OR "KNR Constructions") (contract OR earnings OR expansion)',
)
LISTED_ALIASES={name.lower() for _,names in TRACKED[:2] for name in names}
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
# Strong business-only signals for extracting Hyderabad / Telangana corporate
# stories from broader regional feeds. Politics at an office, school reports,
# traffic or airport incidents must not be promoted into a business desk.
REGIONAL_CORPORATE_SIGNAL=re.compile(
 r'\b(?:\bgcc\b|global capability|fund(?:ed|ing)|start[ -]?ups?|'
 r'invest(?:ment|s|ed|ing)?|acqui(?:res?|red|sition)|merger|'
 r'quarterly|earnings|revenues?|profits?|ipo|shareholders?|'
 r'pharma|biotech|usfda|us fda|fda observation|'
 r'manufactur(?:ing|er)|factories|factory|industrial park|'
 r'expands?|expansion|new plant|plant capacity|'
 r'contract(?:s)?|order win|deal worth|software (?:company|firm|services)|'
 r'data cent(?:re|er)|office leas(?:e|ing)|real estate|'
 r'commercial (?:space|property)|new facility|'
 r'global tech cent(?:re|er))\b|'
 r'పెట్టుబడ|ఒప్పంద|విస్తరణ|ఫార్మా|పరిశ్రమ|కంపెనీ|జీసీసీ|స్టార్టప్|'
 r'ఆర్థిక ఫలితాలు|లాభాలు|నిధులు',re.I
)

def eligible_regional_business(row):
    """Only promote strongly commercial, explicitly regional general news."""
    if not isinstance(row,dict) or row.get("desk")!="regional-general":return False
    if row.get("region") not in ("hyderabad","telangana","andhra-pradesh","ap-tg"):return False
    title=str(row.get("title") or "")
    if re.search(r"\b(?:protest|vandal|rainstorm|flood|cyclone|traffic|robbery|homicide|murder|arrest|detained|bomb threat|accident|road crash|police action)\b",title,re.I):return False
    if not REGIONAL_CORPORATE_SIGNAL.search(title):return False
    return bool(local_business_match(title,row.get("region")))

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
        matched_region,matched_company=company_for(title)
        is_listed=bool(matched_region and matched_company and matched_company.lower() in LISTED_ALIASES)
        found.append({
            "listed_company":is_listed,
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
    selected.extend(LISTED_NEWS_QUERIES[(cycle*2+i)%len(LISTED_NEWS_QUERIES)] for i in range(2))
    status={"queries":len(selected),"successful_feeds":0,"accepted":0,"by_source":{},"warnings":[]}
    out={}
    from concurrent.futures import ThreadPoolExecutor
    def fetch_topic(term):
        url=BASE+"?"+urlencode({"q":term+" when:7d","hl":"en-IN","gl":"IN","ceid":"IN:en"})
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
