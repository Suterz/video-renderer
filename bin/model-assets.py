#!/usr/bin/env python3
"""Fetch pinned model snapshots or verify an existing external asset tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("root", type=Path)
    parser.add_argument("groups", nargs="*")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--hf", default="hf")
    args = parser.parse_args()
    groups = json.loads(args.manifest.read_text())
    for name in args.groups or groups:
        item = groups[name]
        folder = args.root / item["directory"]
        files = item["files"]
        if args.download:
            subprocess.run([args.hf, "download", item["source"], *files,
                            "--revision", item["revision"], "--local-dir", str(folder)], check=True)
        for filename, info in files.items():
            path = folder / filename
            if path.stat().st_size != info["bytes"]:
                raise SystemExit(f"Unexpected size: {path}")
            with path.open("rb") as f:
                sha = hashlib.file_digest(f, "sha256").hexdigest()
            if sha != info["sha256"]:
                raise SystemExit(f"Unexpected checksum: {path}")
        print(f"{name}: {len(files)} verified file(s)", flush=True)


if __name__ == "__main__":
    main()
