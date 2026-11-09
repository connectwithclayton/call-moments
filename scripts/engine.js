// Browser twin of engine.py: same tokens, same phrase syntax, same rule semantics.
(function (root) {
  const TOKEN = /\[[a-z_]+\]|[a-z0-9]+(?:'[a-z]+)?/g;
  const NEGATORS = new Set(["not", "never", "no", "don't", "dont", "won't", "can't", "cannot", "isn't", "wasn't", "didn't"]);
  function tokens(text) {
    let t = text.toLowerCase().replace(/’|‘/g, "'");
    t = t.replace(/\bco[- ]payments?\b/g, "copayment");
    return t.match(TOKEN) || [];
  }
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  function phraseRegex(phrase) {
    let p = phrase.toLowerCase().replace(/’/g, "'").trim();
    const anchored = p.startsWith("^");
    if (anchored) p = p.slice(1);
    const parts = p.match(/\)\?|\(|\)|\||\*|~|[^\s()|*~?]+/g) || [];
    let out = "";
    for (const part of parts) {
      if (part === "(") out += "(?:";
      else if (part === ")?") out += ")?";
      else if (part === ")") out += ")";
      else if (part === "|") out += "|";
      else if (part === "*") out += "\\S+ ";
      else if (part === "~") out += "(?:\\S+ ){0,3}";
      else out += esc(part) + " ";
    }
    return new RegExp((anchored ? "^ " : "(?:^| )") + out);
  }
  function compile(spec) {
    return {
      spec, id: spec.id, moment: spec.moment, version: spec.version || "v1",
      any: (spec.any || []).map(phraseRegex), notIn: (spec.not_in || []).map(phraseRegex),
      negation: !!spec.negation, window: spec.window || null,
      speaker: spec.speaker || null, uthr: spec.utterance_threshold == null ? null : spec.utterance_threshold,
      prev: (spec.prev || []).map(phraseRegex), prevN: spec.prev_window || 2,
      also: (spec.also || []).map((sub, k) => compile({ ...sub, id: spec.id + "+" + k, moment: spec.moment })),
    };
  }
  function matchSentence(rule, toks) {
    const s = " " + toks.join(" ") + " ";
    for (const n of rule.notIn) if (n.test(s)) return null;
    for (const rx of rule.any) {
      const m = rx.exec(s);
      if (!m) continue;
      if (rule.negation) {
        const before = s.slice(0, m.index + 1).split(/\s+/).filter(Boolean).slice(-3);
        if (before.some((w) => NEGATORS.has(w))) continue;
      }
      return { text: m[0].trim(), start: m.index };
    }
    return null;
  }
  function prevOk(rule, toks, i) {
    if (!rule.prev.length) return true;
    for (let j = Math.max(0, i - rule.prevN); j < i; j++) {
      const s = " " + toks[j].join(" ") + " ";
      if (rule.prev.some((rx) => rx.test(s))) return true;
    }
    return false;
  }
  function matchAt(rule, toks, i) {
    if (rule.any.length && prevOk(rule, toks, i)) { const h = matchSentence(rule, toks[i]); if (h) return h; }
    for (const a of rule.also) { const h = matchAt(a, toks, i); if (h) return h; }
    return null;
  }
  function inWindow(rule, t) { return !rule.window || (rule.window[0] <= t && t <= rule.window[1]); }
  function speakerOk(rule, tag) {
    if (!rule.speaker || !tag || tag === "u") return true;
    return (tag === "a") === (rule.speaker === "agent");
  }
  // call.sents: [{t, x, _tok?}]; optional call.sp (speaker tag per sentence) and call.u ({moment: {i: sim}})
  function runCall(rules, call) {
    const out = {};
    for (const s of call.sents) if (!s._tok) s._tok = tokens(s.x);
    const toks = call.sents.map((x) => x._tok);
    const tags = call.sp || "";
    for (const r of rules) {
      let first = null, n = 0;
      const msims = r.uthr != null && call.u ? call.u[r.moment] || null : null;
      call.sents.forEach((s, i) => {
        if (!inWindow(r, s.t)) return;
        if (!speakerOk(r, tags[i])) return;
        let h = matchAt(r, toks, i);
        if (!h && msims) {
          const sc = msims[i];
          if (sc != null && sc >= r.uthr) h = { text: "\u2248 " + sc.toFixed(2) };
        }
        if (h) { n++; if (!first) first = { t: s.t, i, hit: h.text }; }
      });
      if (first) { first.n = n; out[r.id] = first; }
    }
    return out;
  }
  const api = { tokens, phraseRegex, compile, matchSentence, matchAt, prevOk, inWindow, speakerOk, runCall };
  if (typeof module !== "undefined") module.exports = api; else root.MomentEngine = api;
})(this);
