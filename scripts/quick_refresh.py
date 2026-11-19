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
from regional_google_news import collect_regional
from hyderabad_business_news import collect_hyderabad_business
from pf_google_news import collect_personal_finance
from publications import collect_publications
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

def main():
    old=json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {"articles":[]}
    previous=old.get("articles") if isinstance(old.get("articles"),list) else []
    by_url={row["url"]:row for row in previous if isinstance(row,dict) and isinstance(row.get("url"),str)}
    runners={
        "official":collect_official,
        "avi_ivi":collect_avi_ivi,
        "world_discovery":collect_world,
        "regional_discovery":collect_regional,
        "hyderabad_business_discovery":collect_hyderabad_business,
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
            if prior:
                if entry.get("time_basis")=="first_seen":
                    entry["seen"]=prior.get("seen") or entry.get("seen")
                if entry.get("time_basis")!="feed" and prior.get("time_basis")=="feed":
                    entry["seen"]=prior.get("seen") or entry.get("seen")
                    entry["time_basis"]="feed"
                for key in ("title_te","snippet_te","snippet_en","snippet_basis","summary","regional_business","reader_finance"):
                    if not entry.get(key) and prior.get(key):entry[key]=prior[key]
            if not prior or stamp(entry.get("seen"))>=stamp(prior.get("seen")):
                if not prior:new_count+=1
                by_url[url]=entry
    now=datetime.now(timezone.utc)
    rows=[v for v in by_url.values() if (
        stamp(v.get("seen"))>=CUTOFF
        or (v.get("desk")=="telugu-patrikalu" and stamp(v.get("seen"))>=now-timedelta(days=30))
    ) and (v.get("desk")!="avi-ivi" or stamp(v.get("seen"))>=AVI_START)]
    rows.sort(key=lambda v:stamp(v.get("seen")),reverse=True)
    # Preserve quotas so a large national feed cannot displace local or PF news.
    quotas={"business":12000,"personal-finance":12000,"regional-business":2000,
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
