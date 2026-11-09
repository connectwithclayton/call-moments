"""Every phrase should catch something. Count sentence hits per phrase over the corpus and flag dead phrases.
Usage: lint.py corpus.jsonl rules.json"""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import tokens, phrase_regex
corpus, rules_path = sys.argv[1:3]
rules = json.load(open(rules_path))
items = []
for r in rules:
    for kind in ('any', 'not_in'):
        for p in r.get(kind, []):
            items.append((r['id'], kind, p, phrase_regex(p)))
    for k, sub in enumerate(r.get('also', [])):
        for kind in ('any', 'not_in', 'prev'):
            for p in sub.get(kind, []):
                items.append((f"{r['id']}+{k}", kind, p, phrase_regex(p)))
hits = collections.Counter()
for line in open(corpus):
    c = json.loads(line)
    for s in c['sents']:
        st = " " + " ".join(tokens(s['x'])) + " "
        for j, (_, _, _, rx) in enumerate(items):
            if rx.search(st):
                hits[j] += 1
dead = [(rid, kind, p) for j, (rid, kind, p, _) in enumerate(items) if hits[j] == 0]
print(f'{len(items)} phrases checked; {len(dead)} never match a sentence in the corpus')
for d in dead: print('  DEAD', d)
