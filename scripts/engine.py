"""Opera-style moment rules for call transcripts.

A rule flags a *moment* in a call. Rules are plain data (rules.json) so an analyst can
read and edit them without touching code:

  any         phrases; a sentence matches if any phrase is found in it
  not_in      phrases that cancel a match when they appear in the same sentence
  negation    true -> cancel a match preceded (within 3 words) by not / never / no / don't
  window      [start_s, end_s] -> only sentences that start inside this part of the call count
  speaker     "customer" or "agent" -> skip sentences inferred to be the other side
              (speaker_infer.py; sentences of three words or fewer count as either side)
  utterance_threshold
              also fire when a sentence's similarity to the moment's example utterances
              (utterances.json, scored ahead of time) is at least this value

Phrase syntax (applied to lowercased word tokens):
  plain words must appear in order      "not interested"
  ( a | b c )   alternatives            "(do not | don't) call me"
  ( a )?        optional words           "(the)? medicare"
  *             exactly one word        "call * back"
  ~             zero to three words     "medicare ~ updated"
  ^ at the start  only at the start of the sentence   "^ (yes | yeah) "
  prev          phrases one of the previous two sentences must contain (a question
                and its answer, for example)
  also          extra clauses, each with its own any / not_in / prev; the rule fires
                when the main clause or any extra clause matches
"""
import json
import re

TOKEN = re.compile(r"\[[a-z_]+\]|[a-z0-9]+(?:'[a-z]+)?")
NEGATORS = {"not", "never", "no", "don't", "dont", "won't", "can't", "cannot", "isn't", "wasn't", "didn't"}


def tokens(text):
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = re.sub(r"\bco[- ]payments?\b", "copayment", text)
    return TOKEN.findall(text)


def phrase_regex(phrase):
    """Compile one phrase to a regex over a space-joined token string."""
    out, p = [], phrase.lower().replace("’", "'").strip()
    anchored = p.startswith("^")
    if anchored:
        p = p[1:]
    parts = re.findall(r"\)\?|\(|\)|\||\*|~|[^\s()|*~?]+", p)
    for part in parts:
        if part == "(":
            out.append("(?:")
        elif part == ")?":
            out.append(")?")
        elif part == ")":
            out.append(")")
        elif part == "|":
            out.append("|")
        elif part == "*":
            out.append(r"\S+ ")
        elif part == "~":
            out.append(r"(?:\S+ ){0,3}")
        else:
            out.append(re.escape(part) + " ")
    return re.compile((r"^ " if anchored else r"(?:^| )") + "".join(out))


class Rule:
    def __init__(self, spec):
        self.spec = spec
        self.id = spec["id"]
        self.moment = spec["moment"]
        self.version = spec.get("version", "v1")
        self.any = [phrase_regex(p) for p in spec.get("any", [])]
        self.not_in = [phrase_regex(p) for p in spec.get("not_in", [])]
        self.negation = spec.get("negation", False)
        self.prev = [phrase_regex(p) for p in spec.get("prev", [])]
        self.prev_n = spec.get("prev_window", 2)
        self.window = spec.get("window")
        self.speaker = spec.get("speaker")
        self.uthr = spec.get("utterance_threshold")
        self.also = [Rule({**sub, "id": f"{self.id}+{k}", "moment": self.moment})
                     for k, sub in enumerate(spec.get("also", []))]

    def match_at(self, toks, i):
        """Match sentence i (toks is the whole call's token lists), including extra clauses."""
        if self.any and self.prev_ok(toks, i):
            hit = self.match_sentence(toks[i])
            if hit is not None:
                return hit
        for a in self.also:
            hit = a.match_at(toks, i)
            if hit is not None:
                return hit
        return None

    def match_sentence(self, toks):
        s = " " + " ".join(toks) + " "
        if any(n.search(s) for n in self.not_in):
            return None
        for rx in self.any:
            m = rx.search(s)
            if not m:
                continue
            if self.negation and NEGATORS & set(s[: m.start() + 1].split()[-3:]):
                continue
            return m.group(0).strip()
        return None

    def prev_ok(self, toks, i):
        if not self.prev:
            return True
        for j in range(max(0, i - self.prev_n), i):
            s = " " + " ".join(toks[j]) + " "
            if any(rx.search(s) for rx in self.prev):
                return True
        return False

    def in_window(self, t):
        return self.window is None or (self.window[0] <= t <= self.window[1])

    def speaker_ok(self, tag):
        if not self.speaker or not tag or tag == "u":
            return True
        return (tag == "a") == (self.speaker == "agent")


def load_rules(path):
    return [Rule(r) for r in json.load(open(path))]


def run_call(rules, call):
    """Return {rule_id: {"t": first_time, "i": sentence_index, "hit": matched_text, "n": hit_count}}.
    Optional call fields: "sp" (one speaker tag per sentence: a, c or u) and
    "u" ({moment: {sentence_index: similarity}}) for utterance matching."""
    toks = [tokens(s["x"]) for s in call["sents"]]
    tags = call.get("sp") or ""
    sims = call.get("u") or {}
    out = {}
    for r in rules:
        first, n = None, 0
        msims = sims.get(r.moment, {}) if r.uthr is not None else {}
        for i, s in enumerate(call["sents"]):
            if not r.in_window(s["t"]):
                continue
            if not r.speaker_ok(tags[i] if i < len(tags) else None):
                continue
            hit = r.match_at(toks, i)
            if hit is None and msims:
                sc = msims.get(i, msims.get(str(i)))
                if sc is not None and sc >= r.uthr:
                    hit = "\u2248 %.2f" % sc
            if hit is not None:
                n += 1
                if first is None:
                    first = {"t": s["t"], "i": i, "hit": hit}
        if first:
            first["n"] = n
            out[r.id] = first
    return out
