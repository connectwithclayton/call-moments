# Call Moments

Rules that flag the moments that matter in sales calls, measured against labeled calls instead of assumed to work.

The calls are 4,005 PII-redacted outbound Medicare sales calls (433 hours) from a public research dataset. The project defines 18 moments, writes rules for each, has AI reviewers label 301 calls against written guidelines, freezes every rule version, and scores them once on 100 held-out calls the rules never saw. Then it runs the rules across every call to turn hits into findings a contact-center team could act on.

## Read this first

**How old the data is.** The calls come from a public research dataset published in mid-2025. Dates inside the calls are redacted, so the exact months are unknown. CMS's CY2027 marketing rules took effect on Oct 1, 2026: the disclaimer must now come before benefits are discussed, and recordings are kept 6 years instead of 10. So every rate below is a baseline from that period, not a reading of today's market. The rules, their measured accuracy and the method are what carry over to current calls.

**How usable each rule is.** Each rule is graded on the 100 held-out calls:

- **Ready:** precision of 90% or more and recall of 80% or more. Fine for live alerts and for reporting rates.
- **QA only:** recall of 80% or more and precision of 50% or more. It catches most cases, but a person checks each flag.
- **Not yet:** below both bars.
- **Too rare to test:** fewer than 10 held-out cases. A person reads every flag.
- **Exploratory:** discovered moments, whose precision was spot-checked but whose recall is unknown.

| Moment | Status | Use it for | Evidence |
|---|---|---|---|
| Medicare affiliation claim | Ready | Live alerts and rate reporting | held-out: 85 of 85 flags right, 85 of 89 cases caught |
| Money-back claim | Ready | Live alerts and rate reporting | held-out: 35 of 35 flags right, 35 of 35 cases caught |
| Recording notice | Ready | Live alerts and rate reporting | held-out: 23 of 23 flags right, 23 of 24 cases caught |
| Transfer to licensed agent | Ready | Rate reporting: it is the conversion outcome | held-out: 84 of 86 flags right, 84 of 90 cases caught |
| Already covered | QA only | A QA queue where a person checks each flag | held-out: 22 of 41 flags right, 22 of 25 cases caught (recall mode) |
| Bad time, call back | Not yet | Not for use yet | 16 of 25 random hits judged right; recall not measured |
| Medicare number request | Not yet | Not for use yet | held-out: 10 of 21 flags right, 10 of 12 cases caught |
| Trust concern | Not yet | Not for use yet | held-out: 3 of 3 flags right, 3 of 11 cases caught |
| Do-not-call request | Too rare to test | Only with a person reading every flag | no held-out cases; every flagged call read by an independent reviewer: 13 of 16 were real |
| Not interested | Too rare to test | Only with a person reading every flag | only 1 held-out case |
| TPMO disclaimer | Too rare to test | Only with a person reading every flag | no held-out cases; tuning set: 21 of 21 flags right; labels on 250 random calls find it in 1.2%, rules in 1.1% |
| "No one will call you again" | Exploratory | Reading calls and sampling; not for rates | 25 of 25 random hits judged right; recall not measured |
| Asks what the call is about | Exploratory | Reading calls and sampling; not for rates | 24 of 25 random hits judged right; recall not measured |
| Can't hear or understand | Exploratory | Reading calls and sampling; not for rates | 22 of 25 random hits judged right; recall not measured |
| Card not handy | Exploratory | Reading calls and sampling; not for rates | 23 of 25 random hits judged right; recall not measured |
| Card-ready check | Exploratory | Reading calls and sampling; not for rates | 24 of 25 random hits judged right; recall not measured |
| Too many calls | Exploratory | Reading calls and sampling; not for rates | 21 of 25 random hits judged right; recall not measured |
| Unsure of own coverage | Exploratory | Reading calls and sampling; not for rates | 21 of 25 random hits judged right; recall not measured |

Re-test on 100 freshly labeled current calls before relying on any grade.

## Results on the held-out test

100 random calls, never used while writing rules, scored once after every version was frozen (hashes in `rules/FROZEN.txt`). Precision counts every flag; recall counts random calls only.

