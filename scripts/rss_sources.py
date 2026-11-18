#!/usr/bin/env python3
"""Free official RSS, source links only; no publisher article body copies."""
import html, re, sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

FEEDS=[
 ("NSE", "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml", "exchange"),
 ("NSE", "https://nsearchives.nseindia.com/content/RSS/Financial_Results.xml", "exchange"),
 ("NSE", "https://nsearchives.nseindia.com/content/RSS/Board_Meetings.xml", "exchange"),
 ("NSE", "https://nsearchives.nseindia.com/content/RSS/Corporate_action.xml", "exchange"),
 ("BSE", "https://beta.bseindia.com/data/xml/announcements.xml", "exchange"),
 ("BSE", "https://beta.bseindia.com/Data/XML/BoardMeetingsFeed.xml", "exchange"),
 ("RBI", "https://www.rbi.org.in/pressreleases_rss.xml", "policy"),
 ("PIB", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1", "policy"),
]
# Curated coverage groups for editorial monitoring, not a definitive census of listed companies.
# Company aliases are matched in BOTH exchange titles and descriptions.
TRACKED=[
 ("hyderabad",["Dr Reddy","DRREDDY","Aurobindo Pharma","AUROPHARMA","Divi's Laboratories","DIVISLAB","Granules India","GRANULES","Gland Pharma","GLAND","Natco Pharma","NATCOPHARM","Laurus Labs","LAURUSLABS","Neuland Laboratories","NEULANDLAB","Suven Pharmaceuticals","SUVENPHAR","Cyient","CYIENT","CCL Products","CCL","Zen Technologies","ZENTEC","Apollo Micro Systems","APOLLOMICRO","MTAR Technologies","MTARTECH","Bharat Dynamics","BDL","KIMS Hospitals","Krishna Institute of Medical Sciences","KIMS","Rainbow Childrens","RAINBOW","Medplus Health","MEDPLUS","Vijaya Diagnostic","VIJAYA","Nava Limited","NAVA","Heritage Foods","HERITGFOOD","Zaggle","ZAGGLE","KNR Constructions","KNRCON","Pennar Industries","PENIND","Tanla Platforms","TANLA","VST Industries","VSTIND","Pokarna","POKARNA","NCC Limited","NCC","Sai Silks","SAIL","VST Industries"] ),
 ("andhra-pradesh",["Amara Raja","AMARAJABAT","ARE&M","Andhra Paper","ANDHRAPAP","Andhra Sugars","ANDHRSUGAR","Avanti Feeds","AVANTIFEED"]),
]
# Disallow short unqualified aliases matching ordinary English words.
SHORT_ALIASES={"ccl","kims","bdl","ncc","sail","nava","gland"}
BUSINESS=re.compile(r"\b(business|financial|economic|bank|industry|market|share|finance|rbi|sebi|investment|export|import|manufactur|port|aviation|airport|pharma|software|technology|power|energy|startup|policy|commerce|trade|tax|gst|monetary|infrastructure|corporate|results|company|ipo|employment|development|semiconductor|gdp|insurance|loan|logistic|industrial)\w*\b",re.I)
LINK_OK=("nseindia.com","bseindia.com","rbi.org.in","pib.gov.in")

def cleanup(value):
    value=re.sub("<[^>]+>"," ",value or "")
    return re.sub(r"\s+"," ",html.unescape(value)).strip()

def first_text(node, names):
    for name in names:
        elem=node.find(name)
        if elem is not None:
            content="".join(elem.itertext()).strip()
            if content: return content
    return ""

def company_for(subject):
    clean=cleanup(subject)
    lower=clean.lower()
    for region,aliases in TRACKED:
        for alias in aliases:
            key=alias.lower()
            if key in SHORT_ALIASES: # require company identifier or exact symbol framing
                if not re.search(r"(?<!\w)"+re.escape(alias)+r"(?:\s+limited|\s+ltd|\s+hospitals|\s+pharma|\s+industries|\s+technologies|\s*\(|\s*-|\b)",clean,re.I):
                    continue
            elif not re.search(r"(?<!\w)"+re.escape(alias)+r"(?!\w)",lower,re.I):
                continue
            return region,alias
    return None,None

def feed_date(raw):
    if not raw:return None
    try:
        d=parsedate_to_datetime(raw)
        return d.replace(tzinfo=timezone.utc) if not d.tzinfo else d.astimezone(timezone.utc)
    except Exception:
        try:return datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(timezone.utc)
        except Exception:return None

def fetch_one(source,url,kind):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; public official RSS headline index)","Accept":"application/rss+xml, application/xml, text/xml;q=0.9,*/*;q=0.1"})
    with urlopen(req,timeout=18) as response:
        xml=response.read(2_500_000)
    root=ET.fromstring(xml)
    items=root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    now=datetime.now(timezone.utc)
    entries=[]
    for node in items:
        title=cleanup(first_text(node,["title","{http://www.w3.org/2005/Atom}title"]))
        desc=cleanup(first_text(node,["description","{http://purl.org/rss/1.0/modules/content/}encoded","{http://www.w3.org/2005/Atom}summary"]))
        link=first_text(node,["link","guid"])
        if not link:
            elem=node.find("{http://www.w3.org/2005/Atom}link")
            if elem is not None:link=elem.attrib.get("href","")
        if not link.startswith(("https://","http://")):continue
        domain=(urlparse(link).hostname or "").lower()
        if not any(domain==x or domain.endswith("."+x) for x in LINK_OK):continue
        d=feed_date(first_text(node,["pubDate","{http://purl.org/dc/elements/1.1/}date","{http://www.w3.org/2005/Atom}updated"]))
        if d and (d<now-timedelta(days=7) or d>now+timedelta(hours=2)):continue
        when=d.isoformat() if d else now.isoformat()
        if kind=="exchange":
            region,match=company_for(title+" "+desc)
            if not region:continue
            short=desc[:135] if desc else ""
            headline=(title+" — "+short if short and short.lower()!=title.lower() and short.lower() not in title.lower() else title)[:220]
            sector="Corporate & Results"
        else:
            if not BUSINESS.search(title):continue
            region="india"
            if re.search(r"\bhyderabad\b",title,re.I):region="hyderabad"
            elif re.search(r"\bandhra pradesh\b|visakhapatnam|amaravati|tirupati",title,re.I):region="andhra-pradesh"
            elif re.search(r"\btelangana\b",title,re.I):region="telangana"
            headline=title[:220]
            sector="Banking & Finance" if source=="RBI" else "Economy & Policy"
        if len(headline)<8:continue
        entries.append({"id":link,"url":link,"title":headline,"source":source+" • Official","domain":domain,"region":region,"sector":sector,"seen":when,"sourcecountry":"India","language":"English","origin":"official-rss"})
    return entries

def collect_official():
    found=[]
    for source,url,kind in FEEDS:
        try:
            rows=fetch_one(source,url,kind)
            print("Official feed",source,url,"regional/business matches",len(rows),flush=True)
            found.extend(rows)
        except Exception as exc:
            print("Official feed warning",source,str(exc),file=sys.stderr,flush=True)
    return found
