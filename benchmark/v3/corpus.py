"""Compile authored lesson records to the public HTTP request and an external oracle."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).parent
FAMILIES = ("comparisons", "counts", "measurement", "branching", "spatial",
            "cause", "charts", "state", "character", "mixed")
FIELDS = ("id", "title", "setup", "question", "mechanism", "objective", "failure",
          "inputs", "demonstration", "takeaway", "art")
SIGNATURES = (
    "Original pocket editorial cartoons on warm ivory drawing paper. Dark plum contours, "
    "paprika accents, asymmetrical rounded forms and a touch of pencil grain. Clean focal subject.",
    "Cobalt cut-paper atlas on cool pale paper. Navy silhouettes, coral accent shapes, "
    "angular cut edges and quiet geometric texture. Clear uncluttered teaching subject.",
)


def read_cases(*paths):
    cases = {}
    for path in paths:
        for n, line in enumerate(Path(path).read_text().splitlines(), 1):
            if not line or line.startswith("#"):
                continue
            fields = line.split("|")
            if len(fields) != len(FIELDS):
                raise ValueError(f"{path}:{n}: expected {len(FIELDS)} fields; found {len(fields)}")
            case = dict(zip(FIELDS, (v.strip() for v in fields)))
            if not re.fullmatch("[DH][0-9]{2}", case["id"]) or case["id"] in cases:
                raise ValueError(f"invalid/duplicate id {case['id']}")
            if not all(case[k] for k in FIELDS[:-1]):
                raise ValueError(f"{case['id']}: incomplete teaching brief")
            cases[case["id"]] = case
    return cases


def p(s):
    return round(float(s) / 100, 6)


def target(text):
    value = text.split(":")
    return [p(v) for v in value] if len(value) == 2 else text


def layers(commands, native, theme):
    overlays, checks = [], []
    for token in commands.split(";"):
        if not token:
            continue
        kind, *a = token.split(",")
        if kind == "T":
            x, y, *words = a
            text = ",".join(words)
            overlays.append({"type":"text","at":[p(x),p(y)],"text":text, **({"role":"value" if re.search(r"\d", text) else "support"} if native else {})})
            checks.append({"kind":"label","at":[p(x),p(y)],"text":text})
        elif kind == "A":
            source = [p(a[0]),p(a[1])]
            endpoint = target(a[2]) if len(a)==3 else [p(a[2]),p(a[3])]
            overlays.append({"type":"arrow","from":source,"to":endpoint})
            checks.append({"kind":"arrow","from":source,"to":endpoint})
        elif kind in ("G","C"):
            if kind == "C":
                x,y,d = (float(k) for k in a)
                a=[x,y,1,1,1,1]
            else:
                d=7
            x,y,cols,rows,dx,dy = (float(k) for k in a)
            for iy in range(int(rows)):
                for ix in range(int(cols)):
                    at = [p(x+ix*dx), p(y+iy*dy)]
                    if native:
                        overlays.append({"type":"shape","shape":"disc","at":at,"extent":[p(d),p(d)*9/16],"ink":"accent"})
                    else:
                        overlays.append({"type":"marker","at":at})
                    checks.append({"kind":"counter","at":at,"diameter":p(d)})
        elif kind in ("S","K"):
            x,y,u,v = (p(z) for z in a[:4])
            n = int(a[4]) if kind == "K" else None
            points = [[x,y],[u,v]]
            if native:
                overlays.append({"type":"segment","from":points[0],"to":points[1],"divisions":n,"ink":"ink"})
            else:
                # Native v2 cannot draw an undirected ruler. Use its closest
                # existing marks, without silently claiming exact tick geometry.
                overlays.append({"type":"arrow","from":points[0],"to":points[1]})
                if n:
                    overlays.extend({"type":"marker","at":[x+(u-x)*i/n,y+(v-y)*i/n]} for i in range(n+1))
            checks.append({"kind":"segment","from":points[0],"to":points[1],"divisions":n})
        elif kind in ("R","B"):
            if kind=="B":
                x,y = [p(z) for z in a[:2]]
                u,v,ink = x + float(a[2])/float(a[3])*p(a[4]), y+.04, "accent"
            else:
                x,y,u,v = [p(z) for z in a[:4]]
                ink = a[4]
            at = [(x+u)/2,(y+v)/2]
            if native:
                overlays.append({"type":"shape","shape":"rect","at":at,"extent":[u-x,v-y],"ink":ink})
            else:
                overlays.append({"type":"arrow","from":[x,at[1]],"to":[u,at[1]]})
            checks.append({"kind":"rect","bounds":[x,y,u,v],"ink":ink})
        else:
            raise ValueError(f"unknown visual command {kind}")
    return overlays, checks


def compile_case(case, mode):
    native = mode == "v3"
    number = int(case["id"][1:])
    holdout = case["id"].startswith("H")
    family_index = number-1 if holdout else (number-1)//5
    theme = (number + family_index) % 2
    family = FAMILIES[family_index]
    # Different writing voices and draw signatures are allocated before seeing output.
    voice = "ryan" if (number+2*family_index)%4 == 1 else "heart"
    signature = SIGNATURES[theme] + "\n## Renderer-only graphics\nSeparate objects and meaning-bearing labels."
    shape_start, startup = layers(case["inputs"], native, theme)
    shape_process, process = layers(case["demonstration"], native, theme)
    brief = case["art"]
    nice = brief or "Plain nearly-white paper with very light paper grain, no objects, no text, no diagram, blank instructional background."
    seed = int(hashlib.sha256(case["id"].encode()).hexdigest()[:7], 16)
    closing, ending = [], []
    for i, text in enumerate(case["takeaway"].split(" / ")):
        y = 78 if i==0 else 82
        this, checks = layers(f"T,50,{y},{text}", native, theme)
        closing += this
        ending += checks
    header = case["title"].upper()
    if len(header)>33:
        header = " ".join(header.split()[:4])
    title = {"type":"text","at":[.50,.095],"text":header,**({"role":"question"} if native else {})}
    header_check = {"kind":"label","at":[.50,.095],"text":header}
    opts = {"story_context":"Prepared educational mini-lesson. Teach from the declared visual and graphic operations, without lettering in generated images.",
            "visual_signature":signature,"canvas":[1080,1920]}
    if native:
        opts["graphic_theme"] = "paper" if theme==0 else "atlas"
    op = "overlay_only"
    after = {}
    before = {}
    if brief.startswith("Controlled fruit icon."):
        # Use v2's real cutout workflow for this count-dependent scene.
        opts["assets"]={"fruit":{"kind":"generated_cutout","visual":brief.split(". ",1)[1],"seed":119}}
        centers=[o["at"] for o in startup if o["kind"]=="counter"]
        for o in startup:
            if o["kind"]=="counter":
                o["kind"]="fruit"
        shape_start=[o for o in shape_start if o["type"] not in ("shape","marker")]
        before["layout"]={"layers":[{"id":f"fruit{i}","asset":"fruit","center":xy,"width":.110,"max_height":.065}
                               for i,xy in enumerate(centers,1)]}
        nice="Present two separated rows of illustrated orange fruit, with clear room for the authored values."
    anchor_defs={"teal.knot":"the center knot where the striped teal bow loops join, not the tag or bag; absent if obscured",
                 "basket.opening":"the inside of the visible dark basket opening, not rim or front wall; absent if obscured",
                 "book.spine":"the narrow bound edge of the book, not its cover or page block; absent if obscured",
                 "mug.handle":"the striped side handle of the middle mug, not the cup body; absent if obscured",
                 "zipper.slider":"the metal block where the two rows of teeth meet, not the dangling pull tab; absent if obscured"}
    named={k:v for k,v in anchor_defs.items() if k in case["demonstration"]}
    if named:
        before["anchors"]=named
    if "During the edit" in brief:
        nice, action = brief.split("During the edit ",1)
        op = "edit_scene"
        after.update(change=action, keep="Preserve the exact character, viewpoint, position and props.")
        if named:
            after["anchors"]=before.pop("anchors")
    elif "mug.handle" in named:
        op="focus"
        after["focus"]={"anchor":"mug.handle","zoom":1.8}
    if case["id"] in ("D46","H10"):
        op="new_scene"
    setup_panel = {"op":"new_scene","scene_id":"lesson","objective":case["setup"],
                   "instruction":nice, "seed":seed,"overlays":[title]+shape_start,**before}
    if native and not brief:
        setup_panel["paper_scene"]=True
    demonstrator = {
        "op":op, "scene_id":"lesson" if op!="new_scene" else "diagram",
        "objective":case["mechanism"],
        "instruction":("Blank instructional paper matching the established palette. No lettering." if op=="new_scene"
                       else action if op=="edit_scene" else "Preserve the clean image; show the requested explanatory graphics."),
        "seed":seed+1, "overlays":[title]+shape_process, **after,
    }
    if native and op=="new_scene":
        demonstrator["paper_scene"]=True
    # Unit-price calculations annotate the same rows rather than replacing them.
    if before.get("layout"):
        demonstrator["overlays"][1:1] = shape_start
        process = startup + process
    asks = re.findall(r"\b[\w']+\b", case["mechanism"])[:3]
    result = re.findall(r"\b[\w']+\b", case["objective"])[:3]
    request = {"title":case["title"], "visual":opts,"voice_profile":voice, "max_ms":29000,
               "subtitle_font_size":42, "closing_hold_ms":1350,
               "script":[{"id":"setup","text":case["setup"],"caption":None},
                         {"id":"question","text":case["question"],"caption":case["question"],"pause_after_ms":1250+(number%3)*220},
                         {"id":"mechanism","text":case["mechanism"],"caption":"" if native else None},
                         {"id":"answer","text":case["objective"],"caption":"" if native else None}],
               "beats":[
                   {"id":"setup","cue":{"ms":0},"panel":setup_panel},
                   {"id":"demonstrate","parent":"setup" if op!="new_scene" else None,
                    "cue":{"utterance_id":"mechanism","phrase":" ".join(asks)},"panel":demonstrator},
                   {"id":"conclude","parent":"demonstrate","cue":{"utterance_id":"answer","phrase":" ".join(result)},
                    "panel":{"op":"overlay_only","scene_id":demonstrator["scene_id"],"objective":case["objective"],
                             "instruction":"Retain the explanation and add the closing takeaway.",
                             "overlays":demonstrator["overlays"]+closing}},
               ]}
    spec = {"id":case["id"],"family":family,"mode":mode,"theme":theme,"teaching_objective":case["objective"],
            "failure":case["failure"],"minimum_setup_ms":1400,"prediction_rule":"Setup at frame zero; result not visible until conclusion, and at least 1.25 s without narration after question.",
            "readable_phone":"360×640, no clipping or color-only distinction","art_continuity_requires_review":bool(brief and not before.get("layout")),
            "stage":[[header_check]+startup,[header_check]+process,[header_check]+process+ending],"native_required":any(x["kind"] in ("rect","segment") or x["kind"]=="arrow" for x in process+startup)}
    return request,spec


if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--mode",choices=("v2","v3"),default="v3")
    ap.add_argument("--file",type=Path,action="append")
    a=ap.parse_args()
    cases=read_cases(*(a.file or [HERE/"first.tsv",HERE/"development.tsv"]))
    print(json.dumps(compile_case(cases[a.id],a.mode)[0],ensure_ascii=False,indent=2))
