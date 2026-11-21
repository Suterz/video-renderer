"""Append-only one-submit harness; a lost POST acknowledgement is not retried."""
import argparse
import hashlib
import json
import time
import subprocess
from pathlib import Path

import httpx
from corpus import HERE, compile_case, read_cases

TERMINAL = {"succeeded","needs_review","failed","interrupted"}


def write(path, data):
    out = path.with_suffix(".tmp")
    out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    out.replace(path)


def append(path,data):
    with path.open("a") as stream:
        stream.write(json.dumps(data,ensure_ascii=False)+"\n")
        stream.flush()


def commit(path):
    return subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],text=True).strip()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--file",type=Path,action="append")
    p.add_argument("--frozen",type=Path,help="Directory of sealed HXX/request.json + oracle.json pairs")
    p.add_argument("--id",action="append")
    p.add_argument("--mode",choices=["v2","v3"],required=True)
    p.add_argument("--url",required=True)
    p.add_argument("--frames",type=Path,required=True,help="Frame source worktree")
    p.add_argument("--video",type=Path,required=True,help="Video source worktree")
    p.add_argument("--jobs",type=Path,required=True,help="Video job root behind the public endpoint")
    p.add_argument("--frames-store",type=Path,required=True)
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    if a.frozen:
        if a.mode!="v3" or a.file or a.id:
            raise SystemExit("sealed evaluation requires the full unfiltered v3 set")
        cases={d.name:d for d in a.frozen.glob("H[0-9][0-9]") if d.is_dir()}
        if len(cases)!=10:
            raise SystemExit("10 sealed cases required")
    else:
        cases=read_cases(*(a.file or [HERE/"first.tsv",HERE/"development.tsv"]))
    ids=a.id or sorted(cases)
    a.root.mkdir(parents=True,exist_ok=True)
    ledger=a.root/"ledger.jsonl"
    pair={"frames":commit(a.frames),"video":commit(a.video),
          "harness":commit(HERE),"mode":a.mode,"endpoint":a.url,"frame_store":str(a.frames_store),"job_store":str(a.jobs)}
    if a.frozen:
        pair["sealed"]=commit(a.frozen)
    if (a.root/"config.json").exists():
        previous=json.loads((a.root/"config.json").read_text())
        if {k:v for k,v in previous.items() if k!="harness"} != {k:v for k,v in pair.items() if k!="harness"}:
            raise SystemExit("refusing to mix runtime commits or stores")
    else:
        write(a.root/"config.json",pair)
    with httpx.Client(base_url=a.url,timeout=25) as client:
        client.get("/ready").raise_for_status()
        for id in ids:
            out=a.root/id
            out.mkdir(exist_ok=True)
            if (out/"outcome.json").exists():
                continue
            start=time.monotonic()
            if a.frozen:
                payload=(cases[id]/"request.json").read_bytes()
                req=json.loads(payload)
                spec=json.loads((cases[id]/"oracle.json").read_bytes())
                if req.get("reuse_visuals_from") or req.get("reuse_recording_from"):
                    raise SystemExit(f"{id}: fixture-specific reuse is not allowed")
            else:
                req,spec=compile_case(cases[id],a.mode)
                payload=json.dumps(req,ensure_ascii=False,separators=(",",":")).encode()
            if not (out/"submission.json").exists():
                (out/"request.json").write_bytes(payload)
                write(out/"oracle.json",spec)
                submission={"state":"posting","request_sha256":hashlib.sha256(payload).hexdigest(),"pair":pair,"submitted":time.time()}
                write(out/"submission.json",submission)
                try:
                    response=client.post("/v2/renders",content=payload,headers={"Content-Type":"application/json"})
                    body=response.json()
                    submission.update(state="submitted" if response.status_code==202 else "rejected",http=response.status_code,response=body)
                except Exception as e:
                    submission.update(state="lost_acknowledgement",error=str(e))
                write(out/"submission.json",submission)
                append(ledger,{"id":id,"event":"submit",**submission})
            else:
                submission=json.loads((out/"submission.json").read_text())
            if submission["state"]!="submitted":
                # A durable posting record still requires manual reconciliation, never another POST.
                outcome={"id":id,"service_state":submission["state"],"judgment":"operational_failure","submission":submission}
            else:
                job=submission["response"]["id"]; deadline=time.monotonic()+1500; body={}
                while time.monotonic()<deadline:
                    try:
                        r=client.get(f"/v2/renders/{job}")
                        r.raise_for_status()
                        body=r.json()
                    except (httpx.HTTPError,ValueError):
                        time.sleep(2)
                        continue
                    if body.get("state") in TERMINAL:
                        break
                    time.sleep(2)
                service=body.get("state","timeout")
                judgment={"succeeded":"pending_checks","needs_review":"safe_refusal"}.get(service,"operational_failure")
                outcome={"id":id,"job_id":job,"service_state":service,"judgment":judgment,"status":body,
                         "job_dir":str(a.jobs/job),"seconds":round(time.time()-submission["submitted"],3)}
                if service=="succeeded":
                    r=client.get(f"/v2/renders/{job}/video")
                    r.raise_for_status()
                    outcome["download_sha256"]=hashlib.sha256(r.content).hexdigest()
                    if outcome["download_sha256"]!=hashlib.file_digest((a.jobs/job/"video.mp4").open("rb"),"sha256").hexdigest():
                        outcome["judgment"]="operational_failure"
            write(out/"outcome.json",outcome)
            append(ledger,{"event":"outcome",**outcome})
            print(id,outcome["service_state"],outcome["judgment"],round(time.monotonic()-start,1),flush=True)


if __name__=="__main__":
    main()
