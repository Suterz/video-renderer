"""Adjudicate newly terminal jobs without ever issuing a render request."""
from pathlib import Path
import subprocess,sys,time

root=Path.home()/"Videos/storyboard-v4"
repo=Path.home()/"git/video-v4"
py=Path.home()/"venvs/video-renderer/bin/python"
roots=[root/"r1-dev-results",root/"r1-holdout-results",root/"pilot",root/"fact-stage/results"]
if len(sys.argv)>1:
    roots=[Path(x) for x in sys.argv[1:]]
while True:
    for path in roots:
        if (path/"config.json").exists():
            subprocess.run([str(py),"-B",str(repo/"benchmark/v4_evaluate.py"),str(path)],timeout=450,check=False)
    time.sleep(70)
