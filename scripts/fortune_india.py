#!/usr/bin/env python3
"""Fortune India business headline discovery through Google News RSS.

Discovery only: attributed headlines and Google News click-through links.
No publisher bodies, images, descriptions or assertion of RSS syndication rights.
"""
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from rss_sources import cleanup, feed_date
from desk_coverage import pf_match, local_business_match

DOMAIN = "fortuneindia.com"
SEARCH = "https://news.google.com/rss/search"
QUERIES = (
    'site:fortuneindia.com (business OR companies OR earnings OR markets OR economy) when:7d',
    'site:fortuneindia.com (startup OR funding OR manufacturing OR pharma OR technology OR investments) when:7d',
    'site:fortuneindia.com (banking OR finance OR IPO OR policy OR corporate) when:7d',
)
SKIP = re.compile(r"\b(cricket|football|horoscope|celebrity|fashion show|movie review)\b", re.I)
PF = re.compile(r"\b(mutual fund|insurance|retirement|pension|income tax|tax saving|fixed deposit|credit card|home loan|personal finance|savings account|SIP|NPS|PPF|EPF)\b",re.I)
MARKET = re.compile(r"\b(stock|shares|equity|markets|sensex|nifty|ipo|sebi|bse|nse|investor)\b",re.I)
FINANCE = re.compile(r"\b(bank|banking|nbfc|credit|rbi|lending)\b",re.I)
BUSINESS = re.compile(r"\b(business|industr|econom|company|companies|corporate|profit|revenue|earnings|results|funding|investment|startup|manufactur|technology|pharma|healthcare|energy|automotive|trade|exports?|policy|tax|merger|acquisition|real estate|aviation|airport|gdp|inflation|infrastructure)\b",re.I)

def parse_feed(xml, now=None):
    now = now or datetime.now(timezone.utc)
    try: root = ET.fromstring(xml)
    except ET.ParseError: return []
    out = []
    for node in root.findall(".//item")[:100]:
        src=node.find("source")
        if src is None: continue
        src_url=src.get("url","")
        host=(urlparse(src_url).hostname or "").lower().removeprefix("www.")
        if host != DOMAIN:continue
        publisher=cleanup("".join(src.itertext())) or "Fortune India"
        title=cleanup(node.findtext("title"))
        if title.lower().endswith(" - "+publisher.lower()):
            title=title[:-(len(publisher)+3)].strip()
        if not 15<=len(title)<=300 or SKIP.search(title):continue
        if not (PF.search(title) or pf_match(title) or MARKET.search(title) or FINANCE.search(title) or BUSINESS.search(title)):continue
        url=(node.findtext("link") or "").strip()
        parsed=urlparse(url)
        if parsed.scheme!="https" or parsed.hostname!="news.google.com":continue
        date=feed_date(node.findtext("pubDate"))
        if not date or date>now+timedelta(hours=2) or date<now-timedelta(days=7):continue
        if PF.search(title) or pf_match(title): desk,sector="personal-finance","Personal Finance"
        elif MARKET.search(title):desk,sector="business","Markets & IPOs"
        elif FINANCE.search(title):desk,sector="business","Banking & Finance"
        else:desk,sector="business","Other Business"
        region=local_business_match(title) or "india"
        if region!="india" and desk=="business":desk="regional-business"
        out.append({
            "id":url,"url":url,"title":title,
            "source":"Fortune India • Google News","domain":DOMAIN,
            "region":region,"sector":sector,"desk":desk,
            "regional_business":desk=="regional-business",
            "reader_finance":desk=="personal-finance",
            "seen":date.isoformat(),"time_basis":"google_rss",
            "origin":"google-news-rss","link_type":"google-news-redirect",
            "language":"English","sourcecountry":"India",
        })
    return out

def collect_fortune_india(cycle=None):
    if cycle is None:cycle=int(datetime.now(timezone.utc).timestamp()//1800)
    query=QUERIES[cycle%len(QUERIES)]
    url=SEARCH+"?"+urlencode({"q":query,"hl":"en-IN","gl":"IN","ceid":"IN:en"})
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; MyBusinessNews/1.0; headline discovery)",
                              "Accept":"application/rss+xml,application/xml,text/xml;q=0.9"})
    with urlopen(req,timeout=16) as response:xml=response.read(1_500_000)
    rows=parse_feed(xml)
    return rows,{"accepted":len(rows),"discovery":"google-news-rss","query":query}
