"""Leaf-level diff of two science_tests.json runs, per case, ignoring volatile fields (ids, timestamps, timings).
    PYTHONPATH=. python scripts/scenario_diff.py BASE.json NEW.json [ignored_top_keys,...]"""
import json, sys
VOL = ("analysis_id", "report_id", "links", "cache", "progress", "request_id", "_seconds")

def leaves(x, p=""):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in VOL or k.endswith(("_at", "_ms", "seconds", "_s")):
                continue
            yield from leaves(v, f"{p}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, x

a, b = (json.load(open(p)) for p in sys.argv[1:3])
ign = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else set()
total = {}
for cid in a["raw"]:
    la = {k: v for k, v in leaves(a["raw"][cid]) if k.split(".")[1].split("[")[0] not in ign}
    lb = {k: v for k, v in leaves(b["raw"][cid]) if k.split(".")[1].split("[")[0] not in ign}
    d = sorted(k for k in set(la) | set(lb) if la.get(k) != lb.get(k))
    if d:
        total[cid] = d
for cid, d in total.items():
    print(cid, len(d), d[:6])
print("cases with differences:", len(total), "of", len(a["raw"]))
