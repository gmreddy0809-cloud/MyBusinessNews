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
 ("RBI", "https://rbi.org.in/notifications_rss.xml", "policy"),
 ("RBI", "https://www.rbi.org.in/speeches_rss.xml", "policy"),
 ("RBI", "https://www.rbi.org.in/Publication_rss.xml", "policy"),
 ("SEBI", "https://www.sebi.gov.in/sebirss.xml", "policy"),
 ("PIB", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1", "policy"),
]
# Curated coverage groups for editorial monitoring, not a definitive census of listed companies.
# Company aliases are matched in BOTH exchange titles and descriptions.
TRACKED=[
 ("hyderabad",["Dr Reddy","DRREDDY","Aurobindo Pharma","AUROPHARMA","Divi's Laboratories","DIVISLAB","Granules India","GRANULES","Gland Pharma","GLAND","Natco Pharma","NATCOPHARM","Laurus Labs","LAURUSLABS","Neuland Laboratories","NEULANDLAB","Suven Pharmaceuticals","SUVENPHAR","Cyient","CYIENT","CCL Products","CCL","Zen Technologies","ZENTEC","Apollo Micro Systems","APOLLOMICRO","MTAR Technologies","MTARTECH","Bharat Dynamics","BDL","KIMS Hospitals","Krishna Institute of Medical Sciences","KIMS","Rainbow Childrens","RAINBOW","Medplus Health","MEDPLUS","Vijaya Diagnostic","VIJAYA","Nava Limited","NAVA","Heritage Foods","HERITGFOOD","Zaggle","ZAGGLE","KNR Constructions","KNRCON","Pennar Industries","PENIND","Tanla Platforms","TANLA","VST Industries","VSTIND","Pokarna","POKARNA","NCC Limited","NCC","Sai Silks","SAIL","Astra Microwave","ASTRAMICRO","Dodla Dairy","DODLA","Azad Engineering","Vimta Labs","VIMTALABS","Kaveri Seed","KSCL","NMDC","Mishra Dhatu Nigam","MIDHANI"] ),
 ("andhra-pradesh",["Amara Raja","AMARAJABAT","ARE&M","Andhra Paper","ANDHRAPAP","Andhra Sugars","ANDHRSUGAR","Avanti Feeds","AVANTIFEED","Apex Frozen Foods","Coastal Corporation"]),
]
# Extended Hyderabad / AP businesses: local headquarters, sites and clusters.
# A national firm's unrelated national story is not regional by default.
TRACKED.extend([
 ("hyderabad",[
  "Hetero Labs","Hetero Drugs","Hetero Group","Bharat Biotech",
  "Biological E","Indian Immunologicals","MSN Laboratories",
  "Sai Life Sciences","Aragen Life Sciences","Shilpa Medicare",
  "Skyroot Aerospace","Dhruva Space","Ananth Technologies",
  "VEM Technologies","Raghu Vamsi","GMR Aero Technic",
  "GHIAL","Hyderabad International Airport",
  "Yashoda Hospitals","AIG Hospitals","Continental Hospitals",
  "CARE Hospitals","Innominds","ValueLabs",
  "Cigniti Technologies","Darwinbox","Keka Technologies",
  "CtrlS Datacenters","T-Hub","WE Hub","T-Works",
  "Ramky Group","My Home Group","Aparna Constructions",
  "Rajapushpa Properties","Aurore Life Sciences","Cohance Lifesciences"
 ]),
 ("andhra-pradesh",[
  "Sri City","Sri City Industrial","Andhra Pradesh Medtech Zone",
  "Andhra Pradesh Industrial Infrastructure Corporation",
  "APIIC","AMTZ","Brandix India Apparel City",
  "Gangavaram Port","Visakhapatnam Port Authority",
  "Kakinada Gateway Port","Krishnapatnam Port",
  "Bharathi Cement","Sangam Dairy","Amara Raja Group"
 ])
])

# Disallow short unqualified aliases matching ordinary English words.
SHORT_ALIASES={"ccl","kims","bdl","ncc","sail","nava","gland"}
BUSINESS=re.compile(r"\b(business|financial|economic|bank|industry|market|share|finance|rbi|sebi|investment|export|import|manufactur|port|aviation|airport|pharma|software|technology|power|energy|startup|policy|commerce|trade|tax|gst|monetary|infrastructure|corporate|results|company|ipo|employment|development|semiconductor|gdp|insurance|loan|logistic|industrial|capital|securities|investor|mutual|deposit|interest|bond|pension|circular|credit|fraud|payment|consumer)\w*\b",re.I)
LINK_OK=("nseindia.com","bseindia.com","rbi.org.in","pib.gov.in","sebi.gov.in")

PF_WORDS=re.compile(r'fixed deposits?|bank deposits?|interest rate|sovereign gold bond|\bsgb\b|gold bonds?|domestic money transfer|mutual fund|investor|investing|pension|retirement|\bppf\b|\bepf\b|\bnps\b|insurance|credit card|personal loan|home loan|gold loan|recurring deposit|savings account|tax savings?|credit score|digital payment|upi|\bkyc\b|financial literacy|consumer protection|ombudsman|bank customer|borrower|unclaimed deposit|nomination|fraud|cybersecurity',re.I)
LOCAL_WORDS=[
 ("hyderabad",re.compile(r'\bhyderabad|secunderabad|shamshabad|gachibowli|medchal\b',re.I)),
 ("andhra-pradesh",re.compile(r'andhra pradesh|visakhapatnam|vizag|amaravati|vijayawada|tirupati|guntur|kakinada|sri city|nellore|ananthapur|eluru|srikakulam',re.I)),
 ("telangana",re.compile(r'\btelangana\b|warangal|karimnagar|sangareddy|khammam|nizamabad|mahbubnagar|medak|siddipet|adilabad',re.I))
]
def explicit_locality(subject):
 for name,p in LOCAL_WORDS:
    if p.search(subject):return name
 return None

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
    try:
        root=ET.fromstring(xml)
        items=root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    except ET.ParseError as error:
        # A busy BSE RSS endpoint may return a truncated XML response.
        # Recover complete item elements only; never invent missing rows.
        print("RSS partial XML, recovering complete items",source,str(error),file=sys.stderr,flush=True)
        items=[]
        wrapper=b'<root xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">'
        for raw in re.findall(rb"<item(?:\s[^>]*)?>[\s\S]*?</item>",xml,re.I):
            try:
                node=ET.fromstring(wrapper+raw+b"</root>")[0]
                items.append(node)
            except ET.ParseError:
                continue
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
            if not region:region=explicit_locality(title+" "+desc)
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
            sector="Personal Finance" if PF_WORDS.search(title) else ("Markets & IPOs" if source=="SEBI" else ("Banking & Finance" if source=="RBI" else "Economy & Policy"))
        if len(headline)<8:continue
        entries.append({"id":link,"url":link,"title":headline,"source":source+" • Official","domain":domain,"region":region,"sector":sector,"seen":when,"time_basis":"feed" if d else "first_seen","sourcecountry":"India","language":"English","origin":"official-rss","summary":desc[:380] if desc and desc.casefold()!=headline.casefold() else ""})
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
