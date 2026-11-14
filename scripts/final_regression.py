"""Final regression vs ed1ee18 on stored science_tests runs (no network): scientific values AND provenance.
    PYTHONPATH=. python scripts/final_regression.py var/prod_ed1ee18/science_tests.json var/science_tests_final.json"""
import json, sys
sys_argv = sys.argv[:]
sys.argv = ["x", "http://localhost:8010"]
import scripts.science_tests as ST  # noqa: E402

VOL = ("analysis_id", "report_id", "links", "cache", "progress", "request_id", "_seconds", "_retried")


SRC: dict = {}   # source_id -> (service, instrument, product_id, status) of the document being stripped


def strip(x):
    if isinstance(x, dict):
        return {k: (sorted(SRC.get(i, i) for i in v) if k == "source_ids" else strip(v)) for k, v in x.items()
                if not (k in VOL or k.endswith(("_at", "_ms", "seconds", "_s")))}
    if isinstance(x, list):
        return [strip(v) for v in x]
    if isinstance(x, float):
        return round(x, 9)                       # float summation order only
    return x


def prov(d):   # provenance that matters: product ids + instruments of the data sources actually used
    return sorted((s.get("instrument") or "", s.get("product_id") or "", s.get("status") or "")
                  for s in d.get("data_sources", []) if s.get("product_id") or s.get("status") == "error")


base, new = (json.load(open(p)) for p in sys_argv[1:3])
rows = []
for cid in base["raw"]:
    b, n = base["raw"][cid], new["raw"][cid]
    if n.get("status") != "completed":
        rows.append((cid, "NOT COMPLETED")); continue
    def resolved(doc, k):   # source ids are numbered in completion order: compare what they point to
        SRC.clear()
        SRC.update({s["source_id"]: (s.get("service") or "", s.get("instrument") or "", s.get("product_id") or "",
                                     s.get("status") or "") for s in doc.get("data_sources", [])})
        return strip(doc.get(k))
    diffs = [k for k in ("mineralogy", "terrestrial_analogs", "environment", "topography", "imagery", "earth_analogs",
                         "confidence") if resolved(b, k) != resolved(n, k)]
    pv = "same" if prov(b) == prov(n) else f"DIFF {set(prov(b)) ^ set(prov(n))}"
    fam = "same" if ST.families(b) == ST.families(n) else f"DIFF {ST.families(b)} -> {ST.families(n)}"
    g = n.get("geomorphology")
    rows.append((cid, f"verdict {base['verdicts'][cid]['verdict']} -> {new['verdicts'][cid]['verdict']} | families {fam} "
                      f"| sections differing {diffs or 'none'} | provenance {pv} | geomorphology "
                      f"{'absent' if g is None else g['status'] + (' experimental' if g.get('experimental') else '')}"))
for r in rows:
    print(*r)