| Moment | v1 F1 | v2 F1 | v4 F1 | v4 precision | v4 recall | Positives |
|---|---|---|---|---|---|---|
| Medicare affiliation claim | – | 0.91 | 0.98 | 100% | 96% | 89 |
| Money-back claim | 0.62 | 0.97 | 1.00 | 100% | 100% | 35 |
| Recording notice | 0.96 | 0.98 | 0.98 | 100% | 96% | 24 |
| Transfer to licensed agent | 0.33 | 0.78 | 0.95 | 98% | 93% | 90 |
| Medicare number request | 0.53 | 0.46 | 0.61 | 48% | 83% | 12 |
| Already covered | 0.07 | 0.21 | 0.56 | 79% | 44% | 25 |
| Trust concern | – | – | 0.43 | 100% | 27% | 11 |

v1 is a one-phrase first draft, v2 was frozen before any label was seen, and v3 and v4 were tuned on a separate 201-call tuning set. The disclaimer, do-not-call and not-interested moments are too rare for 100 random calls; their checks are in `results/`.

Scripted agent moments are easy for rules; the Medicare-number ask, also agent-side, reaches only 0.61 because it's easily confused with the card check. Customer moments are hard: the transcripts don't say who is talking, and customers phrase things a hundred ways. Gains on the tuning set shrank on fresh calls. Utterance matching in recall mode caught 88% of already-covered calls, up from 44%, at 54% precision. That's useful for QA sampling but too noisy for live hints.

## What the rules found across all 4,005 calls

Rates from calls made before mid-2025, each tagged with the grade of the rule behind it.

- **84%** of calls open by implying Medicare itself is calling ("your Medicare is getting upgraded"), about 12 seconds in. Labels on 250 random calls put it at 85.6%. A third of all calls pair it with a money-back promise (a giveback, a Part B reduction, or money added to the Social Security check). *Ready.*
- The third-party marketer disclaimer appears in **44 calls (1.1%)**, and never in the first minute, which was the CMS rule when these calls were made. Since Oct 1, 2026 (CY2027), it must come before any benefits are discussed, and in 32 of the 44 calls the benefits pitch comes first. *Too rare to test; labels on 250 random calls agree (1.2%).*
- An independent read of all 16 flagged do-not-call calls found **13 genuine requests**. In 11 the pitch continued, and in 6 the agent promised the calls would stop. That promise appears in 198 calls, two times in three just after the transfer cue, so it's part of the handoff script. *Too rare to test, so a reviewer read every flag; the promise rule is exploratory.*
- **What wins can't be read from these calls yet.** The only outcome recorded is the handoff to a licensed agent. Recordings stop a median of 2.5 minutes after it, and none captures a finished enrollment. 255 recordings open after the handoff ("thank you for holding"), so a transfer rarely shows in them. Of the other 3,750, 97% are handed off once you count the connection lines the transfer rule missed. About one recording in ten overlaps another recording of the same call. Counted only before the handoff, and with every call given the same time, no moment moves the handoff rate enough to act on (`results/transfer_from_start.json`). *Not yet: there's no outcome past the handoff.*
- **Withdrawn:** three earlier reads of what wins. Calls with a Medicare-number ask seemed to transfer less (84.8% against 92.2%), the stop-calling promise seemed to lift transfers, and so did the Medicare opener. The gaps came from recordings that open after the handoff (half of all recordings with no transfer cue), handoffs the transfer rule missed, and moments said after the transfer (two-thirds of number asks and promises). Asks made before the handoff go with the same handoff rate as no ask: 96.9% against 97.4%.
- **47%** of calls include at least one friction moment the rules catch, and 33% have one from the customer's side alone. Already covered leads (23.6% in labels), and comprehension trouble, where someone can't hear or understand, follows (22.5%). *Exploratory: the 47% and 22.5% are rule hits; the 23.6% comes from labels.*

## How it works

**Rule engine** (`scripts/engine.py`, browser twin `scripts/engine.js`). Rules are plain JSON that an analyst can read and edit. A rule fires on a sentence that contains any of its phrases, unless the sentence also has an exclusion. It can also be limited to a time window, to one inferred speaker, or to the answer that follows a question. Phrase syntax works on lowercased word tokens:

| Syntax | Meaning |
|---|---|
| `( a \| b )` | either |
| `( a )?` | optional |
| `*` | exactly one word |
| `~` | zero to three words |
| `^` | start of the sentence |

The two engines agree on every hit (`scripts/parity_check.py`; `results/engine_parity.json`: 0 mismatches across 8,500 hits).

**Who's talking** (`scripts/speaker_infer.py`). Agents read scripts, so their wording recurs across thousands of calls, while customers improvise. A sentence counts as agent-like when 40% or more of its 4-word sequences appear in 20 or more calls. That rule was 95% right on held-out labeled quotes (28 of 30 customer lines). The tags keep agent script out of utterance matching.

