#!/usr/bin/env python3
"""AP/TG regional headline discovery through Google News RSS, not syndication.

Only dated titles, credited publisher names and Google News click-through links.
No publisher story bodies, snippets, images or inferred original publication times.
"""
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from rss_sources import cleanup, first_text, feed_date

RSS_URL="https://news.google.com/rss/search"
SOURCES=(
    ("Eenadu","eenadu.net"),
    ("Sakshi","sakshi.com"),
    ("Andhra Jyothy","andhrajyothy.com"),
    ("ETV Bharat Telugu","etvbharat.com"),
    ("TV9 Telugu","tv9telugu.com"),
    ("NTV Telugu","ntvtelugu.com"),
    ("ABP Desam","telugu.abplive.com"),
    ("V6 Velugu","v6velugu.com"),
    ("Telangana Today","telanganatoday.com"),
    ("10TV Telugu","10tv.in"),
    ("Namasthe Telangana","ntnews.com"),
    ("Samayam Telugu","telugu.samayam.com"),
    ("News18 Telugu","telugu.news18.com"),
    ("The Hans India","thehansindia.com"),
    ("TV5 Telugu","tv5news.in"),
    ("HMTV","hmtvlive.com"),
    ("Andhra Prabha","prabhanews.com"),
    ("Prajasakti","prajasakti.com"),
    ("Nava Telangana","navatelangana.com"),
    ("Mana Telangana","manatelangana.news"),
    ("Disha Daily","dishadaily.com"),
    ("Greatandhra","greatandhra.com"),
    ("AP7AM","ap7am.com"),
    ("Telugu360","telugu360.com"),
    ("BBC Telugu","bbc.com"),
    ("Oneindia Telugu","telugu.oneindia.com"),
    ("The Hindu","thehindu.com"),
    ("Deccan Chronicle","deccanchronicle.com"),
    ("New Indian Express","newindianexpress.com"),
    ("Times of India","timesofindia.indiatimes.com"),
    ("The Hindu BusinessLine","thehindubusinessline.com"),
    ("Economic Times","economictimes.indiatimes.com"),
    ("Business Standard","business-standard.com"),
    ("Financial Express","financialexpress.com"),
    ("Moneycontrol","moneycontrol.com"),
    ("Siasat","siasat.com"),
    ("The News Minute","thenewsminute.com"),
    ("India Today","indiatoday.in"),
    ("Hindustan Times","hindustantimes.com"),
    ("NDTV","ndtv.com"),
    ("ABP Live","abplive.com"),
    ("Zee News Telugu","zeenews.india.com"),
    ("The Print","theprint.in"),
    ("Outlook India","outlookindia.com"),
    ("Telugu Post","telugupost.com"),
    ("Telugu One","teluguone.com"),
    ("Telugu Global","teluguglobal.com"),
    ("Asianet News Telugu","telugu.asianetnews.com"),
    ("Telugu Prabha","teluguprabha.net"),
    ("Etemaad","etemaaddaily.com"),
)

REGIONS=(
    '(Andhra Pradesh OR Amaravati OR Vijayawada OR Visakhapatnam OR Tirupati OR "ఆంధ్రప్రదేశ్" OR "అమరావతి" OR "విజయవాడ" OR "విశాఖ")',
    '(Telangana OR Hyderabad OR Warangal OR "తెలంగాణ" OR "హైదరాబాద్" OR "వరంగల్")'
)
# Only explicit place names or clearly regional political references assign a state.
AP=re.compile(
 r'ఆంధ్రప్రదేశ్|ఆంధ్ర ప్రదేశ్|ఏపీ|అమరావతి|విశాఖ|విజయవాడ|తిరుపతి|గుంటూరు|కాకినాడ|నెల్లూరు|కర్నూలు|'
 r'చంద్రబాబు|పవన్ కల్యాణ్|పవన్ కళ్యాణ్|జగన్|లోకేశ్|శ్రీకాకుళం|విజయనగరం|అనకాపల్లి|'
 r'రాజమండ్రి|రాజమహేంద్రవరం|ఏలూరు|భీమవరం|ఒంగోలు|నంద్యాల|అనంతపురం|కడప|చిత్తూరు|'
 r'andhra pradesh|amaravati|visakhapatnam|vizag|vijayawada|tirupati|guntur|kakinada|'
 r'nellore|kurnool|chandrababu|pawan kalyan|ys jagan|nara lokesh|'
 r'srikakulam|vizianagaram|anakapalli|rajahmundry|eluru|ongole|nandyal|'
 r'anantapur|kadapa|chittoor|east godavari|west godavari',re.I)
