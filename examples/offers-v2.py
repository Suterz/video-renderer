"""Prepared author fixture: no lesson-specific branching in either service."""
import json
import sys

voice = sys.argv[1] if len(sys.argv) > 1 else "heart"
reuse = sys.argv[2] if len(sys.argv) > 2 else None
visual = {
    "story_context": "Two grocery offers. The lower checkout price can have the higher unit price.",
    "visual_signature": "Original editorial cartoon, strong plum outlines, warm ivory paper, bright ochre fruit, teal leaves, rounded simple silhouettes.",
    "canvas": [1080, 1920],
    "assets": {"orange": {"kind": "generated_cutout", "seed": 119, "visual": "ONE round orange fruit with one green leaf, thick plum ink outline"}},
    "values": {"A": 600, "B": 800, "na": 3, "nb": 5, "pa": 200, "pb": 160},
    "checks": [{"kind": "equal_groups", "total_minor": k, "count": count, "each_minor": each}
               for k, count, each in [("A", "na", "pa"), ("B", "nb", "pb")]],
}
layers = [{"id": f"{key}{i+1}", "asset": "orange", "center": [x, y], "width": .125}
          for key, y, xs in [("A", .30, [.32, .50, .68]), ("B", .63, [.18, .34, .50, .66, .82])]
          for i, x in enumerate(xs)]


def label(text, x, y):
    return {"type": "text", "text": text, "at": [x, y]}


headers = [label("OFFER A    •    3 ORANGES", .5, .21), label("OFFER B    •    5 ORANGES", .5, .54)]
totals = [label("$6 TOTAL", .5, .38), label("$8 TOTAL", .5, .71)]
prices = [label("$2.00 EACH", .5, .445), label("$1.60 EACH", .5, .775)]
beats = []
for id_, cue, labels in [
    ("offers", {"ms": 0}, headers),
    ("totals", {"utterance_id": "total", "phrase": "At checkout"}, headers + totals + [label("A COSTS LESS AT CHECKOUT", .5, .10)]),
    ("units", {"utterance_id": "unit", "phrase": "But per orange"}, headers + totals + prices),
    ("result", {"utterance_id": "winner", "phrase": "The second wins"}, headers + totals + prices + [label("B SAVES 40¢ PER ORANGE", .5, .10)]),
]:
    parent = beats[-1]["id"] if beats else None
    panel = {"op": "overlay_only" if parent else "new_scene", "scene_id": "comparison",
             "objective": "Compare three oranges for $6 with five for $8 without confusing total and unit prices.",
             "instruction": "Two clearly separated rows of exactly three and five oranges. In-scene labels identify each offer.",
             "overlays": labels}
    if not parent:
        panel["layout"] = {"layers": layers}
    if id_ == "result":
        panel["composed_checks"] = [{"question": "Which offer costs less per orange? Answer only with the letter A or B.", "expected": "B"}]
    beats.append({"id": id_, "parent": parent, "cue": cue, "panel": panel})
script = [
    {"id": "question", "text": "Which bag is cheaper per orange?", "caption": "Which bag is cheaper per orange?"},
    {"id": "counts", "text": "Three oranges cost six dollars. Five cost eight.", "caption": "Three for $6. Five for $8.",
     "critical_spoken": [["three oranges", "3 oranges"], ["six dollars", "6"], ["five cost eight", "5 cost 8", "five cost 8"]]},
    {"id": "total", "text": "At checkout, the first bag costs less.", "caption": "At checkout, the first bag costs less."},
    {"id": "unit", "text": "But per orange?", "caption": "But per orange?"},
    {"id": "winner", "text": "The second wins: one dollar sixty, instead of two.", "caption": "The second wins: $1.60 instead of $2.00.",
     "critical_spoken": [["one dollar sixty", "1.60"], ["instead of two", "instead of 2"]]},
]
print(json.dumps({"title": "Which bag is really cheaper?", "visual": visual, "script": script, "beats": beats,
                  "voice_profile": voice, "reuse_visuals_from": reuse}, indent=2))
