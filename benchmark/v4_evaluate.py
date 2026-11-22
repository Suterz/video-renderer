"""Independent raster adjudication plus an audit across failed and accepted panels."""
import json
from pathlib import Path
import sys
from collections import Counter
import math,statistics

sys.path.insert(0,str(Path(__file__).parent/"v3"))
import judge


def read(p):
    return json.loads(p.read_text()) if p.is_file() else {}


def audit(config,item):
    job=Path(item["job_dir"]) if item.get("job_dir") else None
    if not job:
        return {"frame_attempt_records":0,"repair_samples_complete":False}
    entries=read(job/"panels.partial.json")
    manifest=read(job/"panels.json")
    session=entries.get("session_id") or manifest.get("session_id")
    if not session:
        # On a frame rejection before the first completed frame, the exact
        # provider URL is in the terminal diagnostic.
        import re
        m=re.search(r"/v2/sessions/([a-f0-9]{32})/panels/",item.get("status",{}).get("error",""))
        session=m.group(1) if m else None
    if not session:
        return {"frame_attempt_records":0,"repair_samples_complete":False}
    base=Path(config["frame_store"])/"sessions"/session/"panels"
    reviews=[]
    for path in sorted(base.glob("*/review.json")):
        d=read(path);reviews.append({"panel":path.parent.name,"attempts":[{k:a[k] for k in ("attempt","outcome","stage","defect","repair_action") if k in a}
                  for a in d.get("attempts",[])],"review_file":str(path)})
    repair=sum(max(0,len(r["attempts"])-1) for r in reviews)
    return {"frame_attempt_records":sum(len(r["attempts"]) for r in reviews),"observed_repairs":repair,
            "repair_samples_complete":bool(reviews) and all(a.get("outcome") in {"accepted","rejected","failed"} for r in reviews for a in r["attempts"]),
            "trails":reviews}


def main(root):
    c=read(root/"config.json")
    if not c:
        return
    rows=[]
    for p in sorted(root.glob("*/outcome.json")):
        row=read(p)
        target=p.with_name("evaluation.json")
        manual=p.with_name("inspection.json")
        if not target.exists() or (manual.exists() and manual.stat().st_mtime>target.stat().st_mtime):
            try:
                result,evidence=judge.evaluate(p.parent,c)
            except Exception as e:
                result,evidence="unjudged",{"evaluation_error":str(e)}
            row.update(judgment=result,**evidence,repair_audit=audit(c,row))
            temp=target.with_suffix(".tmp")
            temp.write_text(json.dumps(row,ensure_ascii=False,indent=2))
            temp.replace(target)
        else:
            row=read(target)
        rows.append(row)
    n=len(c["case_ids"]);states=Counter(r["judgment"] for r in rows)
    values=sorted(x["seconds"] for x in rows if "seconds" in x)
    delivered=[r for r in rows if r["service_state"]=="succeeded"]
    correct=[r for r in rows if r["judgment"]=="verified_pass"]
    first=sum(r.get("first_candidate",False) for r in correct)
    s=[f"# {root.name}",f"Frames `{c['frames']}` / Video `{c['video']}`",f"Sealed `{c['sealed']}`","",
       f"Terminal: {len(rows)}/{n}. Verified one-shot: {len(correct)}/{n}. First-candidate: {first}. "
       f"Correct among returned videos: {len(correct)}/{len(delivered)}. Unjudged is not pass.",
       f"Outcomes: {dict(states)}."]
    if values:s.append(f"Wall p50 / p95 = {statistics.median(values):.1f} / {values[math.ceil(.95*len(values))-1]:.1f} s (n={len(values)}).")
    s+=["","| Case | First service outcome | Independent verdict | Observed repairs | Evidence |","|---|---|---|---:|---|"]
    for key in c["case_ids"]:
        r=next((x for x in rows if x["id"]==key),None)
        if not r:
            s.append(f"| {key} | pending | — | — | — |");continue
        repairs=r.get("repair_audit",{}).get("observed_repairs","unknown")
        media=f' · [MP4]({r["job_dir"]}/video.mp4)' if r["service_state"]=="succeeded" else ""
        s.append(f"| {key} | {r['service_state']} | {r['judgment']} | {repairs} | [evidence]({key}/evaluation.json){media} |")
    temp=root/"INDEX.tmp"
    temp.write_text("\n".join(s)+"\n")
    temp.replace(root/"INDEX.md")


if __name__=="__main__":
    main(Path(sys.argv[1]))
