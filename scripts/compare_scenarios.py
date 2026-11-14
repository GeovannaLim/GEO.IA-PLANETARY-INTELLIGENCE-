"""Compare two science_tests.json runs key by key (ignoring volatile fields).
    PYTHONPATH=. python scripts/compare_scenarios.py BASE.json NEW.json"""
import json, sys
VOLATILE = {"analysis_id", "created_at", "completed_at", "report_id", "links", "cache", "elapsed_s", "duration_s",
            "retrieved_at", "generated_at", "timings", "processing_time_s", "updated_at", "request_id"}

def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x

a, b = (json.load(open(p)) for p in sys.argv[1:3])
ignore_new = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else set()
diff = {}
for cid in a["raw"]:
    ra, rb = a["raw"][cid], b["raw"].get(cid)
    if rb is None:
        diff[cid] = ["missing"]; continue
    ra, rb = (r.get("result", r) if isinstance(r, dict) else r for r in (ra, rb))
    keys = set(ra) | set(rb)
    d = [k for k in sorted(keys) if k not in ignore_new and strip(ra.get(k)) != strip(rb.get(k))]
    if d:
        diff[cid] = d
print("cases:", len(a["raw"]), "| keys differing:", diff)
print("verdicts base:", {k: v.get("verdict", v) if isinstance(v, dict) else v for k, v in a["verdicts"].items()})
print("verdicts new :", {k: v.get("verdict", v) if isinstance(v, dict) else v for k, v in b["verdicts"].items()})
