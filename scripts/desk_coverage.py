#!/usr/bin/env python3
"""AP/TG company intelligence and India personal-finance headline discovery.

Indexes title, original story URL, domain and original feed/index timestamp ONLY.
Public publisher RSS without syndication permission is NOT scraped or republished.
"""
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from rss_sources import company_for, explicit_locality

# Onboarding backfill: 14 November 2026, 00:00 IST. This is the *earliest*
# permitted feed/index date for PF, not a fabricated publisher publication date.
PF_START_UTC=datetime(2026,11,13,18,30,tzinfo=timezone.utc)
def pf_cutoff(now=None):
    now=now or datetime.now(timezone.utc)
    return max(PF_START_UTC,now-timedelta(days=30))

# Search only a single GDELT query per half-hour, keeping API fair usage
# and respecting HTTP 429 Retry-After signals / service cooldowns.
PF_QUERIES=[
 ('india','(personal finance OR savings OR deposits OR "fixed deposit" OR retirement OR "pension planning") sourcelang:english'),
 ('india','("mutual funds" OR "systematic investment plan" OR "new fund offer" OR "SIP investment") sourcelang:english'),
 ('india','("health insurance" OR "life insurance" OR "term insurance" OR "insurance claim") sourcelang:english'),
 ('india','("income tax" OR "tax refund" OR "tax planning" OR "capital gains tax") sourcelang:english'),
 ('india','("gold loan" OR "home loan" OR "credit score" OR "credit card" OR EMI) sourcelang:english'),
 ('india','("PPF" OR "EPF" OR "NPS" OR "senior citizen savings" OR "postal savings") sourcelang:english'),
 ('india','("bank customers" OR "banking fraud" OR "UPI fraud" OR "digital payments") sourcelang:english'),
 ('india','("wealth planning" OR "retirement corpus" OR "SGB" OR "interest rates") sourcelang:english')
]
REGIONAL_BUSINESS_QUERIES=[
 ('hyderabad','(Hyderabad OR Telangana) (pharma OR "GCC" OR "global capability" OR investment OR startup) sourcelang:english'),
 ('andhra-pradesh','("Andhra Pradesh" OR Amaravati OR Visakhapatnam OR Vizag) (industry OR company OR investment OR manufacturing) sourcelang:english'),
 ('hyderabad','("Dr Reddys" OR Aurobindo OR Cyient OR Laurus OR Granules OR Divis) (business OR expansion OR profit OR contract) sourcelang:english'),
 ('telangana','(Hyderabad OR Telangana OR Warangal) (IT OR software OR "data centre" OR airport OR hospital OR funding) sourcelang:english'),
 ('andhra-pradesh','("Amara Raja" OR "Avanti Feeds" OR "Andhra Paper" OR "Apex Frozen") (results OR expansion OR earnings OR investment) sourcelang:english'),
 ('hyderabad','(Hyderabad OR Telangana) (aerospace OR defence OR "MRO" OR GCC OR "life sciences") sourcelang:english'),
 ('telangana','(Telangana OR Hyderabad) (real estate OR logistics OR manufacturing OR "industrial park") sourcelang:english'),
 ('andhra-pradesh','(Tirupati OR Vijayawada OR Sri City OR Kakinada OR Visakhapatnam) (investment OR company OR expansion OR startup) sourcelang:english')
]
PF_EN=re.compile(
 r'\b(?:personal finance|fixed deposits?|term deposits?|savings account|savings scheme|'
 r'bank deposits?|deposit interest|interest rates? on deposit|mutual funds?|'
 r'systematic investment plans?|\bsip\b|step.up sip|new fund offer|\bnfo\b|'
 r'portfolio rebalanc|direct mutual fund|redemption of fund|'
 r'life insurance|health insurance|term insurance|insurance claim|insurance premium|'
 r'critical illness cover|policyholder|cashless claims?|'
 r'income tax|tax returns?|tax refunds?|\bitr\b|tax deductions?|capital gains tax|'
 r'old tax regime|new tax regime|'
 r'retirement|retirement corpus|pensioners?|\bnps\b|\bepf\b|\bppf\b|\bapy\b|'
 r'provident fund|senior citizens? savings|post office schemes?|postal savings|'
 r'home loans?|housing loans?|gold loans?|education loans?|personal loans?|'
 r'credit cards?|credit scores?|credit reports?|\bcibil\b|loan emi|'
 r'loan repayment|prepayment of loans?|loan foreclosure|'
 r'bank customers?|banking customers?|unclaimed deposits?|bank nominations?|'
 r'upi fraud|cyber fraud|financial fraud|digital payments? fraud|'
 r'sovereign gold bonds?|\bsgb\b|gold bond redemption|'
 r'investor protection|investor grievances?|financial planning|wealth planning|'
 r'household savings|monthly budget|financial independence)\b',re.I)
