"""Compare independent ASR from the delivered MP4 with source transcript evidence."""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def reconcile(source, rendered):
    def tokens(text):
        return re.findall(r"\d+(?:[.:]\d+)?|[A-Za-z]+(?:'[A-Za-z]+)?", text.casefold())

    old, new = tokens(source), tokens(rendered)
    match = SequenceMatcher(None, old, new, autojunk=False)
    changes = [{"kind": kind, "source": old[a:b], "rendered": new[c:d]}
               for kind, a, b, c, d in match.get_opcodes() if kind != "equal"]
    return {"word_agreement": round(match.ratio(), 4), "changes": changes}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("video", type=Path)
    p.add_argument("manifest", type=Path)
    p.add_argument("--asr-python", type=Path, required=True)
    p.add_argument("--speech-root", type=Path, required=True)
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text())
    worker = Path(__file__).resolve().parents[1] / "src/video_renderer/speech_worker.py"
    completed = subprocess.run(
        [str(args.asr_python), str(worker), "asr", str(args.speech_root), str(args.video)],
        input='{"text":""}', text=True, capture_output=True, timeout=140, check=True,
        env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    )
    source = "".join(word["word"] for word in manifest["asr"]).strip()
    actual = "".join(word["word"] for word in json.loads(completed.stdout.splitlines()[-1])).strip()
    with args.video.open("rb") as media:
        digest = hashlib.file_digest(media, "sha256").hexdigest()
    print(json.dumps({"mp4_sha256": digest, "source_transcript": source, "muxed_transcript": actual,
                      **reconcile(source, actual)}, indent=2))


if __name__ == "__main__":
    main()
