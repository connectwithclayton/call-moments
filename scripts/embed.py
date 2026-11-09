"""Score customer-side sentences against each moment's example utterances (semantic matching).

Embeds every sentence tagged customer or unknown (two or more words) in the chosen calls with
BAAI/bge-small-en-v1.5 (fastembed, CPU), embeds the example utterances, and keeps each sentence's
best cosine similarity per moment when it is at least FLOOR.

Usage: embed.py corpus.jsonl speaker_tags.json utterances.json ids.json [ids.json ...] --out sims.json
Output: {call_id: {moment: {sentence_index: similarity}}}
"""
import json, sys, os, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import tokens

FLOOR = 0.55
MODEL = "BAAI/bge-small-en-v1.5"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")


def load_ids(path):
    d = json.load(open(path))
    return {x["id"] if isinstance(x, dict) else x for x in d}


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[args.index("--out") + 1]
    corpus, tags_path, utt_path = args[:3]
    ids = set()
    for p in args[3:args.index("--out")]:
        ids |= load_ids(p)
    tags = json.load(open(tags_path))
    utt = json.load(open(utt_path))
    texts, where = {}, []
    for line in open(corpus):
        c = json.loads(line)
        if c["id"] not in ids:
            continue
        tg = tags[c["id"]]
        for i, s in enumerate(c["sents"]):
            if tg[i] == "a" or len(tokens(s["x"])) < 2:
                continue
            k = texts.setdefault(s["x"].strip(), len(texts))
            where.append((c["id"], i, k))
    order = sorted(texts, key=len)
    print(f"calls {len(ids)} | sentences {len(where)} | distinct {len(order)}", flush=True)
    from fastembed import TextEmbedding
    m = TextEmbedding(MODEL, cache_dir=CACHE)
    ex_keys = list(utt)
    ex = {k: np.array(list(m.embed(utt[k]))) for k in ex_keys}
    for k in ex_keys:
        ex[k] /= np.linalg.norm(ex[k], axis=1, keepdims=True)
    vec = {}
    t0 = time.time()
    B = 128
    for j in range(0, len(order), B):
        chunk = order[j:j + B]
        V = np.array(list(m.embed(chunk, batch_size=B)))
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        for text, v in zip(chunk, V):
            vec[text] = v
        if (j // B) % 20 == 0:
            done = j + len(chunk)
            print(f"  {done}/{len(order)} in {time.time()-t0:.0f}s", flush=True)
    best = {}
    for text, v in vec.items():
        best[texts[text]] = {k: float((ex[k] @ v).max()) for k in ex_keys}
    res = {}
    for cid, i, k in where:
        for mom, sc in best[k].items():
            if sc >= FLOOR:
                res.setdefault(cid, {}).setdefault(mom, {})[i] = round(sc, 3)
    json.dump(res, open(out, "w"), separators=(",", ":"))
    print(f"done in {time.time()-t0:.0f}s; calls with any score {len(res)}", flush=True)
