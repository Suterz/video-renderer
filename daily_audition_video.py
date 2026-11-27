"""Synchronize the common battery audition artwork to each actual recording."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("take", type=Path)
    parser.add_argument("speech_worker", type=Path)
    args = parser.parse_args()
    from storyboard_renderer.daily_visual import exact

    home = Path.home()
    fresh = home / "ai/storyboard-rehearsal/fresh"
    ffmpeg = home / "ai/tools/media/bin/ffmpeg"
    for passage in ("hook", "explanation"):
        folder = args.take
        source = folder / f"{passage}-playback.wav"
        run = subprocess.run([str(fresh / "venvs/v2-align/bin/python"), str(args.speech_worker), "align",
                              str(fresh / "speech"), str(source)],
                             input=json.dumps({"text": (folder / f"{passage}.txt").read_text()}),
                             text=True, capture_output=True, check=True, timeout=120)
        alignment = json.loads(run.stdout.splitlines()[-1])
        cues = {"hook": ("75", "48"), "explanation": ("100", "75", "60", "48", "80", "75")}[passage]
        cursor = 0
        duration = json.loads((folder / "receipt.json").read_text())["passes"][passage]["audio_seconds"]
        times = []
        for value in cues:
            matches = [i for i in range(cursor, len(alignment)) if alignment[i]["word"] == value]
            if not matches:
                raise ValueError(f"{passage}: expected measured number {value}")
            cursor = matches[0] + 1
            times.append(alignment[cursor-1]["start"])
        panels = []
        for i in range(len(cues)+1):
            if passage == "hook":
                values = [["75 kWh", "?"], ["48 kWh", "?"]]
                focus = ((0,0), (1,0))[i-1] if i else None
            else:
                values = [["75 kWh", "100 kWh" if i else "?"], ["48 kWh", "60 kWh" if i >= 3 else "?"]]
                focus = ((0,1), (0,0), (1,1), (1,0), (1,2), (0,2))[i-1] if i else None
                if i >= 5:
                    values[0].append("75%" if i == 6 else "?")
                    values[1].append("80%")
            meters = [{"object": name, "readings": [{"label": label, "display": display, "focus": focus == (j,k)}
                       for k, (label, display) in enumerate(zip(("Energy returned", "Energy put in", "Share returned"), readings))]}
                      for j, (name, readings) in enumerate(zip(("Battery A", "Battery B"), values, strict=True))]
            path = folder / f"{passage}-frame-{i}.png"
            exact({"operation": "meters", "meters": meters}, (720,1280), path)
            panels.append(path)
        timeline = folder / f"{passage}-concat.txt"
        marks = [0, *times, duration]
        timeline.write_text("".join(f"file '{path.name}'\nduration {end-start:.5f}\n"
                            for path, start, end in zip(panels, marks[:-1], marks[1:], strict=True))
                            + f"file '{panels[-1].name}'\n")
        subprocess.run([str(ffmpeg), "-v", "error", "-f", "concat", "-safe", "1", "-i", str(timeline),
                        "-i", str(source), "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", str(folder / f"{passage}.mp4")],
                       check=True, timeout=120)
        (folder / f"{passage}-timing.json").write_text(json.dumps({"cues": list(zip(cues, times)),
                                                                  "alignment": alignment}, indent=2))


if __name__ == "__main__":
    main()
