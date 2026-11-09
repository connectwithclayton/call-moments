"""Whole-corpus findings from the final rules (v4 keyword rules plus the discovered-moment rules).

Usage: analysis_final.py corpus.jsonl rules_v4.json rules_discovered.json speaker_tags.json out.json
Utterance matching is left out here: similarity scores exist only for the labeled and benchmark
calls, so corpus-wide rates use the keyword part of each rule.
"""
import json, sys, os, statistics, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import load_rules, run_call, tokens

corpus, v4_path, disc_path, tags_path, out_path = sys.argv[1:6]
TAGS = json.load(open(tags_path))
rules = load_rules(v4_path) + load_rules(disc_path)
M = {r.moment: r for r in rules}
calls = []
for line in open(corpus):
    c = json.loads(line)
    c['sp'] = TAGS[c['id']]
    calls.append(c)
N = len(calls)
H = {c['id']: run_call(rules, c) for c in calls}


def hit(c, m):
    return H[c['id']].get(M[m].id)


def has(c, m, before=None, after=None):
    h = hit(c, m)
    if not h:
        return False
    if before is not None and h['t'] > before:
        return False
    if after is not None and h['t'] < after:
        return False
    return True


def t(c, m):
    h = hit(c, m)
    return h['t'] if h else None


def pct(k, n):
    return round(100 * k / n, 1) if n else None


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * max(0, ctr - hw), 1), round(100 * min(1, ctr + hw), 1)]


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


out = {'n_calls': N, 'hours': round(sum(c['dur'] for c in calls) / 3600, 1),
       'median_duration_s': med(c['dur'] for c in calls)}
out['prevalence'] = {}
for m in M:
    k = sum(has(c, m) for c in calls)
    out['prevalence'][m] = {'calls': k, 'pct': pct(k, N), 'ci': wilson(k, N),
                            'median_first_s': med(t(c, m) for c in calls)}

# ---------- compliance at the open ----------
aff = [c for c in calls if has(c, 'medicare_affiliation_claim')]
out['compliance'] = {
    'affiliation_pct': pct(len(aff), N),
    'affiliation_first_minute_pct': pct(sum(has(c, 'medicare_affiliation_claim', before=60) for c in calls), N),
    'affiliation_median_s': med(t(c, 'medicare_affiliation_claim') for c in aff),
    'tpmo_pct': pct(sum(has(c, 'tpmo_disclaimer') for c in calls), N),
    'tpmo_calls': sum(has(c, 'tpmo_disclaimer') for c in calls),
    'tpmo_first_minute_pct': pct(sum(has(c, 'tpmo_disclaimer', before=60) for c in calls), N),
    'tpmo_first_minute_calls': sum(has(c, 'tpmo_disclaimer', before=60) for c in calls),
    'recording_pct': pct(sum(has(c, 'recording_notice') for c in calls), N),
    'recording_first_minute_pct': pct(sum(has(c, 'recording_notice', before=60) for c in calls), N),
    'moneyback_pct': pct(sum(has(c, 'money_back_claim') for c in calls), N),
    'affiliation_with_moneyback_pct_of_aff': pct(sum(has(c, 'money_back_claim') for c in aff), len(aff)),
    'affiliation_without_tpmo_pct': pct(sum(not has(c, 'tpmo_disclaimer') for c in aff), len(aff)),
    'both_claims_pct': pct(sum(has(c, 'money_back_claim') for c in aff), N),
}

# ---------- do-not-call handling (every request is listed for a human read) ----------
PITCH = ('medicare_affiliation_claim', 'money_back_claim', 'medicare_number_request', 'card_ready_check')
dnc = []
for c in calls:
    if not has(c, 'do_not_call_request'):
        continue
    h = hit(c, 'do_not_call_request')
    td, i0 = h['t'], h['i']
    later = {}
    toks = [tokens(x['x']) for x in c['sents']]
    for m in PITCH + ('no_more_calls_promise', 'transfer_to_agent'):
        r = M[m]
        for i in range(i0 + 1, len(c['sents'])):
            s = c['sents'][i]
            if r.in_window(s['t']) and r.speaker_ok(c['sp'][i]) and r.match_at(toks, i):
                later[m] = s['t']
                break
    dnc.append({'id': c['id'], 'i': i0, 't': td, 'dur': c['dur'], 'remaining_s': round(c['dur'] - td, 1),
                'later': later, 'sentences_after': len(c['sents']) - i0 - 1})
