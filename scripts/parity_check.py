"""Check that the Python and JavaScript engines agree on every hit.
Usage: python scripts/parity_check.py work/corpus.jsonl rules/rules_v4.json [work/speaker_tags.json]"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import load_rules, run_call

corpus, rules_path = sys.argv[1:3]
tags = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
calls = [json.loads(l) for l in open(corpus)][:400]
for c in calls:
    if c["id"] in tags: c["sp"] = tags[c["id"]]
rules = load_rules(rules_path)
py = {c["id"]: run_call(rules, c) for c in calls}
js_src = """
const E = require(process.argv[2]); const fs = require('fs');
const rules = JSON.parse(fs.readFileSync(process.argv[3])).map(E.compile);
const calls = JSON.parse(fs.readFileSync(process.argv[4])); const out = {};
for (const c of calls) out[c.id] = E.runCall(rules, c);
fs.writeFileSync(process.argv[5], JSON.stringify(out));"""
with tempfile.TemporaryDirectory() as d:
    open(f"{d}/p.js", "w").write(js_src)
    json.dump([{"id": c["id"], "sents": [{"t": s["t"], "x": s["x"]} for s in c["sents"]], "sp": c.get("sp", "")} for c in calls], open(f"{d}/c.json", "w"))
    subprocess.run(["node", f"{d}/p.js", os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine.js"), rules_path, f"{d}/c.json", f"{d}/o.json"], check=True)
    js = json.load(open(f"{d}/o.json"))
hits = sum(len(v) for v in py.values())
bad = sum(1 for cid in py for rid in set(py[cid]) | set(js[cid])
          if (rid in py[cid]) != (rid in js[cid]) or (rid in py[cid] and py[cid][rid]["i"] != js[cid][rid]["i"]))
print(f"{len(calls)} calls, {len(rules)} rules, {hits} hits, {bad} mismatches")
sys.exit(1 if bad else 0)
