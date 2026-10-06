# Findings

What building and measuring this system actually taught me. Most of these are negative
results: a mechanism that looked right and turned out not to work. They are here
because they changed the design, and because they are the part that transfers to other
knowledge systems.

Unless stated otherwise, the numbers come from one real deployment of this engine: a
product and business canon of about 1,300 notes (roughly 770 business/product notes,
270 technical notes and 300 cached transcripts). Retrieval numbers marked *personal
vault* come from a sibling system with the same contract: a personal knowledge base of
about 10,500 notes, which has a retrieval log large enough to evaluate against.

---

## 1. A mechanism built on a field nobody could fill

**Symptom.** `supersedes`, the field that says "this decision replaces that one", was
empty in 0 of 171 decision-logs. It looked like a capture-discipline problem: people
weren't filling it in.

**Cause.** It was *incomputable*, not empty. Notes only had `captured_on`, the day the
note was written. Forty decision-logs came out of the same bulk extraction and shared
the same date. 395 notes were dated up to six months after the event they described.
With no reliable ordering in time there is no "older" and no "newer" decision. So the
field, its derivation in `maintain`, the ×0.1 ranking penalty in `retrieve` and a health
check could never fire.

**Fix.** Two clocks. `occurred_on` is when the event happened (the call, the meeting, the
decision). `captured_on` is when someone wrote it down. `occurred_on` is recovered from
the source's own date (`source_date` in the extraction log) and is **never** filled by
copying `captured_on`. That copy is exactly the error the field exists to expose, so an
unknown date stays empty (constraint C29).

**What transfers.** Before building something new on a knowledge base, look for
mechanisms that already exist but have no fuel. That is cheaper than building, and more
honest than blaming discipline.

## 2. The contract drives the fill rate, not the people

`client_name` and `client_id` were used by three rules and by retrieval, but they were
never declared in the frontmatter block that the capture steps follow. They were filled
in 384 of 1,103 notes, and in 4 of 171 decision-logs. Nobody was being careless. The
contract simply didn't ask for them. Once they were declared, a deterministic backfill
(`cb.py clients`) was safe because it attributes **only from the title**, never from a
passing mention in the body (C30). A mention becomes a weak `menciona` edge in the graph
instead.

## 3. A ranking signal that touches everything reorders nothing

Retrieval used to multiply unvalidated notes by a penalty. At the time, 93% of business
notes were unvalidated (29 of 659 were validated). A multiplier applied to almost
everything doesn't reorder results. It only lifted the remaining 7%, and those were
mostly technical notes that arrived pre-validated from a migration. The real effect was
"tech above business", which nobody wanted.

Now ranking only penalises **known defects**: superseded (×0.1), contradicted by an
external check (×0.15), expired (×0.4), due for review (×0.7). `validated: false` is a
tie-breaker and a visible label. The one constant that is still set by eye (a ×1.3 boost
for high-severity gotchas) is marked as unmeasured in the skill itself.

## 4. The graph looked like +23 pp of recall. It was +4.

*Personal vault.* Graph expansion (following typed links from the top hits) appeared to
add about 23 percentage points of recall@50. Re-measured with **leave-one-session-out**,
it added about 4. The inflation came from evaluating a signal derived from the retrieval
log against that same log. On the graph channel alone, LOSO moved the measured hit rate
from 45.3% to 25.6%.

The two levers that did pass the gate needed no graph:

- **Query expansion**: +16.9 pp, 95% CI [+7.8, +26.5].
- **A single anchor note.**

**Consequence for this repo.** The derived entity graph is *not* used to expand search
results. It answers structured questions instead ("which customers on WhatsApp hit
problem X?"). That is a different use, and it doesn't inherit the negative result. Every
retrieval log entry now carries a mandatory `session_id`, so that any future signal
learned from the log can be evaluated with a session holdout (C33).

## 5. A self-graded outcome field is useless

The retrieval log had an `outcome` field, a judgment the model gave itself after
answering. In the personal vault 69 of 71 entries said `success`. It was retired. The
replacement is `notas_usadas`: which of the returned notes ended up in the final answer.
That is a human-labelled gold set produced at zero extra cost, and it is the only thing
the canon will ever be able to measure recall against. The log is one file per person
per month, because a single shared JSONL turns every concurrent push into a merge
conflict, and a log that causes conflicts stops being written (C34).

## 6. The first test suite could not fail

`cb.py` writes frontmatter into more than a thousand files. It reached 1,500 lines
without a single test. In one session it shipped two bugs that were only caught by
eyeballing the output: a date regex that ignored quoted dates, and a customer that
existed twice in the graph.

The suite now runs against a synthetic fixture, never against the real canon (which is
non-deterministic: another session added 195 notes while it was being written). It is
verified by **mutation**: reintroduce a real bug and check that the suite goes red. The
first time, **two of three mutations passed**, because the tests covered cases the
fixture didn't contain. A seventh mutation revealed dead code in `cb.py` itself (an alias
pruning step that could never trigger). The rule is now C38: no test counts until it has
been seen failing on the bug it claims to cover.

## 7. You can't derive an entity's class from text

The question was whether `customer` / `partner` / `reseller` / `competitor` could be
inferred from the notes. They can't, reliably. Searching for "competitor" tagged
customers *who talked about* competitors, and "agency" tagged 32 of 113 entities.
Classes are now assigned only on unambiguous evidence. Everything else is `customer` with
`class_via: "default — nobody decided"`. An honest default is worth more than a made-up
label, and human decisions live in a hand-edited overrides file that regeneration never
touches.

## 8. A check that can't go red is a statement, not a check

`health` used to report twelve checks with no thresholds. One of them literally said
"reports the number, does not judge it". Now every metric lives in `metrics.json` with
two thresholds and a written reason:

- `gate` is the collapse floor. It is red only if the canon gets worse than its baseline.
- `aviso` is the target. It is amber until reached.

The entry rule: if a number can't be red, it doesn't take a slot. The converse also
holds: a permanently red gate carries no information either. Thresholds never live in
the prompt (C31), because a number written in prose is a number nobody audits.

## 9. Pick the form that works, even if it's less elegant

"Bets" (a decision plus a falsifiable prediction, a deadline and what to do if it fails)
were designed as a full note type with frontmatter, lifecycle and validation. After a
month that type had zero notes. The equivalent in the personal vault is a JSONL with
eight fields, and it has twenty-odd closed bets. So the type was retired and bets became
one JSONL line. `si_falla` (what we'll do if this fails) is written **when the bet is
opened**, never when it is closed.

## 10. Most problems are seen once

Of 83 shareable product problems with structured occurrences, 77 had been seen with a
single customer and 5 with two. None had been seen with three. A cross-query that
returns one customer isn't failing: that is the evidence. So the tool always reports how
many customers have the problem in total, not only the ones that pass the filter.
Channel attribution is labelled `[declarado]` (written in a note's search terms) or
`[mención]` (the word appears in a body), and mentions are excluded by default.