TG=re.compile(
 r'తెలంగాణ|హైదరాబాద్|సికింద్రాబాద్|వరంగల్|కరీంనగర్|ఖమ్మం|నిజామాబాద్|'
 r'రేవంత్|కేసీఆర్|కేటీఆర్|సంగారెడ్డి|మెదక్|సిద్దిపేట|నల్గొండ|నల్గొండ|'
 r'సూర్యాపేట|మహబూబ్‌నగర్|నిర్మల్|ఆదిలాబాద్|జగిత్యాల|పెద్దపల్లి|భూపాలపల్లి|'
 r'రంగారెడ్డి|మేడ్చల్|జనగామ|వికారాబాద్|మంచిర్యాల|'
 r'telangana|hyderabad|secunderabad|warangal|karimnagar|khammam|nizamabad|'
 r'revanth reddy|\bkcr\b|\bktr\b|sangareddy|medak|siddipet|nalgonda|'
 r'suryapet|mahabubnagar|adilabad|jagtial|peddapalli|rangareddy|medchal|vikarabad',re.I)
# Additional named districts/towns expand geographic recognition, not topic filtering.
AP_MORE=re.compile(r'పల్నాడు|బాపట్ల|కోనసీమ|పార్వతీపురం|అల్లూరి|ప్రకాశం|పుట్టపర్తి|హిందూపురం|మాచర్ల|తెనాలి|పిడుగురాళ్ల|వేటపాలెం|భీమవరం|గుడివాడ|పెనుకొండ|ప్రొద్దుటూరు|ధర్మవరం|నర్సీపట్నం|మచిలీపట్నం|శ్రీకాళహస్తి|palnadu|bapatla|konaseema|parvathipuram|prakasam|puttaparthi|hindupur|tenali|bhimavaram|gudivada|machilipatnam|narsipatnam|proddatur|dharmavaram',re.I)
TG_MORE=re.compile(r'ములుగు|మహబూబాబాద్|కామారెడ్డి|యాదాద్రి|భద్రాద్రి|కొత్తగూడెం|నాగర్‌కర్నూల్|వనపర్తి|గద్వాల|ఆసిఫాబాద్|శంషాబాద్|గచ్చిబౌలి|హనుమకొండ|సిరిసిల్ల|జహీరాబాద్|mulugu|mahabubabad|kamareddy|yadadri|bhadradri|kothagudem|nagarkurnool|wanaparthy|gadwal|asifabad|shamshabad|gachibowli|hanamkonda|sircilla|zaheerabad',re.I)
GEO_NOISE=re.compile(r"(?!)")  # Weather, traffic and routine updates are news too.

def region(title):
    ap=bool(AP.search(title) or AP_MORE.search(title)); tg=bool(TG.search(title) or TG_MORE.search(title))
    if ap and tg:return "ap-tg"  # A genuine two-state headline belongs to all three general-news tabs.
    if ap:return "andhra-pradesh"
    if tg:return "hyderabad" if re.search(r'హైదరాబాద్|సికింద్రాబాద్|hyderabad|secunderabad',title,re.I) else "telangana"
    return None

def valid_link(link):
    p=urlparse(link)
    return p.scheme=="https" and (p.hostname or "").lower()=="news.google.com"

def parse(xml,expected_domain,now=None):
    now=now or datetime.now(timezone.utc)
    try: root=ET.fromstring(xml)
    except ET.ParseError:return []
    out=[]
    for node in root.findall(".//item"):
        source=node.find("source")
        if source is None:continue
        publisher=cleanup("".join(source.itertext()))
        src=source.attrib.get("url","")
        hostname=(urlparse(src).hostname or "").lower().removeprefix("www.")
        if not hostname or "." not in hostname:continue
        if expected_domain and hostname!=expected_domain and not hostname.endswith("."+expected_domain):continue
        title=cleanup(first_text(node,["title"]))
        if publisher and title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if len(title)<10:continue
        place=region(title)
        if not place:continue
        link=cleanup(first_text(node,["link"]))
        if not valid_link(link):continue
        published=feed_date(first_text(node,["pubDate"]))
        if not published or published>now+timedelta(hours=2) or published<now-timedelta(days=7):continue
        out.append({
            "id":link,"url":link,"title":title[:280],
            "source":publisher+" • Google News","domain":hostname,
            "region":place,"sector":"Regional General News",
            "seen":published.isoformat(),"time_basis":"google_rss",
            "origin":"google-news-rss","desk":"regional-general",
            "language":"Telugu/English","sourcecountry":"India",
            "link_type":"google-news-redirect"
        })
    return out