**Utterance matching** (`scripts/embed.py`). Customer-like sentences are embedded with `BAAI/bge-small-en-v1.5` (via fastembed, on CPU) and compared with 10 to 14 example utterances per moment (`rules/utterances.json`).

**Labels** (`labels/`). AI reviewers labeled each call against `labels/GUIDELINES.md`, with a quote and timestamp for every yes. The published labels keep only yes/no and the timestamp: no transcript text.

**Discovered moments** (`rules/rules_discovered.json`). Eight themes were found by reading 100 development calls. They have no labels yet, so an independent reviewer judged 25 random hits per rule (`results/spot_checks.json`). The two weakest rules were revised and re-checked on fresh hits: "what is this about" went from 9/25 to 24/25, and "bad time, call back" stayed at 16/25, because its errors are about who is speaking.

## Reproduce

```bash
pip install -r requirements.txt
python scripts/download.py data
python scripts/prep.py data/insurance_outbound work/corpus.jsonl work/idmap_private.json
python -c "import json,sys; sys.path.insert(0,'scripts'); from speaker_infer import tag_corpus; json.dump(tag_corpus('work/corpus.jsonl'), open('work/speaker_tags.json','w'))"
python scripts/embed.py work/corpus.jsonl work/speaker_tags.json rules/utterances.json labels/tuning/sample.json labels/heldout/sample.json labels/bench_ids.json --out work/utter_sims.json
python scripts/evaluate.py work/corpus.jsonl rules/rules_v4.json labels/heldout/sample.json labels/heldout work/eval_heldout.json --sp work/speaker_tags.json --u work/utter_sims.json
python scripts/analysis_final.py work/corpus.jsonl rules/rules_v4.json rules/rules_discovered.json work/speaker_tags.json work/analysis.json
python scripts/analysis_success.py work/corpus.jsonl work/analysis.json labels/tuning labels/heldout work/transfer_from_start.json
```

`prep.py` numbers calls `C0001` to `C4005` in sorted file order, so the IDs regenerate from the dataset without publishing its file names (which look like phone numbers). Keep `work/` private: it holds transcript text. Embedding runs at about 10 to 60 sentences a second on two CPU cores.

## Data and license

The transcripts come from [AIxBlock, 92k real-world call center scripts](https://huggingface.co/datasets/AIxBlock/92k-real-world-call-center-scripts-english) (insurance outbound set). The publisher PII-redacted them, and they are licensed CC BY-NC 4.0 for research use. No transcript text is in this repository. The code is MIT-licensed (see `LICENSE`).

## Independent check

A separate checker recomputed every published number from the raw files with its own code (109 claims). It caught a few slips: a rounding error, one mis-stated definition, a claim about the disclaimer rule that changed on Oct 1, 2026, and some overstated wording. All are fixed here.

Two later reviews, prompted by the question of what wins, found what that check missed: recordings that open after the handoff, handoffs the transfer rule missed, moments said after the transfer, and overlapping recordings of the same call. Together they withdrew the Medicare-number lead and two other reads of what wins (`results/transfer_from_start.json`).

## Limits

- Labels are AI-drafted: careful but not perfect. On the card check versus the Medicare-number ask, similar calls got different answers.
- The handoff is the only outcome, and 97% of calls recorded from the start get one, so the few misses can't show what loses. The transfer rule misses some handoffs: in the labeled sample, 7 of the 20 recordings it marks as not transferred were labeled transferred. Transfer comparisons set aside the 255 recordings that open after the handoff and count moments only before it (`scripts/analysis_success.py`). Every comparison is an association.
- Calls have no dates. The dataset was published in mid-2025, so disclosures are checked against the first-minute rule in force then and the before-benefits rule since Oct 1, 2026. There are no trends over time.
- Customer moments are rare. The held-out test has 25 already-covered and 11 trust positives, but only 1 not-interested and no do-not-call, so their intervals are wide.
- About one recording in ten overlaps another recording of the same call: 183 to 240 pairs of adjacent recordings, depending on the matching rule, often the first agent's side and the licensed agent's side. None crosses between the tuning and held-out sets. Corpus-wide rates count recordings, not calls.

Clayton Johnson · [linkedin.com/in/connectwithclayton](https://www.linkedin.com/in/connectwithclayton)
