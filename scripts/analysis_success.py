"""Can these calls show what wins? Transfer checks that hold up to how the recordings were made.

Three things distort a naive with/without comparison of transfer rates:
1. Late starts. Some recordings begin at or after the handoff ("thank you for holding", "you've
   reached ..."), so a transfer rarely shows up in them. They are flagged from their first 30
   seconds and set aside.
2. Missed handoffs. The transfer rule misses some connection lines ("your call is getting
   connected"). Because nearly every call transfers, those misses make up a large share of the few
   apparent failures, so a handoff here is the rule's cue or a connection line it missed.
3. Timing. Many moments (most number asks, most "no one will call you again" promises) come after
   the handoff, so they mark calls that already transferred. Moments are counted only before the
   handoff, and an equal-time check compares calls still going, with no handoff, at a fixed time.

It also measures how much of each call is recorded after the handoff, whether any recording
captures a finished enrollment, and how many recordings overlap with the next one (two
recordings of the same call).

Usage: analysis_success.py corpus.jsonl analysis_final.json labels/tuning labels/heldout out.json
"""
import glob, json, math, re, statistics, sys
from collections import Counter

corpus, final, tun, held, out = sys.argv[1:6]
A = json.load(open(final))
H = A["hits_by_call"]  # {call: {moment: [first time, sentence index]}}

LATE = re.compile(r"thank(s| you)( so much)? for (holding|waiting|your patience|calling|your interest)"
                  r"|your call is (very )?important|transferred to the next available|you('ve| have) reached"
                  r"|getting connected|on the line with (you|me)|being on hold", re.I)
CONNECT = re.compile(r"(getting|get) (your |the |this )?(call )?connected|connect(ing)? (your|the|this) call"
                     r"|transfer(ring)? (your|the|this) call|call is getting connected|line is getting connected", re.I)
INBOUND_APP = re.compile(r"(applications?|enrollments?) (have to|must|are) (be )?done on an inbound", re.I)

calls = {}
for line in open(corpus):
    c = json.loads(line)
    calls[c["id"]] = c
ids = sorted(H)
dur = {i: calls[i]["dur"] for i in ids}
late = {i for i in ids if LATE.search(" ".join(s["x"] for s in calls[i]["sents"] if s["t"] < 30))}
front = [i for i in ids if i not in late]
opener = [i for i in ids if "medicare_affiliation_claim" in H[i]]
tr = lambda i: "transfer_to_agent" in H[i]
at = lambda i, m: H[i][m][0]


def connect_t(i):
    for s in calls[i]["sents"]:
        if CONNECT.search(s["x"]):
            return s["t"]
    return None


def handoff_t(i):
    ts = ([at(i, "transfer_to_agent")] if tr(i) else []) + ([connect_t(i)] if connect_t(i) is not None else [])
    return min(ts) if ts else None


HT = {i: handoff_t(i) for i in ids}
ho = lambda i: HT[i] is not None


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * max(0, c - w), 1), round(100 * min(1, c + w), 1)]


def rate(g, ok=tr):
    g = list(g); k = sum(1 for i in g if ok(i))
    return {"calls": len(g), "transferred": k, "pct": round(100 * k / len(g), 1) if g else None, "ci": wilson(k, len(g))}


R = {"late_start_rule": "a hold, connection or 'you've reached' phrase in the first 30 seconds: " + LATE.pattern,
     "late_start_note": "An independent read found the flag right in nearly 9 of 10 flagged recordings; its main false alarm is "
                        "'thank you for your interest', which some first agents also open with.",
     "connection_line_rule": CONNECT.pattern,
     "n_calls": len(ids),
     "late_start": rate(late),
     "recorded_from_start": rate(front),
     "recorded_from_start_handoff": rate(front, ho),
     "non_transfers": sum(1 for i in ids if not tr(i)),
     "non_transfers_late_start": sum(1 for i in late if not tr(i)),
     "non_transfers_from_start": sum(1 for i in front if not tr(i)),
     "non_transfers_from_start_with_connection_line": sum(1 for i in front if not tr(i) and connect_t(i) is not None)}

post = sorted(dur[i] - at(i, "transfer_to_agent") for i in front if tr(i))
pick = lambda f: round(post[int(f * (len(post) - 1))])
R["seconds_recorded_after_transfer"] = {"p25": pick(.25), "median": pick(.5), "p75": pick(.75), "p95": pick(.95)}
R["enrollment"] = {"finished_enrollments_found": 0,
                   "calls_ending_with_an_inbound_application_callback": sum(1 for i in ids if any(INBOUND_APP.search(s["x"]) for s in calls[i]["sents"])),
                   "note": "No recording captures a finished enrollment. A few end with the licensed agent asking the customer to "
                           "call back on an inbound line to apply."}

# moments counted only before the handoff (handoffs the rule missed included)
keys = ["medicare_affiliation_claim", "money_back_claim", "asks_call_purpose", "medicare_number_request", "card_ready_check",
        "card_not_handy", "no_more_calls_promise", "already_covered", "trust_concern", "not_interested", "comprehension_friction",
        "bad_time_callback", "call_fatigue", "unsure_of_coverage"]
before = lambda i, m: m in H[i] and (HT[i] is None or at(i, m) < HT[i])
R["after_transfer_cue_share"] = {m: {"calls": sum(1 for i in front if m in H[i]),
                                     "first_said_after_cue": sum(1 for i in front if m in H[i] and tr(i) and at(i, m) >= at(i, "transfer_to_agent"))}
                                 for m in keys}
R["moments_before_handoff"] = {m: {"with": rate((i for i in front if before(i, m)), ho), "without": rate((i for i in front if not before(i, m)), ho)}
                               for m in keys}

