"""
scripts/ingest_guard.py
Simple polling watcher: re-runs scripts/ingest.py when docs change.

Works in:
  1) Docker compose (used as a long-running process before API)
  2) GitHub Codespaces / local dev

Env:
  WATCH_INTERVAL_SECONDS = poll interval (default: 2)
"""

import os, time, hashlib, glob, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC_GLOB = str(ROOT / "data" / "docs" / "*.md")
INTERVAL = float(os.getenv("WATCH_INTERVAL_SECONDS", "2"))

def md5_paths(pattern: str) -> str:
    h = hashlib.md5()
    paths = sorted(glob.glob(pattern))
    for p in paths:
        try:
            with open(p, "rb") as f:
                h.update(f.read())
        except Exception:
            pass
    # include file list into the hash (add/remove files)
    h.update("|".join(paths).encode())
    return h.hexdigest()

def run_ingest():
    env = os.environ.copy()
    print("→ Running ingest.py …", flush=True)
    code = subprocess.call([sys.executable, str(ROOT / "scripts" / "ingest.py")], env=env)
    if code != 0:
        print(f"ingest.py exited with code {code}", flush=True)

def main():
    # Run once at start (so Chroma is hot even if no changes later)
    last = None
    try:
        run_ingest()
    except Exception as e:
        print(f"initial ingest error: {e}", flush=True)

    while True:
        try:
            cur = md5_paths(DOC_GLOB)
            if cur != last:
                print("Docs changed → reindexing …", flush=True)
                run_ingest()
                last = cur
        except Exception as e:
            print(f"watcher error: {e}", flush=True)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()

