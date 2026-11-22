"""Durable scored submission harness; resume reconciles via GET, not POST."""
from pathlib import Path
import argparse, json, hashlib, os, sys, time, subprocess
import httpx

from v4_prepare import prepare,read_cases

TERMINAL={"succeeded","failed","interrupted","needs_review"}


def write(p,x):
    t=p.with_suffix(".tmp")
    with t.open("w") as f:
        json.dump(x,f,ensure_ascii=False,indent=2)
        f.flush();os.fsync(f.fileno())
    t.replace(p)
    fd=os.open(p.parent,os.O_RDONLY)
    os.fsync(fd);os.close(fd)


def git(path):
    return subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],text=True).strip()


def main(a):
    loc=Path(__file__).parent
    if a.sealed:
        if a.id:
            raise SystemExit("sealed evaluation must include every case")
        specs={p.name:((p/"request.json").read_bytes(),json.loads((p/"oracle.json").read_text())) for p in a.sealed.glob("H[0-9][0-9]")}
        if len(specs)!=10:
            raise SystemExit("ten sealed cases required")
        seal=git(a.sealed)
    else:
        rows=read_cases(loc/"v3/first.tsv",loc/"v3/development.tsv")
        for extra in ("v4-author-revisions.tsv","v4-clarity.tsv","v4-latest.tsv"):
            if (loc/extra).is_file():
                rows.update(read_cases(loc/extra))
        specs={}
        for k,v in rows.items():
            req,oracle=prepare(v)
            specs[k]=(json.dumps(req,sort_keys=True,ensure_ascii=False).encode(),oracle)
        seal=None
    ids=a.id or sorted(specs)
    a.out.mkdir(parents=True,exist_ok=True)
    conf={"frames":git(a.frames),"video":git(a.video),"harness":git(loc),"sealed":seal,"mode":"v3",
          "endpoint":a.url,"job_store":str(a.jobs),"frame_store":str(a.frame_store),"case_ids":ids}
    config=a.out/"config.json"
    if config.exists():
        if conf!=json.loads(config.read_text()):
            raise SystemExit("refusing a different commit pair or case list on resume")
    else:
        write(config,conf)
    with httpx.Client(base_url=a.url,timeout=25) as h:
        h.get("/ready").raise_for_status()
        for k in ids:
            d=a.out/k
            d.mkdir(exist_ok=True)
            outcome=d/"outcome.json"
            if outcome.exists():
                continue
            payload,oracle=specs[k]
            key="v4-"+hashlib.sha256(f"{a.out.resolve()}:{k}".encode()).hexdigest()
            submission=d/"submission.json"
            init=None
            if not submission.exists():
                (d/"request.json").write_bytes(payload)
                write(d/"oracle.json",oracle)
                launch={"idempotency_key":key,"request_sha256":hashlib.sha256(payload).hexdigest(),"submitted":time.time()}
                write(submission,launch)
                try:
                    r=h.post("/v2/renders",content=payload,headers={"Content-Type":"application/json","Idempotency-Key":key})
                    init=r.json()
                    launch.update(http=r.status_code,response=init)
                except (httpx.HTTPError,ValueError) as e:
                    launch["transport"]=str(e)
                write(submission,launch)
            launch=json.loads(submission.read_text())
            init=launch.get("response")
            if launch.get("http") not in (None,202):
                final={"id":k,"service_state":"invalid","judgment":"operational_failure","status":init}
            else:
                if not (init and init.get("id")):
                    # Crash before/after POST is ambiguous. A GET can prove a job exists;
                    # a miss is retained as failure and NEVER triggers a second submission.
                    try:
                        r=h.get("/v2/submissions/"+key)
                        init=r.json() if r.status_code==200 else None
                    except httpx.HTTPError:
                        init=None
                if not init:
                    final={"id":k,"service_state":"lost_acknowledgement","judgment":"operational_failure"}
                else:
                    j=init["id"];end=time.monotonic()+1600
                    result=init
                    while time.monotonic()<end and result.get("state") not in TERMINAL:
                        try:
                            res=h.get(f"/v2/renders/{j}")
                            if res.status_code==200:
                                result=res.json()
                        except httpx.HTTPError:
                            pass
                        if result.get("state") not in TERMINAL:
                            time.sleep(2)
                    state=result.get("state")
                    final={"id":k,"job_id":j,"service_state":state if state in TERMINAL else "timeout","status":result,
                          "job_dir":str(a.jobs/j),"seconds":round(time.time()-launch["submitted"],3),
                          "judgment":{"succeeded":"pending_checks","needs_review":"safe_refusal"}.get(state,"operational_failure")}
                    if state=="succeeded":
                        response=h.get(f"/v2/renders/{j}/video")
                        response.raise_for_status()
                        final["download_sha256"]=hashlib.sha256(response.content).hexdigest()
            write(outcome,final)
            print(k,final["service_state"],final["judgment"],final.get("seconds"),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("frames","video","out","jobs","frame-store"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--url",required=True)
    p.add_argument("--id",action="append")
    p.add_argument("--sealed",type=Path)
    main(p.parse_args())
