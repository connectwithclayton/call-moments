"""Grade every rule against an explicit usability bar, from the frozen held-out scores.

Levels (held-out calls, final version or its recall-mode variant):
  ready      precision >= 0.90 and recall >= 0.80, at least MIN_POS positives: safe for live alerts and rate reporting
  qa         recall >= 0.80 and precision >= 0.50: catches most cases, but a person checks every flag
  not_yet    below both bars
  too_rare   fewer than MIN_POS held-out positives: can't be graded; use only with a person reading every flag
Discovered moments have no labels, so they are 'exploratory' (precision spot-checked, recall unknown).

Usage: readiness.py eval_counts.json moments.json site_extra.json out.json
"""
import json, sys

LIVE_P, LIVE_R, QA_P, QA_R, MIN_POS = 0.90, 0.80, 0.50, 0.80, 10
ec, moments, extra, out = sys.argv[1:5]
rows = json.load(open(ec))["heldout"]["rows"]
M = json.load(open(moments))
X = json.load(open(extra))

LABEL = {"ready": "Ready", "qa": "QA only", "not_yet": "Not yet", "too_rare": "Too rare to test", "exploratory": "Exploratory"}
USE = {"ready": "Live alerts and rate reporting", "qa": "A QA queue where a person checks each flag",
       "not_yet": "Not for use yet", "too_rare": "Only with a person reading every flag",
       "exploratory": "Reading calls and sampling; not for rates"}


def grade(r):
    p = r["correct"] / r["flags"] if r["flags"] else None
    rc = r["caught"] / r["positives"] if r["positives"] else None
    if r["positives"] < MIN_POS:
        lvl = "too_rare"
    elif p is not None and p >= LIVE_P and rc >= LIVE_R:
        lvl = "ready"
    elif p is not None and rc >= QA_R and p >= QA_P:
        lvl = "qa"
    else:
        lvl = "not_yet"
    return lvl, p, rc


order = ["ready", "qa", "not_yet", "too_rare"]
res = {}
for m in M:
    k = m["key"]
    if m.get("discovered"):
        s = X["spot"].get(k, {})
        lvl = "exploratory" if s.get("n") and s["correct"] / s["n"] >= 0.80 else "not_yet"
        res[k] = {"level": lvl, "label": LABEL[lvl], "use": USE[lvl],
                  "precision": s.get("correct", 0) / s["n"] if s.get("n") else None, "recall": None,
                  "evidence": f"{s.get('correct')} of {s.get('n')} random hits judged right; recall not measured"}
        continue
    cands = [r for r in rows if r["moment"] == k and r["version"] in ("v4", "v4r")]
    best = None
    for r in cands:
        lvl, p, rc = grade(r)
        if best is None or order.index(lvl) < order.index(best[0]):
            best = (lvl, p, rc, r)
    lvl, p, rc, r = best
    ev = f"held-out: {r['correct']} of {r['flags']} flags right, {r['caught']} of {r['positives']} cases caught"
    if lvl == "too_rare":
        ev = "no held-out cases" if r["positives"] == 0 else f"only {r['positives']} held-out case{'' if r['positives'] == 1 else 's'}"
    if r["version"] == "v4r":
        ev += " (recall mode)"
    res[k] = {"level": lvl, "label": LABEL[lvl], "use": USE[lvl], "precision": p, "recall": rc, "variant": r["version"],
              "flags": r["flags"], "correct": r["correct"], "positives": r["positives"], "caught": r["caught"], "evidence": ev}
if res["transfer_to_agent"]["level"] == "ready":
    res["transfer_to_agent"]["use"] = "Rate reporting: it is the conversion outcome"
# extra evidence for the rare moments
res["do_not_call_request"]["evidence"] += "; every flagged call read by an independent reviewer: 13 of 16 were real"
res["tpmo_disclaimer"]["evidence"] += "; tuning set: 21 of 21 flags right; labels on 250 random calls find it in 1.2%, rules in 1.1%"
json.dump({"bars": {"live_precision": LIVE_P, "live_recall": LIVE_R, "qa_precision": QA_P, "qa_recall": QA_R, "min_positives": MIN_POS},
           "levels": LABEL, "uses": USE, "moments": res}, open(out, "w"), indent=1)
for k, v in res.items():
    print(f"{k:28} {v['label']:17} {v['evidence']}")
