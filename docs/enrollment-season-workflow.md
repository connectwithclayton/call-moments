# Disclaimer before benefits: an enrollment-season workflow

Medicare's annual open enrollment runs from October 15 to December 7. Since October 1, 2026, under CMS's CY2027 marketing rules, a third-party marketer has to read its disclaimer before discussing any benefits. From October 2022 until then, the rule was within the first minute of the call. In that era the disclaimer began "We do not offer every plan available in your area," and that's the wording these calls use.

This page shows how I'd build that check as a workflow in a no-code tool like Cresta Opera, and what happens when 3,750 past calls are replayed through it. The calls are undated. The dataset was published in mid-2025, and some calls may even predate the disclaimer rule. So the replay measures how far scripts of that era are from the new rule, and says nothing about how agents behave under it.

## What the replay shows

- **The first benefit comes early.** The agent names a specific benefit (dental, vision, transportation, a $0 premium, or money back) in 70% of calls. The trigger finds the first one a median of 49 seconds in, a quarter of them by 38 seconds. The real first benefit often comes a sentence earlier (see the rollout notes below).
- **The disclaimer comes late or never.** It's read in 42 of the 3,750 calls, a median of about 8 minutes in. Of the 2,607 calls that name a benefit, 2,583 never read it. In the other 24, the benefit came first, 3 to 20 minutes earlier.
- **A live prompt alone would be noise.** "Read the disclaimer now" would fire on 70% of calls, and always after the benefit had already been said.

So the first fix is the script, not the prompt. The disclaimer goes into the opener, before the first benefit, and the live workflow becomes a safety net that should rarely fire.

## The workflow

| Step | When it fires | What the agent or reviewer sees | Built from |
|---|---|---|---|
| 1. Checklist item | Call start | "Disclaimer: not yet read," which clears when the disclaimer is detected | Disclaimer rule (`tpmo_v4`) |
| 2. Urgent prompt | The first specific benefit, while the item is still open | "Read the disclaimer now" | Benefit trigger (`benefit_d1`) plus the disclaimer rule |
| 3. Review queue | After the call | Calls where benefits came before the disclaimer, with both timestamps | Same two rules |
| 4. Dashboard | Daily | Share of compliant calls by team, script and vendor | Same two rules |

## Rollout: test on past calls before anything goes live

1. **Shadow run.** Replay last week's calls and read 50 flagged and 50 unflagged ones to check both rules. Their grades today:
   - The disclaimer rule is *too rare to test* on the 100 held-out calls, though all 21 of its flags on tuning calls were right. Under CY2027 the disclaimer no longer mentions State Health Insurance Assistance Programs, so the rule's SHIP phrase only matters for older calls.
   - The benefit trigger is *exploratory*. An independent reviewer judged 24 of 25 random hits right (the 25th was a money-back line said during the handoff), and its recall hasn't been measured. It can also fire late: in 16 of those 25 calls, an earlier sentence had already offered $0 or covered copays. The next version adds copay wording ("co pays", "copayment"), and then gets checked again.
2. **Script change.** Move the disclaimer into the opener, then compare the compliance rate before and after.
3. **Go live.** Turn on the checklist item for everyone. Turn on the urgent prompt only after both rules clear the Ready bar (precision 90%+, recall 80%+) on 100 freshly labeled current calls. Target: a prompt on fewer than 1 call in 10.
4. **Weekly review.** Watch the prompt rate, the compliance rate, and how often agents dismiss the prompt.

## What each compliance rule would cost live

Each rule below is priced as if it raised a live alert: the share of the 3,750 calls it would fire on, at most once per call.

| Rule | Grade | Fires on | What to do with it |
|---|---|---|---|
| No recording notice before the handoff | Ready (the notice detector) | 98% of calls | Play the notice automatically when the call connects. 69% of calls have no notice at all, and most of the rest hear it from the licensed agent after the handoff. |
| Opener implies Medicare is calling | Ready | 90% | Fix the script and track it on a dashboard. A live alert would fire on almost every call. |
| Benefit before the disclaimer | Workflow above | 70% | Fix the script first, then use the live prompt as a safety net. |
| Money-back promise | Ready | 40% | After the call, check that a giveback plan exists in the customer's area. |
| "No one will call you again" | Exploratory | 5% | Review queue. |
| Stop-calling request | Too rare to test | 0.3% | Alert a supervisor, and have a person read every flag. |

My rule of thumb: a live alert has to be rare and right, firing on fewer than 1 call in 10. If a rule fires on most calls, the problem is the script. If a rule isn't Ready yet, its flags go to a person, not to an agent's screen.

## Files

- `rules/benefit_mention.json`: the benefit trigger, agent side only.
- `scripts/workflow_sim.py`: the replay. Its output is `results/workflow_sim.json`.
- `scripts/chart_alert_budget.py`: the chart in the README.
- Recordings that start after the handoff are set aside, as in `scripts/analysis_success.py`.
