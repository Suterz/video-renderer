"""Compare independent unprompted transcripts from source PCM and actual MP4."""
import argparse,json,os,re,subprocess
from pathlib import Path
from difflib import SequenceMatcher

p=argparse.ArgumentParser()
p.add_argument("results",type=Path)
p.add_argument("cases",nargs="+")
a=p.parse_args()
home=Path.home()
speaker=home/"venvs/v2-asr/bin/python"
worker=Path(__file__).resolve().parents[1]/"src/video_renderer/speech_worker.py"
models=home/"ai/storyboard-build/v2"
env={**os.environ,"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"}
for id in a.cases:
    index=a.results/id
    row=json.loads((index/"outcome.json").read_text())
    if row["service_state"]!="succeeded":
        continue
    job=Path(row["job_dir"])
    m=json.loads((job/"manifest.json").read_text())
    proc=subprocess.run([str(speaker),str(worker),"asr",str(models),str(job/"video.mp4")],
          input='{"text":""}',env=env,capture_output=True,text=True,timeout=140,check=True)
    muxed=json.loads(proc.stdout.splitlines()[-1])
    asr=lambda words:"".join(w["word"] for w in words).strip()
    source,end=map(asr,(m["asr"],muxed))
    def tokenize(s):
        # Ignore ordinary punctuation, retain exact numbers and units.
        return re.findall(r"\d+(?:[.:]\d+)?|[A-Za-z]+(?:'[A-Za-z]+)?",s.casefold())
    old,new=tokenize(source),tokenize(end)
    comp=SequenceMatcher(None,old,new,autojunk=False)
    changes=[{"type":t,"source":old[l:r],"muxed":new[u:v]} for t,l,r,u,v in comp.get_opcodes() if t!="equal"]
    report={"case":id,"job":row["job_id"],"muxed_video_sha256":row["download_sha256"],"source_ASR":source,
       "muxed_ASR":end,"word_agreement":round(comp.ratio(),4),"changes":changes,
       "boundary_sample_checks":m.get("instructional_evidence"),
       "scope":"Machine transcripts are preliminary. Pronunciation and perceived sync require listening."}
    (index/"mux-audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(id,report["word_agreement"],changes,flush=True)