def collect_telanganatoday_rss(now=None):
    """Poll publisher's public RSS for attributed headlines and direct links only."""
    now=now or datetime.now(timezone.utc)
    endpoint="https://telanganatoday.com/feed"
    req=Request(endpoint,headers={
        "User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; headline link reader)",
        "Accept":"application/rss+xml,application/xml,text/xml;q=0.9"
    })
    with urlopen(req,timeout=15) as response:
        xml=response.read(1_600_000)
    root=ET.fromstring(xml)
    found={}
    for node in root.findall(".//item"):
        title=cleanup(first_text(node,["title"]))
        link=cleanup(first_text(node,["link"]))
        hostname=(urlparse(link).hostname or "").lower().removeprefix("www.")
        if hostname!="telanganatoday.com" or not link.startswith("https://"):continue
        if not 15<=len(title)<=280:continue
        published=feed_date(first_text(node,["pubDate"]))
        if not published or published>now+timedelta(hours=2) or published<now-timedelta(days=7):continue
        place=region(title)
        # Headlines need explicit AP/TG evidence, or a clear publisher section path.
        path=urlparse(link).path.lower()
        if not place and re.search(r"/(?:hyderabad|telangana)/",path):place="hyderabad" if "/hyderabad/" in path else "telangana"
        if not place and re.search(r"/(?:andhra-pradesh|andhra)/",path):place="andhra-pradesh"
        if not place:continue
        found[link]={
            "id":link,"url":link,"title":title,"source":"Telangana Today • RSS",
            "domain":"telanganatoday.com","region":place,
            "sector":"Regional General News","desk":"regional-general",
            "seen":published.isoformat(),"time_basis":"feed","origin":"publisher-rss",
            "language":"English","sourcecountry":"India"
        }
    return list(found.values())

