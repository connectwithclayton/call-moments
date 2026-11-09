# Labeling guidelines: outbound Medicare sales calls

You are labeling real, PII-redacted call-center transcripts (outbound calls selling Medicare plans or benefits). Each call starts with `### CALL C#### (duration Ns)`, followed by one sentence per line with its start time as `[mm:ss]`.

The transcripts come from speech recognition. There are **no speaker labels**, so work out from context who is talking (the agent pitches and asks questions; the customer answers). Redacted details appear as tags like `[PERSON_NAME]` or `[MONEY_AMOUNT]`. Transcription errors happen; judge what was meant.

Judge **meaning**, not keywords. Mark a moment present only when the transcript clearly supports it. When unsure, mark it absent and say why in `notes`.

## The ten moments

1. `tpmo_disclaimer`: the agent gives the third-party marketer disclaimer. In substance: "we do not offer every plan available in your area". It may add how many organizations or plans they represent, or point to Medicare.gov, 1-800-MEDICARE or a State Health Insurance Program. A vague "we work with many companies" does **not** count.
2. `recording_notice`: the agent (or a recorded message) says the call is recorded or monitored.
3. `medicare_affiliation_claim`: the agent says or clearly implies they are calling **from or on behalf of Medicare or the government**, or that **Medicare itself** is updating, upgrading or renewing the customer's benefits. Example: "your Medicare is getting updated today". Mentioning Medicare plans, "Medicare-approved plans", or saying "I'm not from Medicare" does **not** count.
4. `money_back_claim`: the agent promises money added to the customer's **Social Security check**, or a "giveback" or premium reduction paid back to them. Other plan benefits (dental, vision, allowance or grocery cards) do **not** count.
5. `do_not_call_request`: the customer asks not to be called again, to be taken off the list, or to stop calling. "I'm busy, call me later" does **not** count.
6. `not_interested`: the customer explicitly declines the offer, e.g. "I'm not interested" or "no, I don't want it". Hesitation, questions or "let me think" do **not** count.
7. `already_covered`: the customer says they already have coverage or a plan they want to keep, e.g. a supplement, "I'm happy with my plan", or coverage through Medicaid, the VA, a union or an employer.
8. `trust_concern`: the customer questions the call's legitimacy or their privacy. They suspect a scam, ask how the caller got their number or who is really calling, or refuse to give information over the phone.
9. `transfer_to_agent`: the agent transfers the call, or clearly sets up a live transfer, to a licensed agent, specialist, supervisor or enrollment team, with the customer going along with it. Only saying someone will contact them later does **not** count.
10. `medicare_number_request`: the agent asks the customer for their Medicare card number, Medicare ID or MBI.

## Also record

- `outcome`, one of:
  - `transferred`: a transfer happened or started.
  - `declined_or_ended`: the customer refused or the call ended without progress.
  - `callback_or_followup`: a callback or later contact was agreed.
  - `unclear`
- `call_type`: a few words describing the call, e.g. "Medicare benefits update pitch", "plan review", "final expense", "wrong person / voicemail".

## Output

Write one JSON file: a list with one object per call, in the order they appear. Each object:

```json
{
  "call_id": "C0123",
  "labels": {
    "tpmo_disclaimer": {"present": false},
    "recording_notice": {"present": true, "t": 12, "quote": "this call is being recorded for quality and training"},
    "...": {}
  },
  "outcome": "transferred",
  "call_type": "Medicare benefits update pitch",
  "notes": "optional, short"
}
```

- Include all ten moment keys for every call.
- `t` is integer seconds of the **first** sentence where the moment occurs, taken from its `[mm:ss]` tag (for example, [01:05] is 65).
- `quote` is exact text from that sentence, at most 15 words.
- Return valid JSON only in the file: no comments and no trailing commas.
