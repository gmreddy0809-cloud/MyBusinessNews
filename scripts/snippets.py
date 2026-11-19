#!/usr/bin/env python3
"""Optional source-grounded Telugu headline/snippet enrichment.

Requires OPENAI_API_KEY as a GitHub Actions secret. No publisher body scraping.
A title alone cannot substantiate additional facts: the model must not invent any.
Failures leave original titles/links intact; never fabricate Telugu excerpts.
"""
import json, os, re, sys, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API="https://api.openai.com/v1/chat/completions"
MODEL=os.getenv("MBN_SNIPPET_MODEL","gpt-4.1-mini")
MAX_NEW=int(os.getenv("MBN_SNIPPETS_PER_RUN","45"))
TELUGU=re.compile(r"[\u0c00-\u0c7f]")
def valid(s):
    return isinstance(s,str) and 8<=len(s)<=500 and bool(TELUGU.search(s))
def missing(item):
    return not valid(item.get("title_te")) or not valid(item.get("snippet_te"))
def prompt_batch(batch, key):
    request_body={
        "model":MODEL,
        "temperature":0,
        "response_format":{"type":"json_object"},
        "messages":[
          {"role":"system","content":(
             "You are an accurate Telugu business and personal-finance newsroom editor. "
             "Return JSON object with key 'items', a list of objects with keys 'id','title_te','snippet_te'. "
             "Use fluent, concise Eenadu-style Telugu, no untranslated English sentence. "
             "Each snippet should be 2 short Telugu sentences, displayed across 2–3 lines. "
             "ONLY restate facts explicitly in the provided title or licensed/official summary. "
             "If only title is provided, explain the headline meaning without adding figures, "
             "causes, quotes, implications or outcomes not already in the title. "
             "No claims of verification, no editorial opinion, no financial advice. "
             "Keep numerical figures exactly as supplied, and retain proper nouns. "
             "Do not mention an article's precise publication date unless it is in the input. "
             "Return one object per input id. For an insufficient or unclear headline, return empty strings."
          )},
          {"role":"user","content":json.dumps({"items":batch},ensure_ascii=False)}
        ]
    }
    payload=json.dumps(request_body,ensure_ascii=False).encode()
    req=Request(API,data=payload,method="POST",headers={
        "Authorization":"Bearer "+key,"Content-Type":"application/json",
        "User-Agent":"MyBusinessNews/1.0"
    })
    with urlopen(req,timeout=50) as resp:
        output=json.loads(resp.read(350000).decode())
    data=json.loads(output["choices"][0]["message"]["content"])
    return data.get("items",[])
def enrich(rows):
    key=os.getenv("OPENAI_API_KEY","").strip()
    stats={"configured":bool(key),"attempted":0,"completed":0,"pending":0,"errors":[]}
    if not key:
        stats["pending"]=sum(missing(x) for x in rows)
        return stats
    pending=[x for x in rows if missing(x)]
    # Prioritize missing current content, and preserve earlier translations.
    pending.sort(key=lambda x:x.get("seen",""),reverse=True)
    for offset in range(0,min(len(pending),MAX_NEW),10):
        chosen=pending[offset:offset+10]
        batch=[{"id":str(i),"title":x["title"][:260],
                "summary":x.get("summary","")[:450] if x.get("origin")=="official-rss" else ""}
               for i,x in enumerate(chosen)]
        stats["attempted"]+=len(chosen)
        try:
            answer=prompt_batch(batch,key)
            mapped={str(x.get("id")):x for x in answer if isinstance(x,dict)}
            for idx,item in enumerate(chosen):
                result=mapped.get(str(idx),{})
                title=result.get("title_te","")
                excerpt=result.get("snippet_te","")
                if valid(title) and valid(excerpt):
                    item["title_te"]=title.strip()[:220]
                    item["snippet_te"]=excerpt.strip()[:500]
                    item["snippet_basis"]="title-and-official-summary" if batch[idx]["summary"] else "headline-only"
                    stats["completed"]+=1
        except (ValueError,KeyError,HTTPError,TimeoutError,OSError) as exc:
            stats["errors"].append(type(exc).__name__+": "+str(exc)[:100])
            print("Telugu snippet generation warning:",type(exc).__name__,str(exc)[:100],file=sys.stderr)
            if isinstance(exc,HTTPError) and exc.code in (401,403,429):
                break
        time.sleep(0.3)
    stats["pending"]=sum(missing(x) for x in rows)
    return stats
