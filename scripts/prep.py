"""Build a private, sentence-level corpus from the insurance_outbound transcripts.
Call IDs are replaced with C#### because the source filenames look like phone numbers."""
import json, sys, glob, re, statistics, hashlib
src, out_corpus, out_map = sys.argv[1], sys.argv[2], sys.argv[3]
files = sorted(glob.glob(src + '/*.json'))
END = re.compile(r'[.?!]["\')\]]*$')
calls = []; idmap = {}
for i, f in enumerate(files, 1):
    d = json.load(open(f))
    words = d.get('words') or []
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if END.search(w['text']) or len(cur) >= 60:
            sents.append(cur); cur = []
    if cur: sents.append(cur)
    S = []
    for s in sents:
        txt = ' '.join(w['text'] for w in s).strip()
        if not txt: continue
        conf = statistics.mean(w.get('confidence') or 0 for w in s)
        S.append({'t': round(s[0]['start']/1000, 1), 'e': round(s[-1]['end']/1000, 1), 'x': txt, 'c': round(conf, 3)})
    cid = f'C{i:04d}'
    idmap[cid] = hashlib.sha256(f.encode()).hexdigest()[:12]   # private trace key, no filename kept
    calls.append({'id': cid, 'dur': d.get('audio_duration') or (S[-1]['e'] if S else 0), 'conf': round(d.get('confidence') or 0, 3),
                  'nwords': len(words), 'sents': S})
with open(out_corpus, 'w') as fo:
    for c in calls: fo.write(json.dumps(c) + '\n')
json.dump(idmap, open(out_map, 'w'))
durs = sorted(c['dur'] for c in calls); nw = sorted(c['nwords'] for c in calls)
print('calls', len(calls), '| hours', round(sum(durs)/3600, 1), '| median dur s', durs[len(durs)//2], '| p10/p90', durs[len(durs)//10], durs[9*len(durs)//10])
print('median words', nw[len(nw)//2], '| sentences', sum(len(c['sents']) for c in calls), '| mean ASR conf', round(statistics.mean(c['conf'] for c in calls), 3))
print('calls under 30s', sum(1 for d in durs if d < 30), '| over 15 min', sum(1 for d in durs if d > 900))
