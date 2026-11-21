"""External raster/encoding checks plus evidence-aware human/model status.

No automatic pass when meaning, OCR, or continuity is unverified.
"""
import argparse
from collections import Counter, defaultdict
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import wave

from PIL import Image, ImageChops, ImageDraw

from corpus import FAMILIES

HOME=Path.home()
FF=HOME/"ai/tools/media/bin/ffmpeg"
OCR=HOME/"ai/storyboard-build/v3/ocr"
PALETTES=[{"ink":(72,37,54),"accent":(191,77,49),"pale":(244,221,172)},
          {"ink":(23,53,85),"accent":(183,70,54),"pale":(189,219,234)}]
W,H=360,640


def read(p):
    return json.loads(p.read_text())


def dump(p, data):
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")


def inspect_video(path, indices):
    ns=sorted(set(indices))
    expr="+".join(f"eq(n\\,{n})" for n in ns)
    result=subprocess.check_output([str(FF),"-v","error","-i",str(path),"-an","-vf",f"select={expr},scale={W}:{H}",
                                    "-fps_mode","passthrough","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],timeout=75)
    stride=W*H*3
    if len(result)!=len(ns)*stride:
        raise RuntimeError("encoded frame selection incomplete")
    return {n:Image.frombytes("RGB",(W,H),result[i*stride:(i+1)*stride]) for i,n in enumerate(ns)}


def xy(loc):
    return round(loc[0]*W),round(loc[1]*H)


def close(pixel,guess,tolerance=34):
    return sum(abs(a-b) for a,b in zip(pixel,guess)) <= tolerance


def label_text(im,mark):
    cmd=OCR/"usr/bin/tesseract"
    if not cmd.is_file():
        return None
    x,y=xy(mark["at"])
    # Crop the declared text band, not the model output's location.
    dx=min(165, max(44, round(len(mark["text"])*5.4+16)))
    box=(max(0,x-dx),max(0,y-18),min(W,x+dx),min(H,y+18))
    data=BytesIO()
    im.crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3)).save(data,format="PNG")
    env={**os.environ,"LD_LIBRARY_PATH":str(OCR/"usr/lib/x86_64-linux-gnu")}
    result=subprocess.run([str(cmd),"stdin","stdout","--tessdata-dir",str(OCR/"usr/share/tesseract-ocr/5/tessdata"),
                           "--psm","7"],input=data.getvalue(),capture_output=True,env=env,timeout=8)
    return result.stdout.decode().strip() if result.returncode==0 else None


def normalize(text):
    # Currency, decimal point and comparison operators are not interchangeable.
    return "".join(c for c in text.upper() if c.isalnum() or c in ".$¢°²÷×−<>=")


