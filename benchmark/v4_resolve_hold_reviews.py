"""Adjudicate hybrid alignment evidence without weakening the original hold floor."""
import json,sys
from pathlib import Path

p=Path(sys.argv[1])
for k in sys.argv[2:] or ("D14","D29","D32"):
    d=p/k
    e=json.loads((d/"evaluation.json").read_text())
    note=json.loads((d/"inspection.json").read_text())
    req=json.loads((d/"request.json").read_text())
    assert not e["errors"] and e["hold_seconds"]>=max(req["script"][1]["pause_after_ms"]-80,req["instructional"]["minimum_ms"])/1000
    assert e.get("original_hold_diagnostic")
    assert note["judgment"]=="verified_pass"
    e["judgment"]="verified_pass"
    a=e.get("repair_audit",{})
    e["first_candidate"]=a.get("repair_samples_complete",False) and a.get("observed_repairs")==0
    e["manual_hold_resolution"]="External inspection confirms the decoded mechanism; actual bound question and reveal satisfy the unchanged hold floor."
    tmp=d/"evaluation.tmp"
    tmp.write_text(json.dumps(e,ensure_ascii=False,indent=2)+"\n")
    tmp.replace(d/"evaluation.json")
