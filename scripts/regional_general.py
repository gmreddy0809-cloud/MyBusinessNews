#!/usr/bin/env python3
"""Source-linked AP/TG general-interest news classification for GDELT index.

Not corporate business news: specifically government, politics, public affairs,
welfare, education, agriculture, public health, courts, civic issues and society.
Only a headline, source domain, article URL, GDELT index timestamp are stored.
"""
import re
from urllib.parse import urlparse

# Bounded queries, rotated through the existing 30-minute keyless GDELT budget.
REGIONAL_QUERIES=[
 ('telangana','(Telangana OR Hyderabad) (government OR minister OR assembly OR welfare OR election OR health OR education) sourcelang:english'),
 ('andhra-pradesh','("Andhra Pradesh" OR Amaravati OR Vijayawada) (chief minister OR government OR election OR assembly OR schools OR farmers) sourcelang:english'),
 ('telangana','(Revanth Reddy OR "Telangana cabinet" OR "Telangana government") (decision OR politics OR policy OR scheme OR minister) sourcelang:english'),
 ('andhra-pradesh','(Chandrababu Naidu OR Pawan Kalyan OR "Andhra Pradesh") (politics OR government OR ministers OR farmers OR schools) sourcelang:english')
]
BLOCKED_DOMAINS=('wsj.com','ft.com','bloomberg.com','nytimes.com','economist.com',
                 'livemint.com','thehindu.com','thehindubusinessline.com',
                 'economictimes.indiatimes.com','business-standard.com','theinformation.com')
TELANGANA=re.compile(r'telangana|hyderabad|secunderabad|cyberabad|revanth reddy|warangal|karimnagar|nizamabad|khammam|kcr\b|ktr\b|komatireddy|bhatti vikramarka',re.I)
ANDHRA=re.compile(r'andhra pradesh|amaravati|vijayawada|visakhapatnam|vizag|tirupati|guntur|nellore|chandrababu|pawan kalyan|ys jagan|ysr congress|lokesh naidu|nara lokesh',re.I)
PUBLIC_TOPIC=re.compile(
 r'government|chief minister|\bcm\b|minister|cabinet|assembly|election|mla\b|mp\b|'
 r'politic|party|\btdp\b|\bycp\b|\bbjp\b|\bb[rs]\b|congress|'
 r'court|judge|law|police|crime|arrest|accident|disaster|cyclone|flood|weather|'
 r'welfare|pension|ration|scheme|farmer|agricult|crop|water|power|electricity|'
 r'school|college|university|education|students|recruitment|jobs|exam|'
 r'health|hospital|disease|medical|women|transport|road|metro|'
 r'municipal|village|civic|local|public|protest|people|society|temple|'
 r'development|budget|policy|funds?\b|land|housing|forest|environment',re.I)
CORPORATE_ONLY=re.compile(r'quarterly (results?|profit)|net profit|earnings per share|ipo allotment|stock price|share price|market cap|investor call|analyst rating',re.I)

def region_from_title_url(title,url):
    """No state inferred solely from query match or source country."""
    parsed=urlparse(url)
    path=parsed.path.lower()
    # Explicit location in headline is strongest; a regional article path
    # is next. Generic publisher homepages cannot establish a region.
    if TELANGANA.search(title):return 'telangana' if not re.search(r'hyderabad|secunderabad|cyberabad',title,re.I) else 'hyderabad'
    if ANDHRA.search(title):return 'andhra-pradesh'
    if re.search(r'/(telangana|hyderabad)/',path):return 'telangana'
    if re.search(r'/(andhra-pradesh|andhrapradesh)/',path):return 'andhra-pradesh'
    return None

def category(title):
    if re.search(r'chief minister|minister|cabinet|assembly|election|mla\b|mp\b|politic|revanth reddy|chandrababu|jagan|pawan kalyan|party|congress|bjp|tdp',title,re.I):return 'Politics & Government'
    if re.search(r'farm|crop|agricultur|irrigat|water',title,re.I):return 'Agriculture & Rural'
    if re.search(r'school|student|university|college|exam|education|teacher|recruitment',title,re.I):return 'Education & Jobs'
    if re.search(r'health|medical|hospital|disease|vaccin',title,re.I):return 'Health & Public Services'
    if re.search(r'court|police|crime|arrest|incident|murder|accident',title,re.I):return 'Crime & Courts'
    if re.search(r'cyclone|weather|rain|flood|forest|environment|heatwave',title,re.I):return 'Weather & Environment'
    if re.search(r'welfare|ration|pension|scheme|housing|public|transport|road|metro',title,re.I):return 'Public Issues & Welfare'
    return 'Regional General News'

def keep_general(row,group=None):
    from urllib.parse import urlparse
    title=re.sub(r'\s+',' ',str(row.get('title') or '')).strip()
    link=str(row.get('url') or '').strip()
    parsed=urlparse(link)
    hostname=(parsed.hostname or '').lower().removeprefix('www.')
    if not link.startswith(('https://','http://')) or not hostname or len(title)<12 or len(title)>280:return None
    if any(hostname==d or hostname.endswith('.'+d) for d in BLOCKED_DOMAINS):return None
    region=region_from_title_url(title,link)
    if not region or not PUBLIC_TOPIC.search(title) or CORPORATE_ONLY.search(title):return None
    # Only explicit English GDELT general-news matches; Telugu uses credited RSS.
    lang=str(row.get('language') or '').lower()
    if lang and lang not in ('english','en'):return None
    return {
        'id':link,'url':link,'title':title,'source':row.get('domain') or hostname,
        'domain':hostname,'region':region,'sector':category(title),
        'seen':row.get('seendate') or '',
        'time_basis':'indexed','language':'English',
        'sourcecountry':row.get('sourcecountry') or '',
        'origin':'gdelt-open-index','desk':'regional-general'
    }
