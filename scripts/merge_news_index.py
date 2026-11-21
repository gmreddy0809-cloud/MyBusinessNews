#!/usr/bin/env python3
"""Merge two independently collected indices safely before publishing.

GitHub Actions can finish out of order. A slower older run must never
replace a newer news.json snapshot or silently remove saved headlines.
"""
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

def dt(value):
    try:
        result=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError,OverflowError):
        return datetime(1970,1,1,tzinfo=timezone.utc)

def merge(current,candidate):
    old=current.get("articles") or []
    new=candidate.get("articles") or []
    by_url={}
    for item in old:
        if isinstance(item,dict) and isinstance(item.get("url"),str):
            by_url[item["url"]]=dict(item)
    for item in new:
        if not isinstance(item,dict) or not isinstance(item.get("url"),str):continue
        old_item=by_url.get(item["url"])
        if not old_item:
            by_url[item["url"]]=dict(item)
            continue
        if dt(item.get("seen"))>=dt(old_item.get("seen")):
            winner,loser=dict(item),old_item
        else:
            winner,loser=dict(old_item),item
        winner_had_realty=bool(winner.get("real_estate_kind"))
        for key in ("title_te","snippet_te","snippet_en","summary","snippet_basis","reader_finance","regional_business","listed_company","real_estate_kind"):
            if not winner.get(key) and loser.get(key):
                winner[key]=loser[key]
        # Specialist news desks must survive collisions with broad general
        # indexing of the same source headline.
        general_desks=("india-general","world-general")
        if winner.get("desk") in general_desks and loser.get("desk") not in general_desks:
            for key in ("desk","region","sector","source","origin","regional_business","reader_finance","listed_company"):
                if key in loser:winner[key]=loser[key]
        if loser.get("real_estate_kind") and not winner_had_realty:
            for key in ("sector","desk","region","real_estate_kind","regional_business"):
                if key in loser:winner[key]=loser[key]
        if winner.get("real_estate_kind"):
            winner["sector"]="Real Estate"
        by_url[item["url"]]=winner
    latest=candidate if dt(candidate.get("generated_at"))>=dt(current.get("generated_at")) else current
    result=dict(latest)
    result["articles"]=sorted(by_url.values(),key=lambda item:dt(item.get("seen")),reverse=True)[:16000]
    result["generated_at"]=max(
        (current.get("generated_at"),candidate.get("generated_at")),
        key=dt
    )
    return result

def main():
    newest=Path(sys.argv[1])
    candidate=Path(sys.argv[2])
    current=json.loads(newest.read_text(encoding="utf-8"))
    incoming=json.loads(candidate.read_text(encoding="utf-8"))
    output=merge(current,incoming)
    candidate.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("Merged original",len(current.get("articles",[])),
          "candidate",len(incoming.get("articles",[])),
          "published",len(output["articles"]),
          "generated_at",output["generated_at"],flush=True)

if __name__=="__main__":main()