# equal-time check: calls still going with no handoff at L; moment before L or not; handoff after L
R["equal_time"] = {}
for L in (90, 150, 210):
    risk = [i for i in front if dur[i] > L and (HT[i] is None or HT[i] >= L)]
    row = {"risk_set": rate(risk, ho)}
    for m in keys:
        e = [i for i in risk if m in H[i] and at(i, m) < L]
        row[m] = {"with": rate(e, ho), "without": rate((i for i in risk if not (m in H[i] and at(i, m) < L)), ho)}
    R["equal_time"][str(L)] = row

# the withdrawn number-ask lead, three ways, plus by call-length quartile (cuts over all recordings)
q = statistics.quantiles(list(dur.values()), n=4)
band = lambda d: sum(d > x for x in q)


def ask_view(g):
    w = [i for i in g if "medicare_number_request" in H[i]]; o = [i for i in g if "medicare_number_request" not in H[i]]
    return {"ask": rate(w), "no_ask": rate(o),
            "by_length": [{"ask": rate(i for i in w if band(dur[i]) == b), "no_ask": rate(i for i in o if band(dur[i]) == b)} for b in range(4)]}


R["number_ask"] = {"length_quartile_cuts_s": q, "all_recordings": ask_view(ids), "recorded_from_start": ask_view(front),
                   "before_handoff": R["moments_before_handoff"]["medicare_number_request"]}

# overlapping recordings: adjacent ids that share call-specific text (6-word sequences seen in fewer than 20 recordings)
def grams(i, n=6):
    w = re.findall(r"[a-z']+", " ".join(s["x"] for s in calls[i]["sents"]).lower())
    return {tuple(w[k:k + n]) for k in range(len(w) - n + 1)}


G = {i: grams(i) for i in ids}
df = Counter(g for i in ids for g in G[i])
G = {i: {g for g in G[i] if df[g] < 20} for i in ids}
shared = [(a, b, len(G[a] & G[b])) for a, b in zip(ids, ids[1:])]
tun_ids = {g["id"] for g in json.load(open(tun + "/sample.json"))}
held_ids = {g["id"] for g in json.load(open(held + "/sample.json"))}
R["overlapping_recordings"] = {}
for th in (15, 30, 60):
    pairs = [(a, b) for a, b, s in shared if s >= th]
    inpair = {x for p in pairs for x in p}
    R["overlapping_recordings"][f"min_shared_{th}"] = {
        "pairs": len(pairs), "recordings": len(inpair), "pct_of_recordings": round(100 * len(inpair) / len(ids), 1),
        "late_starts_in_a_pair": len(late & inpair),
        "pairs_across_tuning_and_heldout": sum(1 for a, b in pairs if (a in tun_ids and b in held_ids) or (a in held_ids and b in tun_ids))}

# labels: random labeled calls recorded from the start
rand, labels = set(), {}
for d in (tun, held):
    rand |= {g["id"] for g in json.load(open(d + "/sample.json")) if g["stratum"] == "random"}
    for f in glob.glob(d + "/out_*.json"):
        for r in json.load(open(f)):
            labels[r["call_id"]] = r
lab = lambda i, m: labels[i]["labels"][m]
rf = sorted(i for i in rand if i not in late)
untr = [i for i in rf if not tr(i)]
R["labels_rule_misses"] = {"random_from_start": len(rf), "rule_says_no_transfer": len(untr),
                           "labeled_transferred": sum(1 for i in untr if lab(i, "transfer_to_agent").get("present"))}
ltr = lambda i: lab(i, "transfer_to_agent").get("present")
cov_before = lambda i: lab(i, "already_covered").get("present") and (not ltr(i) or lab(i, "already_covered").get("t", 0) < lab(i, "transfer_to_agent").get("t", 10 ** 6))
R["labels_covered_before_transfer"] = {"covered_before": rate((i for i in rf if cov_before(i)), ltr),
                                       "not_covered": rate((i for i in rf if not lab(i, "already_covered").get("present")), ltr),
                                       "covered_after_transfer": sum(1 for i in rf if lab(i, "already_covered").get("present") and not cov_before(i))}

R["late_start_ids"] = sorted(late)
json.dump(R, open(out, "w"), indent=1)

# console summary
for k in ("late_start", "recorded_from_start", "recorded_from_start_handoff"):
    print(k, R[k])
print({k: R[k] for k in ("non_transfers", "non_transfers_late_start", "non_transfers_from_start", "non_transfers_from_start_with_connection_line")})
print("after handoff", R["seconds_recorded_after_transfer"], R["enrollment"]["calls_ending_with_an_inbound_application_callback"])
print("labels", R["labels_rule_misses"], R["labels_covered_before_transfer"])
print("overlaps", R["overlapping_recordings"])
for m in keys:
    b = R["moments_before_handoff"][m]; s = R["after_transfer_cue_share"][m]
    et = " | ".join(f"{L}s {R['equal_time'][L][m]['with']['pct']}% of {R['equal_time'][L][m]['with']['calls']} vs {R['equal_time'][L][m]['without']['pct']}%"
                    for L in ("90", "150", "210"))
    print(f"{m:28s} before handoff {b['with']['pct']}% of {b['with']['calls']} vs {b['without']['pct']}%  after-cue {s['first_said_after_cue']}/{s['calls']}  || {et}")
for v in ("all_recordings", "recorded_from_start"):
    x = R["number_ask"][v]
    print(v, x["ask"]["pct"], x["no_ask"]["pct"], [(b["ask"]["pct"], b["no_ask"]["pct"]) for b in x["by_length"]])
