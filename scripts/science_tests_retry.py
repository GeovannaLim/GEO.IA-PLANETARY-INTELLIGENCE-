"""Re-run only the cases of a science_tests.json run that did not complete, or whose mineralogy failed for a
provider reason (e.g. the M3 deadline under a slow PDS: not a scientific result), then
re-evaluate every verdict with the same pre-registered criteria. Never changes a criterion.
    PYTHONPATH=. python scripts/science_tests_retry.py http://localhost:8010 var/science_tests_phase3a.json"""
import json
import sys
from pathlib import Path

sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
import scripts.science_tests as ST  # noqa: E402  (BASE taken from argv[1])

path = Path(sys.argv[2])
d = json.loads(path.read_text())
raw = d["raw"]
for case in ST.CASES:
    r0 = raw.get(case["id"], {})
    provider_failed = (r0.get("mineralogy") or {}).get("reason") == "provider_error"   # e.g. M3 deadline (PDS slow)
    if r0.get("status") != "completed" or provider_failed:
        print(f"[retry {case['id']}] {case['name']} ...", flush=True)
        raw[case["id"]] = ST.run(case)
        raw[case["id"]]["_retried"] = True
        print(f"     {raw[case['id']].get('status')} in {raw[case['id']].get('_seconds')} s", flush=True)
verdicts = {}
for case in ST.CASES:
    v, why = ST.evaluate(case["id"], raw[case["id"]], raw)
    ok, why_a = ST.analog_consistency(raw[case["id"]])
    verdicts[case["id"]] = {"verdict": v, "detail": why, "analogs_consistent": ok, "analogs_detail": why_a,
                            "seconds": raw[case["id"]].get("_seconds"), "retried": raw[case["id"]].get("_retried", False)}
    print(f"{v:12} {case['id']} {case['name']}: {why} | analogs: {why_a}", flush=True)
path.write_text(json.dumps({"cases": ST.CASES, "raw": raw, "verdicts": verdicts}, default=str, indent=1))
