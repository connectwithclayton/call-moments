"""Score rules against the labeled sample.
Recall and prevalence use only the random part of the sample; precision uses every labeled call
(the enriched calls only add more chances for rare rules to fire).
Usage: evaluate.py corpus.jsonl rules.json gold_sample.json labels_dir out.json [--sp speaker_tags.json] [--u sims.json]"""
import json, sys, glob, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import load_rules, run_call

corpus, rules_path, gold_path, labels_dir, out_path = sys.argv[1:6]
opt = dict(zip(sys.argv[6::2], sys.argv[7::2]))
TAGS = json.load(open(opt['--sp'])) if '--sp' in opt else {}
SIMS = json.load(open(opt['--u'])) if '--u' in opt else {}
strata = {g['id']: g['stratum'] for g in json.load(open(gold_path))}
labels = {}
for f in sorted(glob.glob(labels_dir + '/out_*.json')):
    for row in json.load(open(f)):
        labels[row['call_id']] = row
calls = {c['id']: c for c in map(json.loads, open(corpus)) if c['id'] in labels}
for cid, c in calls.items():
    if cid in TAGS: c['sp'] = TAGS[cid]
    if cid in SIMS: c['u'] = {m: {int(i): v for i, v in d.items()} for m, d in SIMS[cid].items()}
rules = load_rules(rules_path)
hits = {cid: run_call(rules, c) for cid, c in calls.items()}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def present(cid, moment):
    return bool(labels[cid]['labels'].get(moment, {}).get('present'))


rows = []
for r in rules:
    tp = fp = fn = 0
    rtp = rfp = rfn = rpos = rn = 0
    fps, fns = [], []
    for cid in calls:
        y, yhat = present(cid, r.moment), r.id in hits[cid]
        rand = strata.get(cid) == 'random'
        if yhat and y: tp += 1
        if yhat and not y:
            fp += 1; fps.append(cid)
        if y and not yhat:
            fn += 1
        if rand:
            rn += 1; rpos += y
            if yhat and y: rtp += 1
            if yhat and not y: rfp += 1
            if y and not yhat:
                rfn += 1; fns.append(cid)
    prec = tp / (tp + fp) if tp + fp else None
    rec = rtp / (rtp + rfn) if rtp + rfn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else None
    rows.append({
        'rule': r.id, 'moment': r.moment, 'version': r.version,
        'precision': prec, 'precision_ci': wilson(tp, tp + fp), 'fires': tp + fp,
        'recall': rec, 'recall_ci': wilson(rtp, rtp + rfn), 'positives_random': rtp + rfn,
        'f1': f1, 'labeled_prevalence_random': rpos / rn if rn else None, 'n_random': rn,
        'rule_rate_random': (rtp + rfp) / rn if rn else None,
        'false_positive_calls': fps[:12], 'missed_calls': fns[:12],
    })
json.dump({'n_labeled': len(calls), 'n_random': sum(1 for c in calls if strata.get(c) == 'random'), 'rules': rows},
          open(out_path, 'w'), indent=1)
fmt = lambda v: '  -  ' if v is None else f'{v:5.2f}'
print(f"labeled calls: {len(calls)} (random {sum(1 for c in calls if strata.get(c) == 'random')})")
print(f"{'rule':16} {'prec':>5} {'fires':>5} {'recall':>6} {'pos':>4} {'f1':>5} {'label%':>6} {'rule%':>6}")
for x in rows:
    print(f"{x['rule']:16} {fmt(x['precision'])} {x['fires']:5d} {fmt(x['recall']):>6} {x['positives_random']:4d} {fmt(x['f1'])} "
          f"{100*(x['labeled_prevalence_random'] or 0):6.1f} {100*(x['rule_rate_random'] or 0):6.1f}")
