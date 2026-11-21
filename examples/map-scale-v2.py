"""Held-out transfer input: fixed geometry and an utterance-internal reveal."""
import json

visual = {
    "story_context": "A map scale converts a drawn distance to a real distance using equal units.",
    "visual_signature": "Flat atlas editorial cartoon, navy outlines, clean white paper and red accents. No text baked into icons.",
    "assets": {"pin": {"kind": "generated_cutout", "visual": "one simple solid red map pin icon, full shape, dark navy outline", "seed": 409}},
}
layout = {"layers": [{"id": k, "asset": "pin", "center": [x, .40], "width": .13, "max_height": .14}
                     for k, x in [("start", .23), ("end", .77)]]}


def label(text, pos):
    return {"type": "label", "at": pos, "text": text}


common = {"scene_id": "atlas", "instruction": "Two red map pins with distinct labels and a clear scale explanation.",
          "objective": "Two centimeters on the map represent four kilometers at two kilometers per centimeter."}
link = {"type": "arrow", "from": "start.center", "to": "end.center"}
request = {
    "title": "Read a map scale", "voice_profile": "heart", "visual": visual,
    "script": [
        {"id": "scale", "text": "On this map, one centimeter stands for two kilometers.", "caption": "1 cm on the map = 2 km"},
        {"id": "length", "text": "The pins are two centimeters apart, so the real distance is four kilometers.",
         "caption": "2 cm on the map = 4 km", "critical_spoken": [["four kilometers", "4 kilometers", "4 km"]]},
    ],
    "beats": [
        {"id": "map", "cue": {"ms": 0}, "panel": {**common, "op": "new_scene", "layout": layout,
         "overlays": [label("MAP SCALE", [.5, .13]), label("1 cm = 2 km", [.5, .65])]}},
        {"id": "measure", "parent": "map", "cue": {"utterance_id": "length", "phrase": "two centimeters"},
         "panel": {**common, "op": "overlay_only", "overlays": [label("2 cm ON THE MAP", [.5, .23]), link]}},
        {"id": "real", "parent": "measure", "cue": {"utterance_id": "length", "phrase": "four kilometers"},
         "panel": {**common, "op": "overlay_only", "overlays": [label("2 cm ON THE MAP", [.5, .23]), link,
                     label("4 km IN REAL LIFE", [.5, .65])],
                   "composed_checks": [{"question": "Read the number of kilometers shown for the real-life distance. Give only the digit.", "expected": "4"}]}},
    ],
}
print(json.dumps(request))
