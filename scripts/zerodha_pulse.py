#!/usr/bin/env python3
"""Zerodha Pulse RSS discovery; links open original publishers, not copied articles."""
import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from desk_coverage import pf_match
from rss_sources import company_for, explicit_locality

FEED = "https://pulse.zerodha.com/feed.php?n=100"
ARCHIVE_DAYS = 7
PF = re.compile(r"\b(mutual funds?|sip|systematic investment|fixed deposits?|fd rates?|ppf|epf|nps|pension|retirement|income tax|tax saving|tax return|itr|insurance|health cover|life cover|credit cards?|credit score|home loans?|personal loans?|gold loans?|savings account|bank deposit|personal finance|kyc|upi|nominee|nomination|investor education)\b", re.I)
MARKETS = re.compile(r"\b(stock|stocks|shares|equity|sensex|nifty|sebi|ipo|fpo|bse|nse|market|trading|demat|mutual fund|index fund|etf)\b", re.I)
BANKING = re.compile(r"\b(bank|banking|rbi|nbfc|lending|credit|interest rate|monetary policy)\b", re.I)
RESULTS = re.compile(r"\b(results|earnings|profit|revenue|quarterly|dividend|merger|acquisition)\b", re.I)
BUSINESS = re.compile(r"\b(business|economic|economy|investment|funding|startup|technology|software|pharma|manufacturing|exports?|imports?|industry|companies|corporate|automotive|energy|real estate|property|airline|airport|trade|inflation|gdp|tax|finance|financial|government|policy)\b", re.I)
SKIP = re.compile(r"\b(cricket|football|bollywood|celebrity|movie review|horoscope|astrology)\b", re.I)
DC = "{http://purl.org/dc/elements/1.1/}"

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()

def published(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def parse_feed(xml, now=None):
    now = now or datetime.now(timezone.utc)
    root = ET.fromstring(xml)
    rows = []
    for item in root.findall(".//item"):
        title = clean(item.findtext("title"))
        desc = clean(item.findtext("description"))
        url = (item.findtext("link") or "").strip()
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower().removeprefix("www.")
        if parsed.scheme not in ("https", "http") or not domain or domain.endswith("zerodha.com"):
            continue
        if len(title) < 12 or SKIP.search(title) or not (PF.search(title) or pf_match(title) or MARKETS.search(title) or BANKING.search(title) or RESULTS.search(title) or BUSINESS.search(title)):
            continue
        date = published(item.findtext("pubDate") or item.findtext(DC+"date"))
        if date and not (now-timedelta(days=ARCHIVE_DAYS) <= date <= now+timedelta(hours=2)):
            continue
        region = explicit_locality(title) or company_for(title)[0] or ("india" if re.search(r"\b(india|indian|nifty|sensex|rbi|sebi|rupee)\b", title, re.I) or domain.endswith(".in") else "world")
        if PF.search(title) or pf_match(title):
            sector, desk = "Personal Finance", "personal-finance"
        elif MARKETS.search(title):
            sector, desk = "Markets & IPOs", "business"
        elif BANKING.search(title):
            sector, desk = "Banking & Finance", "business"
        elif RESULTS.search(title):
            sector, desk = "Corporate & Results", "business"
        else:
            sector, desk = "Other Business", "business"
        source = domain
        rows.append({
            "id": url, "url": url, "title": title, "source": source,
            "domain": domain, "region": region, "sector": sector, "desk": desk,
            "reader_finance": desk == "personal-finance",
            "seen": date.isoformat() if date else now.isoformat(),
            "time_basis": "feed" if date else "first_seen",
            "origin": "zerodha-pulse-rss", "discovered_via": "Zerodha Pulse",
            "summary": desc[:380] if desc and desc.casefold() != title.casefold() else "",
            "language": "English",
        })
    return rows

def collect_pulse():
    request = Request(FEED, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MyBusinessNews/1.0; RSS discovery)",
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9,*/*;q=0.1",
    })
    with urlopen(request, timeout=18) as response:
        xml = response.read(2_500_000)
    rows = parse_feed(xml)
    return rows, {"accepted": len(rows), "feed": FEED}
