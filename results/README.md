# What each results file holds

| File | What it is |
|---|---|
| `eval_heldout.json` | The final test: every rule version scored once on 100 held-out random calls |
| `eval_tuning.json` | The same scores on the 201 tuning calls the rules were improved on (expect these to look better) |
| `readiness.json` | The grade for each moment (Ready, QA only, Not yet, Too rare to test, Exploratory) and the bars behind it |
| `corpus_findings.json` | Rates from running the final rules on all 4,005 recordings |
| `transfer_from_start.json` | The corrected look at handoffs: recordings that start late set aside, moments counted only before the handoff |
| `workflow_sim.json` | The disclaimer-before-benefits replay and the alert budget |
| `label_prevalence_250_random.json` | How often each moment appears in the labels on 250 random calls |
| `spot_checks.json` | An independent reviewer's verdicts on 25 random hits per discovered rule |
| `dnc_review_counts.json` | The read of all 16 flagged stop-calling calls |
| `speaker_inference_heldout.json` | How well the who's-talking tags did on held-out quotes |
| `engine_parity.json` | Proof the Python and browser engines give the same hits |

## Withdrawn numbers still in these files

`corpus_findings.json` keeps the first, confounded comparisons of handoff rates so the correction can be checked. Don't cite these:

- `funnel` (for example, calls with a Medicare-number ask at 84.8%)
- `transfer_by_moment` (for example, calls with and without the Medicare opener)

They count recordings that start after the handoff as lost calls, miss some handoffs, and include moments said after the transfer. `transfer_from_start.json` replaces them: counted properly, no moment moves the handoff rate enough to act on.
