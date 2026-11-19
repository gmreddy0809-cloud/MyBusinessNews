#!/usr/bin/env python3
"""Keyless source-link news index; no full article republishing."""
import json, re, os, sys
from rss_sources import collect_official, company_for
from avi_ivi import collect_avi_ivi
from world_google_news import collect_world
from publications import collect_publications
from regional_general import REGIONAL_QUERIES, keep_general
from desk_coverage import PF_QUERIES, REGIONAL_BUSINESS_QUERIES, from_telugu_publisher, index_gdelt, pf_match, pf_cutoff
from amfi_official import collect_amfi
from pf_google_news import collect_personal_finance, pf_editorial_match
from regional_google_news import collect_regional
from hyderabad_business_news import collect_hyderabad_business
from snippets import enrich
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"data"/"news.json"
API="https://api.gdeltproject.org/api/v2/doc/doc"
QUERIES=[
 ("india", '(India OR Indian) (business OR investment OR corporate OR manufacturing)'),
 ("hyderabad", 'Hyderabad (business OR pharma OR GCC OR investment OR company)'),
 ("india", '(India OR Indian) (banking OR stock market OR startup OR aviation)'),
 ("world", '(business OR economy OR earnings OR acquisition) sourcelang:english'),
 ("andhra-pradesh", '("Andhra Pradesh" OR Visakhapatnam OR Amaravati OR Tirupati) (investment OR business OR industry)'),
 ("telangana", 'Telangana (business OR investment OR manufacturing OR pharma)'),
 ("india", '(India OR Indian) (automotive OR pharmaceuticals OR technology OR finance)'),
 ("world", '(markets OR global economy OR aviation OR renewables) sourcelang:english')
]
BLOCKED=("wsj.com","ft.com","bloomberg.com","nytimes.com","economist.com","livemint.com","thehindu.com","thehindubusinessline.com","economictimes.indiatimes.com","business-standard.com","theinformation.com")
RELEVANT=re.compile(r'\b(business|industr|econom|invest|fund|start.?up|gcc|pharma|health|bank|financial|loan|insuran|airlin|airport|aviation|aircraft|auto|vehicle|manufactur|company|companies|profit|revenue|earnings|market|stock|ipo|shares?|equity|merger|acquisition|technology|software|AI|semiconductor|renewable|energy|solar|oil|gas|infrastructure|real estate|retail|telecom|shipping|logistics|export|import|policy|trade|factory|tourism|corporate|contract|capital|economic|hospital|investment|construction)\w*\b',re.I)
SECTORS=[
 ("Aviation & Airports",r'airline|airport|aviation|aircraft|boeing|airbus|aerospace|\bmro\b'),
 ("GCCs",r'global capability|global in.house|\bgccs?\b'),
 ("Pharma & Life Sciences",r'pharma|drugmaker|biotech|clinical|usfda|fda approval|life sciences'),
 ("Healthcare & Hospitals",r'hospital|healthcare|diagnostic|medical'),
 ("Automobiles & EV",r'auto|electric vehicle|automaker|maruti|car sales|suv'),
 ("Startups",r'startup|start.up|unicorn'),
 ("Funding & Investments",r'funding|fundrais|investment|investor|venture capital|private equity'),
 ("IT & AI",r'software|technology|artificial intelligence|semiconductor|cybersecurity|data cent|cloud computing|\bai\b'),
 ("Personal Finance",r'mutual fund|personal finance|retirement|life insurance|health insurance|fixed deposit|home loan|\bsip\b|\bppf\b'),
 ("Banking & Finance",r'bank|credit|lending|\brbi\b|nbfc|finance|fintech'),
 ("Markets & IPOs",r'\bipo\b|stock market|nifty|sensex|nasdaq|wall street|shares|equity market'),
 ("Real Estate",r'real estate|property|housing|office space|realty'),
 ("Energy & Renewables",r'solar|renewable|wind power|oil|gas|energy|battery|power generation'),
 ("Infrastructure",r'infrastructure|railway|highway|construction|metro rail'),
 ("Logistics & Shipping",r'logistics|port|shipping|cargo|supply chain'),
 ("FMCG & Retail",r'fmcg|retail|consumer goods|supermarket|e.commerce'),
 ("Manufacturing",r'manufactur|factory|industrial park|steel|cement'),
 ("Telecom",r'telecom|5g|6g|mobile network'),
 ("Tourism & Hospitality",r'tourism|hotel|hospitality|resort'),
 ("Corporate & Results",r'earnings|profit|revenue|merger|acquisition|dividend|quarterly'),
 ("Economy & Policy",r'economy|inflation|\bgdp\b|budget|policy|tariff|trade agreement')
]
REGIONS=[
 ("hyderabad",r'hyderabad|cyberabad|secunderabad|gachibowli|shamshabad'),
 ("andhra-pradesh",r'andhra pradesh|visakhapatnam|vizag|amaravati|vijayawada|tirupati|kakinada|guntur'),
 ("telangana",r'telangana|warangal|karimnagar|nizamabad|sangareddy|khammam')
]
def dt(s):
    try:
        if re.match(r'^\d{8}T\d{6}Z$',str(s)): return datetime.strptime(s,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
    except Exception: return datetime.fromtimestamp(0,timezone.utc)
def classify(title,group,country):
    PF_RE=re.compile(r'fixed deposit|sovereign gold bond|\bsgb\b|gold bond|domestic money transfer|savings account|mutual fund|personal finance|retirement|pension|\bsip\b|\bppf\b|\bepf\b|health insurance|life insurance|term insurance|credit score|credit card|income tax|tax saving|gold loan|home loan|wealth planning|recurring deposit',re.I)
    sector="Personal Finance" if PF_RE.search(title) else next((name for name,p in SECTORS if re.search(p,title,re.I)),"Other Business")
    region=next((name for name,p in REGIONS if re.search(p,title,re.I)),None)
    if region is None:
        region,_=company_for(title)
    if region is None:
        region=group if group in ("hyderabad","telangana","andhra-pradesh") else ("india" if (re.search(r'\b(india|indian|nifty|sensex|mumbai|delhi|bengaluru)\b',title,re.I) or str(country).lower() in ("india","in") or group=="india") else "world")
    return region,sector
def keep(row,group):
    title=re.sub(r'\s+',' ',str(row.get("title") or "")).strip()
    url=str(row.get("url") or "").strip()
    p=urlparse(url)
    if p.scheme not in ("https","http") or not p.hostname or len(title)<12:return None
    domain=p.hostname.removeprefix("www.").lower()
    if any(domain==x or domain.endswith("."+x) for x in BLOCKED):return None
    if group in ("india","world") and not RELEVANT.search(title):return None
    country=row.get("sourcecountry") or ""
    region,sector=classify(title,group,country)
    return {"id":url,"url":url,"title":title,"source":row.get("domain") or domain,"domain":domain,"region":region,"sector":sector,"seen":row.get("seendate") or "","time_basis":"indexed","language":row.get("language") or "","sourcecountry":country}
def request(query):
    days="7d" if any(query==q for _,q in PF_QUERIES+REGIONAL_BUSINESS_QUERIES) else "2d"
    url=API+"?"+urlencode({"query":query,"mode":"artlist","format":"json","maxrecords":150,"timespan":days,"sort":"datedesc"})
    req=Request(url,headers={"User-Agent":"MyBusinessNews/1.0 open-link-index","Accept":"application/json"})
    with urlopen(req,timeout=30) as res: data=json.loads(res.read(3_000_000).decode("utf-8-sig"))
    return data.get("articles",[])
def main():
    try: old=json.loads(DEST.read_text(encoding="utf-8"))
    except Exception:old={"articles":[]}
    news={x["url"]:x for x in old.get("articles",[]) if x.get("url") and not (x.get("origin")=="google-news-rss" and x.get("desk")=="personal-finance" and not pf_editorial_match(x.get("title","")))}
    official=collect_official()
    for entry in official:
        if pf_match(entry.get("title","")):
            entry["reader_finance"]=True
        prev=news.get(entry["url"])
        # RSS entries without a published date use first-observed time.
        # Keep that original observation on every later refresh, never inflate recency.
        if prev and entry.get("time_basis")=="first_seen":
            entry["seen"]=prev.get("seen") or entry["seen"]
        if prev and entry.get("time_basis")!="feed" and prev.get("time_basis")=="feed":
            entry["seen"]=prev.get("seen") or entry["seen"]
            entry["time_basis"]="feed"
        if prev:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and prev.get(key):
                    entry[key]=prev[key]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    misc_rows,misc_status=collect_avi_ivi()
    for entry in misc_rows:
        prev=news.get(entry["url"])
        if prev and entry.get("time_basis")=="first_seen":
            entry["seen"]=prev.get("seen") or entry["seen"]
        if prev:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and prev.get(key):
                    entry[key]=prev[key]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    world_rows,world_discovery_status=collect_world()
    for entry in world_rows:
        prev=news.get(entry["url"])
        if prev:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and prev.get(key):entry[key]=prev[key]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    publication_rows,publication_status=collect_publications()
    pub_tags=from_telugu_publisher(publication_rows)
    for entry in publication_rows:
        entry.update(pub_tags.get(entry["url"],{}))
        prev=news.get(entry["url"])
        if prev:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and prev.get(key):
                    entry[key]=prev[key]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    amfi_rows,amfi_status=collect_amfi()
    for entry in amfi_rows:
        prev=news.get(entry["url"])
        if prev:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and prev.get(key):
                    entry[key]=prev[key]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    # Separate source-based India PF discovery from the GDELT endpoint.
    # Google News links are labeled as discovery click-throughs, not publisher syndication.
    pf_discovery_rows,pf_discovery_status=collect_personal_finance()
    for entry in pf_discovery_rows:
        prev=news.get(entry["url"])
        if prev:
            for field in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(field) and prev.get(field):
                    entry[field]=prev[field]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    # Broaden AP/TG news discovery without copying restricted publisher RSS or bodies.
    regional_discovery_rows,regional_discovery_status=collect_regional()
    for entry in regional_discovery_rows:
        prev=news.get(entry["url"])
        if prev:
            for field in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(field) and prev.get(field):
                    entry[field]=prev[field]
        if not prev or dt(entry["seen"])>=dt(prev.get("seen")):
            news[entry["url"]]=entry
    # Regional-business discovery for Hyderabad GCCs, unlisted pharma and startups.
    hyd_business_rows,hyd_business_status=collect_hyderabad_business()
    for entry in hyd_business_rows:
        previous=news.get(entry["url"])
        if previous:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and previous.get(key):
                    entry[key]=previous[key]
        if not previous or dt(entry["seen"])>=dt(previous.get("seen")):
            news[entry["url"]]=entry
    good=bool(pf_discovery_status["successful_feeds"] or official or amfi_rows) or misc_status["successful_feeds"]>0 or publication_status["successful_feeds"]>0
    count_by_region={}
    regional_general_count=sum(1 for item in news.values() if item.get("desk")=="regional-general")
    for item in news.values():
        if item.get("desk") in ("avi-ivi","telugu-patrikalu","english-magazines","regional-general","personal-finance","regional-business"):continue
        region=item.get("region") or ""
        count_by_region[region]=count_by_region.get(region,0)+1
    cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    # Check just one query per run: the free GDELT endpoint frequently rate-limits multi-query bursts.
    # Balanced, keyless-source polling: PF and AP/TG businesses each receive
    # two slots per six cycles. Remaining slots serve general/business news.
    # Each half-hour slot performs AT MOST one GDELT request.
    search_type=("pf","regional-business","regional-general",
                 "pf","regional-business","business")[cycle%6]
    if search_type=="pf":
        selected=PF_QUERIES[(cycle//3)%len(PF_QUERIES)]
    elif search_type=="regional-business":
        selected=REGIONAL_BUSINESS_QUERIES[(cycle//3)%len(REGIONAL_BUSINESS_QUERIES)]
    elif search_type=="regional-general":
        selected=REGIONAL_QUERIES[(cycle//6)%len(REGIONAL_QUERIES)]
    else:
        selected=QUERIES[(cycle//6)%len(QUERIES)]
    group,q=selected
    now=datetime.now(timezone.utc)
    gdelt_state=dict((old.get("source_status") or {}).get("gdelt") or {})
    retry_after=dt(gdelt_state.get("retry_after"))
    if now<retry_after:
        print("GDELT paused until",gdelt_state["retry_after"],"to respect free feed rate limits",flush=True)
        gdelt_state["state"]="cooldown"
    else:
        gdelt_state["last_attempt"]=now.isoformat()
        try:
            rows=request(q)
            count=0
            for row in rows:
                if search_type=="regional-general":
                    item=keep_general(row,group)
                elif search_type in ("pf","regional-business"):
                    item=index_gdelt(row,search_type,group)
                else:
                    item=keep(row,group)
                    if item and pf_match(item["title"]):
                        item["reader_finance"]=True
                if item and (item["url"] not in news or dt(item["seen"])>=dt(news[item["url"]].get("seen"))):
                    news[item["url"]]=item
                    count+=1
            good=True
            gdelt_state={"state":"ok","last_attempt":now.isoformat(),"last_success":now.isoformat(),"retry_after":(now+timedelta(minutes=30)).isoformat()}
            print(search_type,group,"received",len(rows),"accepted",count,flush=True)
        except Exception as exc:
            limited=getattr(exc,"code",None)==429
            next_time=now+timedelta(hours=2 if limited else 1)
            gdelt_state.update({"state":"rate_limited" if limited else "temporarily_unavailable","retry_after":next_time.isoformat()})
            print("GDELT feed unavailable; retry after",next_time.isoformat(),str(exc),file=sys.stderr,flush=True)
    old_by_url={x.get("url"):x for x in old.get("articles",[]) if x.get("url")}
    for url,entry in news.items():
        previous=old_by_url.get(url)
        if previous:
            for key in ("title_te","snippet_te","snippet_basis","summary"):
                if not entry.get(key) and previous.get(key):
                    entry[key]=previous[key]
    # Preserve the 14-Nov-2026 archive instead of dropping older business articles weekly.
    cutoff=datetime(2026,11,13,18,30,tzinfo=timezone.utc)
    pf_from=pf_cutoff()
    # Avii Ivii relaunch: start its archive from 19 Nov 2026, 00:00 IST.
    avi_start=datetime(2026,11,18,18,30,tzinfo=timezone.utc)
    rows=[x for x in news.values()
          if (x.get("desk")!="avi-ivi" or dt(x.get("seen"))>=avi_start)
          and (dt(x.get("seen"))>cutoff or (
              (x.get("desk")=="personal-finance" or x.get("reader_finance")) and
              dt(x.get("seen"))>=pf_from
          ) or (
              x.get("desk")=="telugu-patrikalu" and
              x.get("source","").startswith("Dharani News") and
              dt(x.get("seen"))>datetime.now(timezone.utc)-timedelta(days=30)
          ))]
    rows.sort(key=lambda x:dt(x.get("seen")),reverse=True)
    # Keep regional exchange announcements and official updates visible even with a crowded global index.
    # Keep the business newsroom and Avii Ivii independent despite one shared JSON index.
    # Reserve space per desk: abundant national news must never crowd out PF
    # and regional corporate disclosures during the 14-Nov onward backfill.
    business_rows=[x for x in rows if x.get("desk","business")=="business"][:12000]
    pf_rows=[x for x in rows if x.get("desk")=="personal-finance"][:12000]
    regional_business_rows=[x for x in rows if x.get("desk")=="regional-business"][:350]
    misc_rows=[x for x in rows if x.get("desk")=="avi-ivi"][:12000]
    english_rows=[x for x in rows if x.get("desk")=="english-magazines"][:12000]
    regional_rows=[x for x in rows if x.get("desk")=="regional-general"][:12000]
    telugu_rows=[x for x in rows if x.get("desk")=="telugu-patrikalu"][:180]
    rows=sorted(business_rows+pf_rows+regional_business_rows+misc_rows+english_rows+telugu_rows+regional_rows,key=lambda x:dt(x.get("seen")),reverse=True)
    snippet_status=enrich(rows)
    payload={"generated_at":datetime.now(timezone.utc).isoformat() if good else old.get("generated_at"),"articles":rows,"sources":["NSE","BSE","RBI","SEBI","PIB","NASA","WHO","UN News","The Conversation","Oneindia Telugu","Dharani News","AMFI","Google News RSS (discovery)","The GDELT Project"],"source_status":{"personal_finance_discovery":pf_discovery_status,"regional_discovery":regional_discovery_status,"hyderabad_business_discovery":hyd_business_status,"telugu_snippets":snippet_status,"gdelt":gdelt_state,"official_rss_matches":len(official),"avi_ivi":misc_status,"world_discovery":world_discovery_status,"publications":publication_status,"amfi_rss":amfi_status,"dedicated_desks":{"personal_finance_links":len(pf_rows),"regional_business_links":len(regional_business_rows),"personal_finance_from_14_nov_2026":pf_from.isoformat()}},"note":"Official RSS feed dates, first-observed times and GDELT indexed times are not interchangeable with independently verified publication times. Source links remain with publishers."}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("news:",len(payload["articles"]),"successful queries:",good,flush=True)
if __name__=="__main__":main()