def compare(im, mark, anchors, theme, mode):
    k=mark["kind"]
    if k=="label":
        got=label_text(im,mark)
        valid=bool(got and normalize(mark["text"]) in normalize(got))
        return {**mark,"ocr":got,"result":"match" if valid else "unjudged"}
    def point(at):
        if isinstance(at,str):
            return xy([anchors[at]["point"][0]/1080,anchors[at]["point"][1]/1920])
        return xy(at)
    pal=PALETTES[theme]
    if k=="counter":
        x,y=point(mark["at"])
        if mode=="v3":
            rr=mark["diameter"]*W/2
            mid=close(im.getpixel((x,y)),pal["accent"])
            left=close(im.getpixel((round(x-rr*.7),y)),pal["accent"])
            right=close(im.getpixel((round(x+rr*.7),y)),pal["accent"])
            return {**mark,"result":"match" if mid and left and right else "failed"}
        # V2 uses rings; check the actual raster for the rim.
        samples=[im.getpixel((x+dx,y+dy)) for dx in range(-9,10) for dy in range(-9,10)
                 if 25<=dx*dx+dy*dy<=100 and 0<=x+dx<W and 0<=y+dy<H]
        seen=sum(close(v,(246,185,64),85) for v in samples)>7
        return {**mark,"result":"match" if seen else "unjudged"}
    if k=="fruit":
        x,y=point(mark["at"])
        count=sum(r>150 and 50<g<200 and b<155 and r-g>32 for r,g,b in im.crop((x-16,y-16,x+16,y+16)).getdata())
        return {**mark,"visible_orange_pixels":count,"result":"match" if count>=42 else "unjudged"}
    if k=="rect":
        if mode=="v2":
            return {**mark,"result":"failed","reason":"v2 shows a thin arrow where the teaching mechanism requires a filled region"}
        x0,y0,x1,y1=mark["bounds"]
        probes=[xy([x0+(x1-x0)*i/10,y0+(y1-y0)*j/10]) for i in range(1,10) for j in range(1,10)]
        count=sum(close(im.getpixel(p),pal[mark["ink"]],58) for p in probes)
        # Some regions are deliberately partially filled by a later rectangle.
        return {**mark,"matched_probes":count,"result":"match" if count>=72 else "unjudged"}
    if k in ("segment","arrow"):
        try:
            a,b=point(mark["from"]),point(mark["to"])
        except KeyError:
            return {**mark,"result":"failed","reason":"named endpoint absent"}
        if k=="segment" and mode=="v2":
            return {**mark,"result":"failed","reason":"v2 encoded a directed arrow rather than the required undirected segment/ticked scale"}
        color=(246,185,64) if k=="arrow" else pal["ink"]
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=max(1,math.hypot(dx,dy))
        center=lambda x,y:any(close(im.getpixel((xx,yy)),color,105) for yy in range(max(0,y-2),min(H,y+3))
                              for xx in range(max(0,x-2),min(W,x+3)))
        hits=sum(center(round(a[0]+i*dx/20),round(a[1]+i*dy/20)) for i in range(1,20))
        tick_hits=None
        if mark.get("divisions"):
            n=mark["divisions"]
            hits2=lambda i: (center(round(a[0]+i*dx/n-4*dy/length),round(a[1]+i*dy/n+4*dx/length))
                            and center(round(a[0]+i*dx/n+4*dy/length),round(a[1]+i*dy/n-4*dx/length)))
            tick_hits=sum(hits2(i) for i in range(n+1))
        good=hits>=17 and (tick_hits is None or tick_hits==mark["divisions"]+1)
        return {**mark,"path_samples":hits,"tick_samples":tick_hits,"result":"match" if good else "unjudged"}
    raise ValueError(k)