PF_TE=re.compile(
 r'పొదుపు|మ్యూచువల్.?ఫండ్|సిప్|బీమా|ఇన్సూరెన్స్|పెన్షన్|పదవీ.?విరమణ|'
 r'ఆదాయపు.?పన్ను|పన్ను.?రీఫండ్|పీపీఎఫ్|ఈపీఎఫ్|ఎన్.?పీఎస్|'
 r'హోమ్.?లోన్|గృహ.?రుణం|బంగారు.?రుణం|వ్యక్తిగత.?రుణం|'
 r'క్రెడిట్.?కార్డు|సిబిల్|రుణ.?గ్రహీత|ఈఎంఐ|బ్యాంకు.?ఖాతా|'
 r'బ్యాంకు.?వడ్డీ|సావరిన్.?గోల్డ్|డిపాజిట్లు|ఫిక్స్.?డ్.?డిపాజిట్',re.I)
CORPORATE_EN=re.compile(
 r'\b(?:pharma|biotech|laborator|manufactur|plant|factory|industrial|'
 r'company|companies|corporate|quarterly results?|earnings|profit|revenue|'
 r'acquisition|merger|investment|funding|start.?up|venture capital|'
 r'expansion|contract|order win|aerospace|aviation|airport|aircraft|'
 r'global capability|gccs?|software|technolog|data cent|it services|'
 r'listed|filings?|retail|real estate|logistic|ports?|hospital|healthcare|'
 r'energy|solar|renewable|defence|infrastructure|tourism|construction|'
 r'exports?|industrial park|production|capacity)\b',re.I)
CORPORATE_TE=re.compile(r'పెట్టుబడ|కంపెనీ|సంస్థ|పరిశ్రమ|విస్తరణ|ఉత్పత్తి|ఫార్మా|స్టార్టప్|'
                        r'ఒప్పందం|లాభాలు|ఆదాయం|నిధులు|వ్యాపార|ఐటీ|జీసీసీ|ఆర్థిక ఫలితాలు|'
                        r'కర్మాగార|మౌలిక వసతులు|పారిశ్రామిక',re.I)
GEO_TE=re.compile(r'హైదరాబాద్|సికింద్రాబాద్|తెలంగాణ|ఆంధ్రప్రదేశ్|ఆంధ్ర ప్రదేశ్|'
                  r'అమరావతి|విశాఖ|విజయవాడ|తిరుపతి|కాకినాడ|గుంటూరు|వరంగల్|'
                  r'రంగారెడ్డి|మేడ్చల్|సంగారెడ్డి|శ్రీసిటీ',re.I)
PAYWALLED={'wsj.com','ft.com','bloomberg.com','nytimes.com','economist.com',
           'livemint.com','thehindu.com','thehindubusinessline.com',
           'economictimes.indiatimes.com','business-standard.com','theinformation.com'}

def pf_match(title):
    return bool(PF_EN.search(title) or PF_TE.search(title))

def local_business_match(title,region=None):
    known_region,_=company_for(title)
    if known_region:return known_region
    region=region or explicit_locality(title)
    if region in ('hyderabad','telangana','andhra-pradesh') and (
            CORPORATE_EN.search(title) or CORPORATE_TE.search(title)):
        return region
    return None

def from_telugu_publisher(rows):
    """Flag already permitted RSS titles for multiple desks without duplication.

    Keep the publisher row's original 'desk' so it remains in Telugu Patrikalu
    and AP+TG general news. No RSS fetch and no body copying here.
    """
    by_url={}
    for row in rows:
        if row.get('desk')!='telugu-patrikalu':continue
        title=row.get('title') or ''
        flags={}
        if pf_match(title):
            flags['reader_finance']=True
        if local_business_match(title,row.get('region')):
            flags['regional_business']=True
        if flags:
            by_url[row.get('url')]=flags
    return by_url

def _url_domain(url):
    p=urlparse(url)
    if p.scheme not in ('https','http') or not p.hostname:return ''
    return p.hostname.lower().removeprefix('www.')

def index_gdelt(row,mode,group=''):
    """No publisher body, no images, no invented time; links are original URLs."""
    title=re.sub(r'\s+',' ',str(row.get('title') or '')).strip()
    url=str(row.get('url') or '').strip()
    domain=_url_domain(url)
    if not domain or not 12<=len(title)<=300:return None
    if any(domain==blocked or domain.endswith('.'+blocked) for blocked in PAYWALLED):return None
    lang=str(row.get('language') or '').lower()
    if lang and lang not in ('english','en'):return None
    if mode=='pf':
        if not pf_match(title):return None
        region='india'
        sector='Personal Finance'
        desk='personal-finance'
    elif mode=='regional-business':
        region=local_business_match(title)
        if not region:return None
        sector='Other Business'
        desk='regional-business'
    else:
        return None
    return {'id':url,'url':url,'title':title,'source':row.get('domain') or domain,
            'domain':domain,'region':region,'sector':sector,'seen':row.get('seendate') or '',
            'time_basis':'indexed','language':'English','origin':'gdelt-open-index',
            'desk':desk,'sourcecountry':row.get('sourcecountry') or ''}
