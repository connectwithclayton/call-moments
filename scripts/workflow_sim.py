"""Replay every call the way a disclaimer-before-benefits workflow would see it live.

CMS's CY2027 marketing rules (in force since Oct 1, 2026) say a third-party marketer must give
its disclaimer before any benefits are discussed. Built in a no-code tool such as Cresta Opera,
the workflow has three parts:
  1. A checklist item, "Disclaimer: not yet read", shows from the start of the call and clears
     when the disclaimer rule fires.
  2. If the first specific benefit comes up while the item is still open, an urgent prompt fires.
  3. After the call, a call where benefits came before the disclaimer goes to compliance review.

The replay uses the recordings that start with the first agent (late starts are set aside; see
analysis_success.py). It reports how often each step fires and when, and the share of calls each
compliance rule would alert on if it ran live, so a rule's grade and its noise decide its action.

The calls are undated (the dataset was published in mid-2025) and some may predate the disclaimer
rule, which began in October 2022. So this measures how far scripts of that era are from the new
rule, not how well agents followed it.

Usage: workflow_sim.py corpus.jsonl analysis_final.json speaker_tags.json rules/benefit_mention.json
       analysis_success.json out.json private_spot_sample.json
"""
import json, os, random, statistics, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import load_rules, run_call

corpus, final, tags_path, benefit_rules, success, out, spot_out = sys.argv[1:8]
H = json.load(open(final))["hits_by_call"]
TAGS = json.load(open(tags_path))
BEN = load_rules(benefit_rules)
LATE = set(json.load(open(success))["late_start_ids"])

calls = {}
for line in open(corpus):
    c = json.loads(line)
    calls[c["id"]] = c
front = [i for i in sorted(calls) if i not in LATE]
hours = sum(calls[i]["dur"] for i in front) / 3600
first = lambda i, m: H[i][m][0] if m in H[i] else None

ben = {}
for i in front:
    c = dict(calls[i]); c["sp"] = TAGS.get(i, "")
    hit = run_call(BEN, c).get("benefit_d1")
    if hit:
        ben[i] = hit

with_b = [i for i in front if i in ben]
tb = sorted(ben[i]["t"] for i in with_b)
q = lambda f: round(tb[int(f * (len(tb) - 1))])
disc = [i for i in front if first(i, "tpmo_disclaimer") is not None]
disc_before = [i for i in with_b if first(i, "tpmo_disclaimer") is not None and first(i, "tpmo_disclaimer") < ben[i]["t"]]
prompt = [i for i in with_b if i not in set(disc_before)]
first_word = Counter(ben[i]["hit"].split()[0] if ben[i]["hit"] else "?" for i in with_b)

both = [i for i in with_b if first(i, "tpmo_disclaimer") is not None]
gaps = sorted((first(i, "tpmo_disclaimer") - ben[i]["t"]) / 60 for i in both)
R = {"recordings_from_start": len(front), "recorded_hours": round(hours, 1),
     "with_benefit_mention": len(with_b), "with_benefit_pct": round(100 * len(with_b) / len(front), 1),
     "first_benefit_seconds": {"p25": q(.25), "median": q(.5), "p75": q(.75)},
     "first_benefit_within_60s_pct": round(100 * sum(t < 60 for t in tb) / len(tb), 1),
     "disclaimer_any": len(disc),
     "disclaimer_median_seconds": round(statistics.median(first(i, "tpmo_disclaimer") for i in disc)) if disc else None,
     "disclaimer_before_first_benefit": len(disc_before),
     "benefit_calls_without_disclaimer": len(with_b) - len(both),
     "benefit_calls_with_disclaimer": len(both),
     "benefit_first_gap_minutes": {"min": round(gaps[0], 1), "median": round(gaps[len(gaps) // 2], 1), "max": round(gaps[-1], 1)} if gaps else None,
     "urgent_prompt_calls": len(prompt), "urgent_prompt_pct": round(100 * len(prompt) / len(front), 1),
     "first_benefit_words": first_word.most_common(8)}

# the share of calls each compliance rule would alert on if it ran live (at most one alert per call)
handoff = lambda i: first(i, "transfer_to_agent")
budget = {}
for m in ("medicare_affiliation_claim", "money_back_claim", "recording_notice", "do_not_call_request", "no_more_calls_promise"):
    if m == "recording_notice":  # the alert is the notice missing before the handoff (or from a call with no handoff)
        fires = [i for i in front if first(i, m) is None or (handoff(i) is not None and first(i, m) >= handoff(i))]
        label = "no recording notice before the handoff"
    else:
        fires = [i for i in front if first(i, m) is not None]
        label = m
    budget[m] = {"fires_on": label, "calls": len(fires), "pct": round(100 * len(fires) / len(front), 1)}
budget["tpmo_disclaimer"] = {"fires_on": "benefit before the disclaimer (urgent prompt)", "calls": len(prompt), "pct": R["urgent_prompt_pct"]}
R["alert_budget"] = budget
rn = [i for i in front if first(i, "recording_notice") is not None]
R["recording_notice"] = {"any_pct": round(100 * len(rn) / len(front), 1), "none_pct": round(100 * (len(front) - len(rn)) / len(front), 1),
                         "before_detected_handoff_pct": round(100 * sum(1 for i in rn if handoff(i) is not None and first(i, "recording_notice") < handoff(i)) / len(front), 1),
                         "first_minute_pct": round(100 * sum(first(i, "recording_notice") < 60 for i in rn) / len(front), 1)}

# the 44 disclaimers across all recordings: did a specific benefit come first?
dall = [i for i in sorted(calls) if first(i, "tpmo_disclaimer") is not None]
def ben_t(i):
    if i in ben:
        return ben[i]["t"]
    c = dict(calls[i]); c["sp"] = TAGS.get(i, "")
    h = run_call(BEN, c).get("benefit_d1")
    return h["t"] if h else None
bt = {i: ben_t(i) for i in dall}
R["disclaimer_calls_all_recordings"] = {"calls": len(dall),
                                        "benefit_first": sum(1 for i in dall if bt[i] is not None and bt[i] < first(i, "tpmo_disclaimer")),
                                        "disclaimer_first": sum(1 for i in dall if bt[i] is not None and bt[i] >= first(i, "tpmo_disclaimer")),
                                        "no_benefit_detected": sum(1 for i in dall if bt[i] is None)}

# private sample for an independent precision check of the benefit trigger (holds transcript text)
random.seed(20261109)
sample = []
for i in random.sample(with_b, 25):
    k = ben[i]["i"]; s = calls[i]["sents"]
    sample.append({"id": i, "t": round(ben[i]["t"]), "before": s[k - 1]["x"] if k else "", "sentence": s[k]["x"],
                   "after": s[k + 1]["x"] if k + 1 < len(s) else ""})
json.dump(sample, open(spot_out, "w"), indent=1)
json.dump(R, open(out, "w"), indent=1)
print(json.dumps(R, indent=1))
