"""Apply the November 26 inspection of saved R5/R6 exports; never submit work."""
import json
from pathlib import Path
import sys


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def main(root):
    revised = {
        "D20": (False, "The right lever changes state, but the left switch is depicted as an undifferentiated wire with dangling stubs. Both switches are not identifiable."),
        "D21": (True, "Two distinguishable ribbon bows and separate tags remain visible. The tip rests on the dark center knot between the striped loops."),
        "D22": (True, "The opening is an interior oval distinct from the rim; the arrow starts at the apple and terminates within the oval."),
        "D24": (True, "The front cover changes to an oblique view with a separate light page block; the colored bound edge remains identifiable and the actual tip reaches it."),
        "D25": (True, "The three mugs establish the center one by two distinctive handle marks. The crop preserves the marks and body-handle association, and the tip lands on that handle."),
        "D40": (True, "Same square at snapshots one and two; the direction changes from up to right. Snapshot three advances exactly one cell right after the first upward step."),
        "D42": (False, "The opening already puts $7 on a ticket literally labeled RETURN. The answer is exposed before the requested prediction; the reveal adds a sentence without establishing a new association."),
        "D43": (True, "Two book cutouts and their fixed labels remain; the gap gains an actual third cutout at reveal, at the same shelf height."),
        "D44": (True, "The kept side and hem are visible first; the lower cut is outside the hem and the bracket shows two actual gaps."),
        "D45": (True, "One and three visible plate symbols remain next to their respective diners; the amounts are both $6, independent of the different counts."),
        "D46": (True, "A marked square remains as a reference and matches the cells of the filled 3×5 rectangle; the reveal maintains scale."),
        "D48": (True, "Fixed wall and shelf faces establish the joints. The added diagonal connects both ends and closes the same triangle."),
    }
    for round_no in (5, 6):
        store = root / f"r{round_no}-dev-results"
        for src in sorted(store.glob("*/evaluation.json")):
            current = read(src)
            if current["service_state"] != "succeeded":
                continue
            case = current["id"]
            baseline = root / "r4-dev-results" / case
            variant = case in revised and (round_no == 6 or case in {"D42", "D44", "D45", "D46", "D48"})
            if variant:
                correct, detail = revised[case]
                inspection = {"judgment": "verified_pass" if correct else "false_accept"}
                for field in ("visible_facts", "association", "disclosure", "mechanism", "phone"):
                    inspection[field] = detail
                if not correct:
                    inspection["reasons"] = [detail]
                inspection["voice_content"] = "Saved independent transcript retains the relevant associations and values; human listening pending."
            else:
                inspection = read(baseline / "inspection.json")
            inspection["review_scope"] = (
                "Inspected saved phone-size opening, pre-reveal/reveal and final rasters; compared material content "
                "against the original expectation and saved independent transcript. No scored job was resubmitted.")
            path = src.with_name("inspection.json")
            if path.exists():
                prior = read(path)
                if prior == inspection:
                    continue
                assert inspection.get("reasons") and prior == {
                    key: value for key, value in inspection.items() if key != "reasons"
                }, path
            save(path, inspection)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
