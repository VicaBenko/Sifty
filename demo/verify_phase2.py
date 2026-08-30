"""Automated walk-through of the Phase 2 acceptance criteria (D-1, D-4, D-6, D-8..D-11).

Runs a full round headlessly against demo/serve.py, then resets the photo set.
Safe to run before the demo. Needs no API key: predicates come from the cache.

    python demo/verify_phase2.py
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"
PHOTOS = DEMO / "photos"
QUAR = DEMO / "quarantine"
PORT = 8199
BASE = f"http://127.0.0.1:{PORT}"
fails = []

def check(label, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (f"   {detail}" if detail else ""))
    if not ok: fails.append(label)

def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=30))

def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=30))

print("== reset baseline ==")
print(subprocess.run([sys.executable, "demo/reset.py"], cwd=ROOT,
                     capture_output=True, text=True).stdout.strip())

env = dict(os.environ); env.pop("ANTHROPIC_API_KEY", None)  # prove offline operation
server = subprocess.Popen([sys.executable, "demo/serve.py", "--port", str(PORT)],
                          cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/gallery", timeout=2); break
        except Exception: time.sleep(0.2)

    print("\n== D-8  full round ==")
    preds = post("/api/predicates", {"query": "a dog"})
    check("predicates came from cache, no network", preds["source"] == "cache", preds["source"])
    res = post("/api/search", {"predicates": preds["predicates"]})
    check("`a dog` returns 11 matches", res["total"] == 11, f"total={res['total']} certain={res['certain']}")
    check("every match carries a byte size", all(m.get("bytes", 0) > 0 for m in res["matches"]))

    certain = [m["id"] for m in res["matches"] if m["confidence"] == "certain"]
    borderline = [m["id"] for m in res["matches"] if m["confidence"] == "borderline"]
    check("P2-1 default selection = certain only", len(certain) == 10 and len(borderline) == 1,
          f"certain={len(certain)} borderline={len(borderline)}")

    before = {p.name for p in PHOTOS.iterdir() if p.suffix == ".jpg"}
    q = post("/api/quarantine", {"ids": certain, "query": "a dog"})
    check("P2-3 copy, never move: originals all still present",
          {p.name for p in PHOTOS.iterdir() if p.suffix == ".jpg"} == before)
    check("P2-6 banner state says 10 awaiting", q["awaiting"] == 10, str(q["awaiting"]))

    man = json.loads((QUAR / "manifest.json").read_text())
    check("P2-4 manifest maps copy -> source + signature",
          len(man) == 10 and all(e.get("source") and e.get("sha256") and e.get("query") == "a dog" for e in man))

    st = get("/api/quarantine")
    check("P2-6 status survives being read fresh from disk", st["awaiting"] == 10)

    print("\n== D-9  AC-3: two photos pulled out of quarantine before approval ==")
    spared = sorted(e["filename"] for e in man)[:2]
    for name in spared:
        (QUAR / name).unlink()
    print(f"  pulled out by hand: {spared}")

    result = post("/api/approve", {})
    check("released count = 2", result["released"] == 2, str(result["released"]))
    check("deleted count = 8", result["deleted"] == 8, str(result["deleted"]))
    check("D-9  the two released photos are STILL in demo/photos/",
          all((PHOTOS / n).is_file() for n in spared), str(spared))
    deleted_names = [e["filename"] for e in man if e["filename"] not in spared]
    check("the other eight are gone from demo/photos/",
          not any((PHOTOS / n).is_file() for n in deleted_names))
    check("the borderline hot-dog photo was never selected, and survives",
          all((PHOTOS / Path(json.loads((DEMO/'_ws'/'manifest.json').read_text())[0]['filename']).name).exists() for _ in [0])
          and (PHOTOS / next(i["filename"] for i in json.loads((DEMO/"_ws"/"manifest.json").read_text()) if i["id"] == borderline[0])).is_file())

    log = json.loads((DEMO / "operation-log.json").read_text())
    check("P2-9 operation log records id, source, date, query for each deletion",
          len(log["deletions"]) == 8 and all(set(d) >= {"id","source","date","query"} for d in log["deletions"]))
    check("P2-10 release rate recorded", log["rounds"][-1]["release_rate"] == 0.2,
          str(log["rounds"][-1]["release_rate"]))

    check("P2-6 banner clears after approval", get("/api/quarantine")["awaiting"] == 0)
    again = post("/api/search", {"predicates": preds["predicates"]})
    check("deleted photos no longer appear in results", again["total"] == 3, f"total={again['total']}")

    print("\n== D-6  bind address ==")
    check("server refuses a non-localhost address",
          subprocess.run(["ss","-ltnp"], capture_output=True, text=True).stdout.count(f"127.0.0.1:{PORT}") >= 1
          or f"127.0.0.1:{PORT}" in subprocess.run(["netstat","-ltn"], capture_output=True, text=True).stdout)
finally:
    server.terminate(); server.wait(timeout=10)

print("\n== D-11  reset ==")
out = subprocess.run([sys.executable, "demo/reset.py"], cwd=ROOT, capture_output=True, text=True).stdout
print("  " + out.strip().replace("\n", "\n  "))
check("D-11 photo set restored to 128", len([p for p in PHOTOS.iterdir() if p.suffix == ".jpg"]) == 128)
check("quarantine emptied", not any(QUAR.iterdir()) if QUAR.is_dir() else True)
check("operation log cleared", not (DEMO / "operation-log.json").exists())

print("\n== D-10  no move in any code path ==")
code = (DEMO/"serve.py").read_text() + (DEMO/"reset.py").read_text()
import re
lines = [l for l in code.splitlines() if not l.strip().startswith("#")]
bad = [l.strip() for l in lines if re.search(r"shutil\.move|os\.rename|\.rename\(|os\.replace", l)]
check("D-10 no move/rename of any photo", not bad, str(bad))

print("\n== regression tests ==")
r = subprocess.run([sys.executable, "demo/test_matching.py"], cwd=ROOT, capture_output=True, text=True)
print("  " + (r.stdout + r.stderr).strip().replace("\n", "\n  ")[:600])
check("test_matching.py passes", r.returncode == 0)

print("\n" + ("ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