def collect_regional(cycle=None):
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    # Poll six priority outlets every run, plus 16 rotating publisher checks.
    # Each query covers BOTH states; classify strictly from headline evidence.
    priority=[p for p in SOURCES if p[1] in {'eenadu.net','sakshi.com','andhrajyothy.com','etvbharat.com','tv9telugu.com','v6velugu.com','telanganatoday.com','ntnews.com','navatelangana.com','manatelangana.news','dishadaily.com','siasat.com'}]
    others=[p for p in SOURCES if p not in priority]
    rotating=[others[(cycle*16+i)%len(others)] for i in range(min(16,len(others)))]
    chosen=list(dict.fromkeys(list(priority)+rotating))
    status={"sources_configured":len(SOURCES),"queries":len(chosen)+len(priority),"successful_feeds":0,"accepted":0,"by_source":{},"warnings":[]}
    found={}
    # Dedicated Telangana Today RSS every run; Google News remains a backup.
    try:
        direct=collect_telanganatoday_rss()
        status["successful_feeds"]+=1
        status["by_source"]["Telangana Today RSS"]=len(direct)
        for item in direct:found[item["url"]]=item
    except Exception as exc:
        status["warnings"].append("Telangana Today RSS: "+type(exc).__name__+": "+str(exc)[:80])
        print("Telangana Today RSS unavailable",type(exc).__name__,str(exc)[:80],file=sys.stderr)
    # Fetch independent publishers concurrently; do not serialize 24 HTTP timeouts.
    from concurrent.futures import ThreadPoolExecutor
    def fetch_publisher(pair):
        name,domain,scope=pair
        location='("Andhra Pradesh" OR Telangana OR Hyderabad OR Amaravati OR Visakhapatnam OR "ఆంధ్రప్రదేశ్" OR "తెలంగాణ" OR "హైదరాబాద్")'
        if scope=='tg':
            location='(Telangana OR Hyderabad OR Warangal OR Karimnagar OR Khammam OR Nizamabad OR Siddipet OR Nalgonda OR "తెలంగాణ" OR "హైదరాబాద్" OR "వరంగల్")'
        query="site:"+domain+" "+location+" when:7d"
        url=RSS_URL+"?"+urlencode({"q":query,"hl":"en-IN","gl":"IN","ceid":"IN:en"})
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; attributed regional headline discovery)","Accept":"application/rss+xml,application/xml,text/xml;q=0.9"})
            with urlopen(req,timeout=12) as response:xml=response.read(1_600_000)
            return name,parse(xml,domain),None
        except Exception as exc:
            return name,[],type(exc).__name__+": "+str(exc)[:80]
    # Independently search Telangana among its priority publishers.
    publisher_jobs=[(name,domain,"both") for name,domain in chosen]
    publisher_jobs += [(name,domain,"tg") for name,domain in priority]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name,rows,error in pool.map(fetch_publisher,publisher_jobs):
            if error:
                status["warnings"].append(name+": "+error)
                print("Regional Google News discovery warning",name,error,file=sys.stderr)
                continue
            status["successful_feeds"]+=1
            status["by_source"][name]=status["by_source"].get(name,0)+len(rows)
            for item in rows:found[item["url"]]=item
    # Broader general news searches: publisher-independent, two per state per cycle.
    # Always query AP and TG without ANY category term; rotate district coverage.
    # Google News returns only a bounded subset per search, so independent broad
    # location queries prevent politics/business keywords excluding other news.
    general_queries=[
      '"Andhra Pradesh" when:2d',
      '("ఆంధ్రప్రదేశ్" OR "ఏపీ" OR "అమరావతి") when:2d',
      '("Vijayawada" OR "Visakhapatnam" OR "Tirupati" OR "Guntur") when:2d',
      '("Kurnool" OR "Kakinada" OR "Nellore" OR "Srikakulam" OR "Kadapa") when:2d',
      '"Telangana" when:2d',
      '("తెలంగాణ" OR "హైదరాబాద్" OR "వరంగల్") when:2d',
      '("Hyderabad" OR "Secunderabad" OR "Warangal") when:2d',
      '("Karimnagar" OR "Nizamabad" OR "Khammam" OR "Nalgonda") when:2d',
    ]
    tg_district_queries=[
      '("Siddipet" OR "Sangareddy" OR "Medak" OR "Vikarabad") when:2d',
      '("Mahabubnagar" OR "Nagarkurnool" OR "Wanaparthy" OR "Gadwal") when:2d',
      '("Adilabad" OR "Nirmal" OR "Asifabad" OR "Mancherial") when:2d',
      '("Jagtial" OR "Peddapalli" OR "Sircilla" OR "Kamareddy") when:2d',
      '("Mulugu" OR "Bhadradri" OR "Kothagudem" OR "Mahabubabad") when:2d',
      '("Yadadri" OR "Suryapet" OR "Hanamkonda" OR "Rangareddy") when:2d',
      '("సిద్దిపేట" OR "సంగారెడ్డి" OR "మెదక్" OR "వికారాబాద్") when:2d',
      '("ఆదిలాబాద్" OR "నిర్మల్" OR "ములుగు" OR "గద్వాల") when:2d',
    ]
    selected_general=[general_queries[0],general_queries[1],general_queries[2+(cycle%2)],
                      general_queries[4],general_queries[5],general_queries[6],general_queries[7],
                      tg_district_queries[cycle%len(tg_district_queries)],
                      tg_district_queries[(cycle+3)%len(tg_district_queries)]]
    status["general_queries"]=len(selected_general)
    def fetch_general(term):
        url=RSS_URL+"?"+urlencode({"q":term,"hl":"en-IN","gl":"IN","ceid":"IN:en"})
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (MyBusinessNews AP TG General News)","Accept":"application/rss+xml,application/xml"})
            with urlopen(req,timeout=12) as response:xml=response.read(1_600_000)
            return parse(xml,None),None
        except Exception as exc:
            return [],type(exc).__name__+": "+str(exc)[:80]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index,(rows,error) in enumerate(pool.map(fetch_general,selected_general)):
            if error:
                status["warnings"].append("General query "+str(index)+": "+error)
                continue
            status["successful_feeds"]+=1
            status["by_source"]["AP/TG general "+str(index+1)]=len(rows)
            for item in rows:found[item["url"]]=item
    status["accepted"]=len(found)
    return list(found.values()),status
