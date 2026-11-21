#!/usr/bin/env python3
"""Resilient half-hour source-link refresh.

Fetch desk sources independently, keep the last good JSON when sources fail,
and publish source-attributed links even if optional models/GDELT are unavailable.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

from rss_sources import collect_official
from avi_ivi import collect_avi_ivi
from world_google_news import collect_world
from all_general_news import collect_general_news
from reuters_google_news import collect_reuters
from regional_google_news import collect_regional
from hyderabad_business_news import collect_hyderabad_business, eligible_regional_business, sector as local_business_sector
from hyderabad_real_estate import collect_hyderabad_real_estate
from hyderabad_mail import collect_hyderabad_mail
from pf_google_news import collect_personal_finance
from publications import collect_publications, telugu_region
from desk_coverage import from_telugu_publisher, pf_match

DEST=Path(__file__).resolve().parents[1]/"data"/"news.json"
CUTOFF=datetime(2026,11,13,18,30,tzinfo=timezone.utc)
AVI_START=datetime(2026,11,18,18,30,tzinfo=timezone.utc)
MAX_ARTICLES=16000

def stamp(value):
    try:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError,TypeError,OverflowError):
        return datetime(1970,1,1,tzinfo=timezone.utc)

def collect_desk(name,fn):
    try:
        response=fn()
        if isinstance(response,tuple) and len(response)==2:
            rows,status=response
        else:
            rows,status=response,{"accepted":len(response)}
        if not isinstance(rows,list):raise ValueError("collector did not return a list")
        return name,rows,status,None
    except Exception as exc:
        return name,[],{},type(exc).__name__+": "+str(exc)[:180]

def route_general_business_topic(entry):
    """Make Google News business-topic headlines visible in specialist desks.

    Google News Business & Economy topic stories were once stored as general
    news, then hidden from India News without appearing in India Business.
    These are already publisher-attributed business-topic titles, not guesses.
    """
    if not isinstance(entry,dict):return None
    if entry.get("sector")!="Business & Economy":return None
    if entry.get("desk") not in ("india-general","world-general"):return None
    title=entry.get("title") or ""
    if pf_match(title):
        entry["desk"]="personal-finance"
        entry["sector"]="Personal Finance"
        entry["reader_finance"]=True
        return "personal_finance"
    entry["desk"]="business"
    return "business"

def main():
    old=json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {"articles":[]}
    previous=old.get("articles") if isinstance(old.get("articles"),list) else []
    by_url={row["url"]:row for row in previous if isinstance(row,dict) and isinstance(row.get("url"),str)}
    # Backfill the region on already-indexed Telugu general news, without
    # changing its original time, title or URL or reclassifying India-only news.
    for row in by_url.values():
        if row.get("desk")=="telugu-patrikalu" and row.get("region")=="india":
            tagged=telugu_region(row.get("title",""),row.get("url",""))
            if tagged!="india":row["region"]=tagged
    runners={
        "official":collect_official,
        "avi_ivi":collect_avi_ivi,
        "world_discovery":collect_world,
        "india_world_general":collect_general_news,
        "reuters_discovery":collect_reuters,
        "regional_discovery":collect_regional,
        "hyderabad_business_discovery":collect_hyderabad_business,
        "hyderabad_real_estate_discovery":collect_hyderabad_real_estate,
        "hyderabad_mail_rss":collect_hyderabad_mail,
        "personal_finance_discovery":collect_personal_finance,
        "publications":collect_publications,
    }
    updates={}
    stats={}
    errors={}
    # All desks run independently. One slow/broken feed does not stall the others.
    with ThreadPoolExecutor(max_workers=len(runners)) as pool:
        futures=[pool.submit(collect_desk,key,fn) for key,fn in runners.items()]
        for future in as_completed(futures):
            name,rows,report,error=future.result()
            if error:
                errors[name]=error
                print("Refresh warning:",name,error,flush=True)
                continue
            if name=="publications":
                tags=from_telugu_publisher(rows)
                for item in rows:item.update(tags.get(item.get("url"),{}))
            updates[name]=rows
            stats[name]=report
            print("Refreshed:",name,"rows:",len(rows),flush=True)
    # Rescue Google News Business & Economy headlines from the general topic
    # feed: India News hides these as business, so they must also be routed
    # into business / reader finance instead of becoming invisible.
    routed={"business_new":0,"pf_new":0,"business_archive":0,"pf_archive":0}
    for current in updates.values():
        for row in current:
            decision=route_general_business_topic(row)
            if decision:routed["business_new" if decision=="business" else "pf_new"]+=1
    for row in by_url.values():
        decision=route_general_business_topic(row)
        if decision:routed["business_archive" if decision=="business" else "pf_archive"]+=1
    stats["general_business_routing"]=routed
    # When Google News's narrowly scoped Hyderabad corporate search returns
    # few matches, recover strictly verified business headlines from the wider
    # AP/TG general feed collected in the SAME run. Keep public affairs,
    # politics, crime and everyday local news in their general desks.
    recovered_new=0
    recovered_hyderabad=0
    for row in updates.get("regional_discovery",[]):
        if eligible_regional_business(row):
            row["desk"]="regional-business"
            row["sector"]=local_business_sector(row["title"])
            row["regional_business"]=True
            recovered_new+=1
            if row.get("region")=="hyderabad":recovered_hyderabad+=1
    recovered_archive=0
    for row in by_url.values():
        if eligible_regional_business(row):
            row["desk"]="regional-business"
            row["sector"]=local_business_sector(row["title"])
            row["regional_business"]=True
            recovered_archive+=1
    stats["regional_business_recovery"]={
        "newly_collected":recovered_new,
        "hyderabad_newly_collected":recovered_hyderabad,
        "reclassified_prior":recovered_archive,
        "method":"strict-commercial-titles-from-AP-TG-regional-discovery"
    }
    new_count=0
    for name,rows in updates.items():
        for entry in rows:
            if not isinstance(entry,dict):continue
            url=entry.get("url")
            if not isinstance(url,str) or not url.startswith(("https://","http://")):continue
            if not entry.get("title"):continue
            if name=="official" and pf_match(entry["title"]):
                entry["reader_finance"]=True
            prior=by_url.get(url)
            # Retain a verified local real-estate classification when the same
            # Google News URL is rediscovered by another general/business desk.
            if prior and prior.get("real_estate_kind") and not entry.get("real_estate_kind"):
                for key in ("sector","desk","region","real_estate_kind","regional_business"):
                    if key in prior:entry[key]=prior[key]
            if prior:
                # Never let an all-topic general index steal an item from an
                # existing specialist desk (PF, AP/TG, Avii Ivii, business).
                general_desks=("india-general","world-general")
                prior_desk=prior.get("desk") or "business"
                incoming_desk=entry.get("desk") or "business"
                if incoming_desk=="business" and prior_desk=="regional-business":
                    for field in ("desk","region","sector","regional_business","real_estate_kind"):
                        if field in prior:entry[field]=prior[field]
                if incoming_desk in general_desks and prior_desk not in general_desks:
                    for field in ("desk","region","sector","source","origin","regional_business","reader_finance","listed_company"):
                        if field in prior:entry[field]=prior[field]
                if entry.get("time_basis")=="first_seen":
                    entry["seen"]=prior.get("seen") or entry.get("seen")
                if entry.get("time_basis")!="feed" and prior.get("time_basis")=="feed":
                    entry["seen"]=prior.get("seen") or entry.get("seen")
                    entry["time_basis"]="feed"
                for key in ("title_te","snippet_te","snippet_en","snippet_basis","summary","regional_business","reader_finance","listed_company","real_estate_kind"):
                    if not entry.get(key) and prior.get(key):entry[key]=prior[key]
            if not prior or stamp(entry.get("seen"))>=stamp(prior.get("seen")):
                if not prior:new_count+=1
                by_url[url]=entry
    # Verified 19-Nov Hyderabad pharma agreement: retain the original publisher link
    # even if Google News does not index the story. Time is first-observed, NOT
    # the original publication time.
    biosol_url="https://www.businessbriefingtoday.com/health/be-biosol-and-gates-foundation-collaborate-to-expand-access-to-ferric-carboxymaltose-injection"
    if biosol_url not in by_url:
        by_url[biosol_url]={
            "id":biosol_url,"url":biosol_url,
            "title":"BE Biosol and Gates Foundation collaborate to expand access to ferric carboxymaltose injection",
            "source":"Business Briefing Today","domain":"businessbriefingtoday.com",
            "region":"hyderabad","sector":"Pharma & Life Sciences",
            "desk":"regional-business","regional_business":True,"listed_company":False,
            "seen":datetime.now(timezone.utc).isoformat(),"time_basis":"first_seen",
            "sourcecountry":"India","language":"English","origin":"verified-source-link",
            "summary":"Hyderabad-based BE Biosol Private Limited signed a collaboration with the Gates Foundation to develop and expand access to ferric carboxymaltose injection."
        }
        new_count+=1
    now=datetime.now(timezone.utc)
    rows=[v for v in by_url.values() if (
        stamp(v.get("seen"))>=CUTOFF
        or (v.get("desk")=="telugu-patrikalu" and stamp(v.get("seen"))>=now-timedelta(days=30))
    ) and (v.get("desk")!="avi-ivi" or stamp(v.get("seen"))>=AVI_START)]
    rows.sort(key=lambda v:stamp(v.get("seen")),reverse=True)
    # Preserve quotas so a large national feed cannot displace local or PF news.
    quotas={"business":12000,"personal-finance":12000,"india-general":12000,"world-general":12000,"regional-business":2000,
            "regional-general":12000,"avi-ivi":12000,"english-magazines":12000,
            "telugu-patrikalu":1500}
    desk_counts={}
    kept=[]
    for item in rows:
        desk=item.get("desk") or "business"
        if desk_counts.get(desk,0)>=quotas.get(desk,2000):continue
        desk_counts[desk]=desk_counts.get(desk,0)+1
        kept.append(item)
        if len(kept)>=MAX_ARTICLES:break
    # If every source fails, keep the old timestamp and content; never fake freshness.
    any_success=bool(updates)
    source_status=dict(old.get("source_status") or {})
    source_status.update(stats)
    source_status["quick_refresh"]={
       "checked_at":now.isoformat(),"successful_desks":list(updates),
       "failed_desks":errors,"new_links":new_count,"articles":len(kept)
    }
    payload=dict(old)
    payload.update({
        "generated_at":now.isoformat() if any_success else old.get("generated_at"),
        "articles":kept if any_success else previous,
        "source_status":source_status,
    })
    if not any_success:
        print("No collection succeeded; leaving original news.json unchanged",flush=True)
        return
    # Atomic replacement: GitHub job can publish a complete file only.
    DEST.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(mode="w",encoding="utf-8",dir=DEST.parent,delete=False) as output:
        json.dump(payload,output,ensure_ascii=False,separators=(",",":"))
        temp=Path(output.name)
    os.replace(temp,DEST)
    print("Updated",len(kept),"headlines; new:",new_count,"generated:",payload["generated_at"],flush=True)

if __name__=="__main__":main()
