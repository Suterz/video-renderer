"""Two unrelated movement videos with independently checked actual cutouts."""
from pathlib import Path
import json,sys,httpx
from v4_controls import send

url,root=sys.argv[1:]
root=Path(root)
cases=[
    {"id":"reflection","title":"What changes at the mirror?","visual":"One bright red toy sailboat with a triangular sail in side profile, pointed to the right. Isolated on completely white.",
     "setup":"Both boats sit equally far from the mirror line.",
     "question":"When the left boat moves closer, where does its image go?",
     "answer":"The two boats move equally close to the mirror.",
     "old":[.23,.77],"new":[.39,.61],"moves":["real","image"],"names":["BOAT","IMAGE"]},
    {"id":"dock","title":"Which boat reaches the dock?","visual":"One tiny round blue cartoon tugboat in side profile, on uniform white. No floor or shadows.",
     "setup":"The right boat stays still. The other heads toward the dock.",
     "question":"Which boat moves to the dock line?",
     "answer":"The left boat reaches the dock. The other stays put.",
     "old":[.23,.77],"new":[.43,.77],"moves":["real"],"names":["MOVING BOAT","WAITING BOAT"]},
]
with httpx.Client(base_url=url,timeout=25) as h:
    for c in cases:
        axis={"type":"segment","from":[.5,.29],"to":[.5,.66]}
        title={"type":"label","text":"MIRROR" if c["id"]=="reflection" else "DOCK",
               "at":[.5,.22],"role":"value","fact":"reference"}
        def layers(xs):
            a,b=xs
            return {"layers":[{"id":"real","asset":"boat","center":[a,.47],"width":.14},
                    {"id":"image","asset":"boat","center":[b,.47],"width":.14,"flip_x":c["id"]=="reflection"}]}
        def graphics(xs):
            return [axis,title]+[{"type":"label","text":n,"at":[x,.59],"role":"support"} for n,x in zip(c["names"],xs)]
        req={"title":c["title"],"voice_profile":"heart",
             "visual":{"story_context":c["title"],"visual_signature":"Editorial cartoon in clean navy, red and ivory.",
                       "assets":{"boat":{"kind":"generated_cutout","visual":c["visual"],"keep_largest_component":True,"seed":98}}},
             "script":[{"id":"setup","text":c["setup"]},{"id":"question","text":c["question"],"pause_after_ms":1500},
                       {"id":"answer","text":c["answer"]}],
             "instructional":{"question_utterance":"question","answer_beat":"reveal","required_facts":["reference"],
                              "region":[.07,.18,.94,.74],"minimum_ms":1120},
             "beats":[{"id":"open","cue":{"ms":0},"panel":{"op":"new_scene","scene_id":"move","objective":c["setup"],
                       "instruction":"Use the two separate authored cutouts.","layout":layers(c["old"]),"overlays":graphics(c["old"])}},
                      {"id":"reveal","parent":"open","cue":{"utterance_id":"answer","phrase":" ".join(c["answer"].split()[:3])},
                       "panel":{"op":"layout_transition","scene_id":"move","objective":c["answer"],"instruction":"Translate the specified instances.",
                                "moved_instances":c["moves"],"layout":layers(c["new"]),"overlays":graphics(c["new"])}}]}
        place=root/c["id"]
        d=send(h,"/v2/renders",req,place)
        (place/"status.json").write_text(json.dumps(d,indent=2))
        if d["state"]=="succeeded":
            (place/"video.mp4").write_bytes(h.get(d["video_url"]).content)
            (place/"manifest.json").write_bytes(h.get(d["status_url"]+"/manifest").content)
        print(c["id"],d["state"],d.get("error"),flush=True)
        if c["id"]=="reflection":
            req["beats"][1]["panel"]["layout"]=layers(c["old"])
            wrong=root/"annotation-only"
            d=send(h,"/v2/renders",req,wrong)
            (wrong/"status.json").write_text(json.dumps(d,indent=2))
            print("annotation-only",d["state"],d.get("error"),flush=True)