out['dnc'] = {'calls': len(dnc), 'detail': dnc}

# ---------- the transfer funnel ----------
def rate(group):
    return {'calls': len(group), 'transfer_pct': pct(sum(has(c, 'transfer_to_agent') for c in group), len(group)),
            'ci': wilson(sum(has(c, 'transfer_to_agent') for c in group), len(group))}


check = [c for c in calls if has(c, 'card_ready_check')]
out['funnel'] = {
    'overall': rate(calls),
    'card_check': rate(check),
    'card_check_then_not_handy': rate([c for c in check if has(c, 'card_not_handy', after=t(c, 'card_ready_check') - 1)]),
    'card_check_card_handy': rate([c for c in check if not has(c, 'card_not_handy', after=t(c, 'card_ready_check') - 1)]),
    'number_request': rate([c for c in calls if has(c, 'medicare_number_request')]),
    'median_transfer_s': med(t(c, 'transfer_to_agent') for c in calls),
}
# trust concerns around the number request
nr = [c for c in calls if has(c, 'medicare_number_request')]
trust_after = [c for c in nr if has(c, 'trust_concern') and 0 <= t(c, 'trust_concern') - t(c, 'medicare_number_request') <= 90]
trust_before = [c for c in nr if has(c, 'trust_concern') and t(c, 'trust_concern') < t(c, 'medicare_number_request')]
out['trust_vs_number'] = {
    'number_request_calls': len(nr),
    'trust_within_90s_after_pct': pct(len(trust_after), len(nr)),
    'trust_before_pct': pct(len(trust_before), len(nr)),
    'trust_any_pct_overall': pct(sum(has(c, 'trust_concern') for c in calls), N),
    'trust_with_number_vs_without': [pct(sum(has(c, 'trust_concern') for c in nr), len(nr)),
                                     pct(sum(has(c, 'trust_concern') for c in calls if not has(c, 'medicare_number_request')),
                                         N - len(nr))],
}
# conversion associations (descriptive only; longer calls give every moment more chances to fire)
groups = {}
for m in ('medicare_affiliation_claim', 'money_back_claim', 'trust_concern', 'already_covered', 'not_interested',
          'comprehension_friction', 'asks_call_purpose', 'call_fatigue', 'bad_time_callback', 'unsure_of_coverage',
          'card_not_handy', 'no_more_calls_promise', 'recording_notice'):
    w = [c for c in calls if has(c, m)]
    wo = [c for c in calls if not has(c, m)]
    groups[m] = {'with': rate(w), 'without': rate(wo), 'median_dur_with': med(c['dur'] for c in w),
                 'median_dur_without': med(c['dur'] for c in wo)}
out['transfer_by_moment'] = groups

# ---------- when things happen ----------
bins = [0, 30, 60, 120, 240, 480, 10 ** 6]
def hist(m):
    ts = [t(c, m) for c in calls if has(c, m)]
    return [sum(1 for x in ts if lo <= x < hi) for lo, hi in zip(bins, bins[1:])]
out['timing'] = {'bins_s': bins[:-1], 'rows': {m: hist(m) for m in M}}

# ---------- co-occurrence of customer-side moments ----------
cust = ['comprehension_friction', 'asks_call_purpose', 'trust_concern', 'already_covered', 'card_not_handy',
        'bad_time_callback', 'call_fatigue', 'not_interested', 'unsure_of_coverage']
out['customer_moments_any_pct'] = pct(sum(any(has(c, m) for m in cust) for c in calls), N)
out['hits_by_call'] = {c['id']: {m: [h['t'], h['i']] for m in M for h in [hit(c, m)] if h} for c in calls}
json.dump(out, open(out_path, 'w'))
show = {k: v for k, v in out.items() if k not in ('dnc', 'hits_by_call', 'timing')}
show['dnc_calls'] = out['dnc']['calls']
print(json.dumps(show, indent=1))
