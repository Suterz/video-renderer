"""Paired spoken-disclosure controls: exact declared answer, identical art."""
from pathlib import Path
import json,sys,httpx
from v4_controls import send

url,output=sys.argv[1:]
with httpx.Client(base_url=url,timeout=20) as h:
    for idx,(title, setup, question, answer, result) in enumerate((
        ("Which chute carries the parcel?", "A parcel reaches a junction. Only one chute is open.",
         "Which chute will it take?", "It goes down the left chute.", "LEFT CHUTE"),
        ("Which timer completes first?", "The two timers begin together, one set to three and one set to four.",
         "Which finishes first?", "The shorter timer finishes first.", "SHORTER TIMER"),
    )):
        for disclose in (True,False):
            opening=[{"type":"text","at":[.5,.27],"text":title.upper(),"role":"question","fact":"prompt"}]
            req={"title":title,"voice_profile":"heart",
                 "visual":{"story_context":title,"visual_signature":"Clear warm paper diagram."},
                 "script":[{"id":"setup","text":setup+(f" {answer}" if disclose else "")},
                           {"id":"ask","text":question,"pause_after_ms":1500},
                           {"id":"answer","text":answer}],
                 "instructional":{"question_utterance":"ask","answer_beat":"answer","required_facts":["prompt"],
                    "region":[.08,.1,.92,.78],"minimum_ms":1080,"spoken_answer_phrases":[answer]},
                 "beats":[{"id":"open","cue":{"ms":0},"panel":{"op":"new_scene","paper_scene":True,"scene_id":"test","objective":"Hold the question.",
                                "instruction":"Do not visually show the answer yet.","overlays":opening}},
                          {"id":"answer","parent":"open","cue":{"utterance_id":"answer","phrase":answer},
                           "panel":{"op":"overlay_only","scene_id":"test","objective":"Reveal the result.","instruction":"Only add the result.",
                                    "overlays":opening+[{"type":"text","at":[.5,.49],"text":result,"role":"value"}]}}]}
            p=Path(output)/f"control-{idx}-{'early' if disclose else 'timed'}"
            d=send(h,"/v2/renders",req,p)
            (p/"status.json").write_text(json.dumps(d,indent=2))
            print(p.name,d["state"],d.get("error"),flush=True)
            if disclose:
                assert d["state"]=="needs_review" and "before its declared reveal" in d.get("error","")
            else:
                assert d["state"]=="succeeded",d
                (p/"video.mp4").write_bytes(h.get(d["video_url"]).content)
