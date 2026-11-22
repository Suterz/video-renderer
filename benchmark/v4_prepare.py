"""Author-side V4 compiler; corpus IDs never enter service decision logic."""
import json
import hashlib
import re
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).parent/"v3"))
from corpus import compile_case,read_cases


def prepare(record):
    req,oracle=compile_case(record,"v3")
    opening=req["beats"][0]["panel"]
    reveal=req["beats"][1]["panel"]
    # Preserve the apostrophe and hyphen group in the authored phrase. A
    # partial prefix of a possessive token is not a real spoken boundary.
    utterances={u["id"]:u["text"] for u in req["script"]}
    for beat in req["beats"]:
        cue=beat["cue"]
        if "phrase" in cue:
            words=list(re.finditer(r"\w+(?:['’\-]\w+)*",utterances[cue["utterance_id"]]))
            if words:
                cue["phrase"]=utterances[cue["utterance_id"]][words[0].start():words[min(2,len(words)-1)].end()]
    # Teaching area is above the subtitle reserve.
    req["instructional"]={"question_utterance":"question","answer_beat":req["beats"][1]["id"],
         "minimum_ms":1180,"region":[.06,.14,.94,.83],"required_facts":[]}
    for i, item in enumerate(opening["overlays"][1:],1):
        if item["type"] not in ("text","segment","shape"):
            continue
        if item["type"]=="shape" and item.get("ink")=="pale":
            # Pale backplates are not the foreground claim; requiring their
            # unpainted fill to survive marked areas would reject correct
            # partitions. Ticks/marks and exact labels remain required.
            continue
        # Annotation bounds are computed by frames-renderer and verified on its actual raster.
        fact=f"opening-{i}"
        item["fact"]=fact
        req["instructional"]["required_facts"].append(fact)
    if "can.spout" in record["demonstration"]:
        opening["anchors"]={"can.spout":"open mouth of the narrow watering tube, not its handle or tank"}
    # Reuse the author's existing semantic grounding query across later beats.
    named={key:query for panel in (opening,reveal) for key,query in panel.get("anchors",{}).items() if isinstance(query,str)}
    for beat in req["beats"][1:]:
        for graphic in beat["panel"]["overlays"]:
            point=graphic.get("to")
            if graphic["type"]=="arrow" and isinstance(point,str) and point in named:
                graphic["part_target"]=named[point].split(", not")[0].split("; absent")[0]
                if re.search(r"inside|interior|opening",named[point],re.I):
                    graphic["part_relation"]="inside_region"
    if reveal["op"]=="edit_scene":
        reveal["action_claim"]=reveal["change"]
    for beat in req["beats"]:
        panel=beat["panel"]
        ink=[x for x in panel["overlays"] if x["type"]=="shape" and x.get("ink")=="accent"]
        if panel.get("paper_scene") or panel["op"]=="overlay_only" and opening.get("paper_scene"):
            if ink and all(x.get("shape")=="disc" for x in ink):
                lo=[min(x["at"][i]-x["extent"][i]/2-.025 for x in ink) for i in range(2)]
                hi=[max(x["at"][i]+x["extent"][i]/2+.025 for x in ink) for i in range(2)]
                panel["component_claims"]=[{"region":[max(0,x) for x in lo]+[min(1,x) for x in hi],
                    "rgb":[191,77,49] if req["visual"]["graphic_theme"]=="paper" else [183,70,54],
                    "minimum_pixels":65,"expected":len(ink)}]
    oracle["evaluation_version"]="v4-1"
    oracle["phone_truth_required"]=True
    if req["script"][-1]["text"]==record["objective"]:
        # Author-declared exact spoken result. This guards verbatim disclosure;
        # visual review still checks paraphrases and the viewer's evidence.
        req["instructional"]["spoken_answer_phrases"]=[req["script"][-1]["text"]]
    return req,oracle


if __name__=="__main__":
    source,destination=map(Path,sys.argv[1:])
    for row in read_cases(source).values():
        req,oracle=prepare(row)
        folder=destination/row["id"]
        folder.mkdir(parents=True,exist_ok=False)
        for name,value in (("request",req),("oracle",oracle)):
            (folder/(name+".json")).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