def evaluate(case,config):
    outcome=read(case/"outcome.json")
    if outcome["service_state"]!="succeeded":
        return outcome["judgment"],{}
    req=read(case/"request.json")
    spec=read(case/"oracle.json")
    job=Path(outcome["job_dir"])
    manifest=read(job/"manifest.json")
    fps=req["fps"] if "fps" in req else 30
    end=manifest["verification"]["expected_video_frames"]-1
    cuts=[b["frame"] for b in manifest["beats"]]
    d=inspect_video(job/"video.mp4",[0,end,*cuts,*[c-1 for c in cuts[1:]]])
    preview=Image.new("RGB",(W*len(d),H+28),"#182739")
    for i,(n,im) in enumerate(d.items()):
        preview.paste(im,(i*W,28))
        ImageDraw.Draw(preview).text((i*W+8,7),f"{n} / {n/fps:.2f}s",fill="white")
    preview.save(case/"decoded-contact.png")
    d[0].save(case/"opening-phone.png")
    errors=[]
    duration=float(manifest["verification"]["ffprobe"]["format"]["duration"])
    if not 0<duration<45:
        errors.append("encoded duration outside strict limit")
    recording=job/"narration.wav"
    if not recording.is_file():
        errors.append("missing actual PCM")
    else:
        with wave.open(str(recording),"rb") as f:
            raw=f.readframes(f.getnframes())
        from array import array
        samples=array("h",raw)
        if not any(samples):
            errors.append("silent narration")
        clipped=sum(v in (-32768,32767) for v in samples)
        if clipped>len(samples)*.001:
            errors.append("clipped more than 0.1% of speech samples")
    request_pause=req["script"][1]["pause_after_ms"]
    aligned=manifest["aligned"]
    question_n=sum(len(re.findall(r"[\w]+",u["text"])) for u in req["script"][:2])
    if question_n <= len(aligned):
        qend=aligned[question_n-1]["end"]
        observed=cuts[1]/fps-qend
        # 80 ms covers aligner's native timestamp quantization and frame rounding.
        if observed < (request_pause/1000)-.08:
            errors.append(f"clear prediction hold too short ({observed:.2f}s)")
    else:
        observed=None
    traces=[]
    for a,b in zip(cuts[1:],cuts):
        g=ImageChops.difference(d[a],d[a-1]).crop((0,0,W,540)).getbbox()
        if g is None:
            errors.append(f"no image change at encoded reveal frame {a}")
    checks=[]
    for j,(marks,n) in enumerate(zip(spec["stage"],[0,*cuts[1:-1],end],strict=True)):
        entry=manifest["panels"][j]
        panel=Path(config["frame_store"])/"sessions"/manifest["session_id"]/"panels"/entry["panel_id"]
        trace=read(panel/"review.json")
        traces.append(trace)
        media=d[n]
        checks.extend({"stage":j,"frame":n,**compare(media,m,trace["anchors"],spec["theme"],spec["mode"])} for m in marks)
    if any(x["result"]=="failed" for x in checks):
        errors.append("required raster/geometry check failed")
    if any(x["result"]=="unjudged" for x in checks) or spec["art_continuity_requires_review"] or observed is None:
        judgment="unjudged"
    else:
        # A correct bitmap is not a full semantic review of mechanism, opacity,
        # association and pre-reveal answer leakage.
        judgment="unjudged"
    if errors:
        judgment="false_accept"
    note=case/"inspection.json"
    if note.is_file():
        inspector=read(note)
        if inspector["judgment"]=="false_accept":
            errors+=inspector["reasons"]
            judgment="false_accept"
        elif inspector["judgment"]=="verified_pass" and not errors:
            if not all(inspector.get(key) for key in ("visible_facts","association","disclosure","mechanism","phone","voice_content")):
                raise ValueError("explicit evidence required to complete manual adjudication")
            judgment="verified_pass"
    return judgment,{"runtime":duration,"cuts":cuts,"hold_seconds":observed,"errors":errors,
                     "checks":checks,"repairs":sum(max(0,len(x["attempts"])-1) for x in traces),
                     "repair_stages":[a["stage"] for x in traces for a in x["attempts"] if "stage" in a],
                     "illustrator_calls":sum(sum(bool(a.get("backend")) for a in x["attempts"])+
                                             sum(bool(v.get("backend")) and not v.get("reused") for v in x["asset_records"].values()) for x in traces),
                     "review_worker_calls":sum(sum(bool(a.get("pass_a"))+bool(a.get("pass_b")) for a in x["attempts"]) for x in traces),
                     "first_candidate":judgment=="verified_pass" and all(len(x["attempts"])==1 for x in traces)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--id",action="append")
    args=ap.parse_args()
    config=read(args.root/"config.json")
    outcomes=[]
    for path in sorted(args.root.glob("*/outcome.json")):
        p=path.parent
        if args.id and p.name not in args.id:
            continue
        o=read(path)
        try:
            judgment,details=evaluate(p,config)
        except Exception as e:
            judgment,details="unjudged",{"evaluation_error":str(e)}
        final={**o,"judgment":judgment,**details}
        dump(p/"evaluation.json",final)
        outcomes.append(final)
        print(p.name,judgment,details.get("errors") or details.get("evaluation_error",""),flush=True)
    rows=[read(p) for p in args.root.glob("*/evaluation.json")]
    by=defaultdict(list)
    for row in rows:
        n=int(row["id"][1:])
        by[FAMILIES[n-1 if row["id"].startswith("H") else (n-1)//5]].append(row)
    header=["# Run index","",f"Frame `{config['frames']}` · Video `{config['video']}`","",
            "| Family | Judged / default denominator | Outcomes | p50 seconds | p95 seconds | Repairs (observed) |",
            "|---|---:|---|---:|---:|---:|"]
    def stat(batch):
        durations=sorted(r["seconds"] for r in batch if "seconds" in r)
        return (f"{statistics.median(durations):.1f}",f"{durations[math.ceil(.95*len(durations))-1]:.1f}") if durations else ("—","—")
    den=1 if rows and rows[0]["id"].startswith("H") else 5
    for fam in FAMILIES:
        batch=by[fam]
        t,p95=stat(batch)
        header.append(f"| {fam} | {len(batch)}/{den} | {dict(Counter(r['judgment'] for r in batch))} | {t} | {p95} | {sum(r.get('repairs',0) for r in batch)} |")
    header.extend(["","| Case | Outcome | Wall seconds | First candidate verified | Evidence |","|---|---|---:|---|---|"])
    for row in sorted(rows,key=lambda x:x["id"]):
        id=row["id"]
        video=f"[MP4]({row['job_dir']}/video.mp4)" if row["service_state"]=="succeeded" else ""
        first=("yes" if row.get("first_candidate") else "no") if row["judgment"]=="verified_pass" else "—"
        header.append(f"| {id} | {row['judgment']} | {row.get('seconds','—')} | {first} | [request]({id}/request.json) · [evaluation]({id}/evaluation.json) {video} |")
    (args.root/"INDEX.md").write_text("\n".join(header)+"\n")


if __name__=="__main__":
    main()
