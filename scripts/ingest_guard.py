# scripts/ingest_guard.py
import hashlib, os, json
from pathlib import Path
from subprocess import run, CalledProcessError

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "docs"
STATE = ROOT / "data" / ".ingest_state.json"

def dir_hash(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(path).as_posix().encode())
            h.update(str(p.stat().st_mtime_ns).encode())
            h.update(p.read_bytes())
    return h.hexdigest()

def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    old = {}
    if STATE.exists():
        try:
            old = json.loads(STATE.read_text())
        except Exception:
            old = {}
    current = {"docs_hash": dir_hash(DOCS)}
    if old.get("docs_hash") != current["docs_hash"]:
        print("Docs changed → running ingest.py …")
        try:
            run(["python", "scripts/ingest.py"], check=True)
            STATE.write_text(json.dumps(current))
            print("Ingest complete.")
        except CalledProcessError as e:
            raise SystemExit(e.returncode)
    else:
        print("Docs unchanged → skipping ingest.")

if __name__ == "__main__":
    main()
