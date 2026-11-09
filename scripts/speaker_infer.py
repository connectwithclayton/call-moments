"""Infer who is talking without speaker labels.

Agents read from scripts, so their word sequences recur across thousands of calls; customers
improvise. For every sentence we measure how many of its n-grams are "script n-grams" (seen in at
least DF_MIN different calls). Mostly-script sentences are tagged agent, mostly-novel ones customer,
and very short ones unknown.

Usage: speaker_infer.py corpus.jsonl labels_dir [labels_dir ...] --out speaker_eval.json
Writes per-threshold accuracy against labeled quotes (agent-side vs customer-side moments) and
exposes `scorer(corpus_path)` for other scripts.
"""
import json, sys, os, glob, hashlib, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import tokens

N = 4
AGENT_MOMENTS = {"tpmo_disclaimer", "recording_notice", "medicare_affiliation_claim", "money_back_claim",
                 "transfer_to_agent", "medicare_number_request"}
CUSTOMER_MOMENTS = {"do_not_call_request", "not_interested", "already_covered", "trust_concern"}


def h(s):
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little", signed=True)


def grams(toks, n=N):
    return [h(" ".join(toks[i:i + n])) for i in range(len(toks) - n + 1)]


def build(corpus_path):
    calls, per_call = [], []
    for line in open(corpus_path):
        c = json.loads(line)
        toks = [tokens(s["x"]) for s in c["sents"]]
        g = [grams(t) for t in toks]
        calls.append((c, toks, g))
        per_call.append(np.unique(np.fromiter((x for gs in g for x in gs), dtype=np.int64)))
    allg = np.concatenate(per_call)
    keys, df = np.unique(allg, return_counts=True)
    return calls, keys, df


def script_share(g, keys, df, df_min):
    if not g:
        return None
    a = np.asarray(g, dtype=np.int64)
    idx = np.searchsorted(keys, a)
    idx[idx >= len(keys)] = 0
    found = keys[idx] == a
    d = np.where(found, df[idx], 0)
    return float((d >= df_min).mean())


def norm(s):
    return " ".join(tokens(s))


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[args.index("--out") + 1]
    corpus, label_dirs = args[0], [a for a in args[1:args.index("--out")]]
    labels = {}
    for d in label_dirs:
        for f in glob.glob(d + "/out_*.json"):
            for row in json.load(open(f)):
                labels[row["call_id"]] = row["labels"]
    calls, keys, df = build(corpus)
    print("calls", len(calls), "distinct 4-grams", len(keys))
    # labeled quotes -> (sentence 4-grams, side)
    items = []
    for c, toks, g in calls:
        L = labels.get(c["id"])
        if not L:
            continue
        joined = [" " + " ".join(t) + " " for t in toks]
        for m, v in L.items():
            if not v.get("present") or not v.get("quote"):
                continue
            q = " " + norm(v["quote"]) + " "
            hit = [i for i, s in enumerate(joined) if q.strip() and q in s]
            if not hit:
                continue
            i = min(hit, key=lambda k: abs(c["sents"][k]["t"] - (v.get("t") or 0)))
            side = "agent" if m in AGENT_MOMENTS else "customer" if m in CUSTOMER_MOMENTS else None
            if side:
                items.append((g[i], side, m, len(toks[i])))
    print("labeled sentences located", len(items), {s: sum(1 for x in items if x[1] == s) for s in ("agent", "customer")})
    res = []
    for df_min in (10, 20, 40, 80, 160):
        scores = [(script_share(g, keys, df, df_min), side, m) for g, side, m, _ in items]
        for thr in (0.3, 0.4, 0.5, 0.6, 0.7):
            tab = {"agent": [0, 0, 0], "customer": [0, 0, 0]}  # [called agent, called customer, unknown]
            for sc, side, m in scores:
                k = 2 if sc is None else (0 if sc >= thr else 1)
                tab[side][k] += 1
            ag, cu = tab["agent"], tab["customer"]
            known = ag[0] + ag[1] + cu[0] + cu[1]
            acc = (ag[0] + cu[1]) / known if known else 0
            res.append({"df_min": df_min, "thr": thr, "agent": ag, "customer": cu, "acc_known": round(acc, 3),
                        "cust_recall": round(cu[1] / max(1, cu[0] + cu[1]), 3),
                        "agent_recall": round(ag[0] / max(1, ag[0] + ag[1]), 3)})
    res.sort(key=lambda r: -(r["cust_recall"] + r["agent_recall"]))
    for r in res[:8]:
        print(r)
    json.dump(res, open(out, "w"), indent=1)


def tag_corpus(corpus_path, df_min=20, thr=0.4):
    """Return {call_id: 'a'/'c'/'u' per sentence}: agent-like, customer-like, unknown (3 words or fewer)."""
    calls, keys, df = build(corpus_path)
    out = {}
    for c, toks, g in calls:
        tags = []
        for gs in g:
            sc = script_share(gs, keys, df, df_min)
            tags.append("u" if sc is None else ("a" if sc >= thr else "c"))
        out[c["id"]] = "".join(tags)
    return out
