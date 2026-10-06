# Open Company Brain

**A company's shared memory that knows when it's wrong.** It is a Claude skill plus a
zero-dependency Python instrument. Together they turn a git repo of Markdown notes into
a living canon of what a team decided, how things really work, what each metric means,
and what keeps breaking for which customers. Every note has an owner, an expiry date and
a reliability label, and the canon is measured against gates that can go red.

![tests](https://github.com/csmoya/open-company-brain/actions/workflows/ci.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.9%2B%20·%20stdlib%20only-blue)
![license](https://img.shields.io/badge/license-MIT-green)

---

## Why

Company knowledge rots in a predictable way. A decision gets made on a call, a doc says
one thing while the product does another, a metric means three things to three people,
and the same bug is reported by four customers who never get linked. Wikis don't fix
this, because nothing in a wiki ever expires and nothing tells you how much to trust a
page.

This system starts from the opposite assumption: **every note is provisionally wrong
until someone checks it, and the system must say which ones nobody has checked.**

It runs in production on a real B2B SaaS canon of about 1,300 notes (business, product
and technical), built from real calls, Slack threads and code. This repo is the engine
without the content.

## What it does

You talk to Claude in natural language, for example *"register this decision"*,
*"process this meeting transcript"*, *"what do we know about X?"* or *"what should I
validate this week?"*, and the skill infers one of eight actions:

| Action | In one line |
|---|---|
| `capture` | Document something, but only after checking that it doesn't already exist (*recover before create*) |
| `extract` | Turn a transcript into 3–8 notes, never process the same source twice, and add occurrences instead of duplicating |
| `retrieve` | Answer from the canon, ranked down by **known defects** (superseded, contradicted, expired), with every result's status visible |
| `maintain` | Mark what is stale or superseded and build a prioritised validation queue. It never validates anything itself |
| `validate` | A weekly ritual of at most 5 notes, where a human confirms, edits or retires each one |
| `manifest` | A cheap index so an agent knows which note to open without reading everything |
| `health` | Artifact hygiene plus the measurement gates |
| `enrich` | Normalise vocabulary against an ontology and propose typed links between notes |

The design is in [`docs/architecture.md`](docs/architecture.md). The skill itself is
[`skill/SKILL.md`](skill/SKILL.md), and the per-type note contract is in
[`skill/references/contrato-de-notas.md`](skill/references/contrato-de-notas.md). Both
are written in Spanish, the language the system was built and is operated in.

## What I learned building it

The most useful part of this repo is probably [`docs/findings.md`](docs/findings.md):
ten results, mostly negative, that changed the design. Three of them:

- **A mechanism built on a field nobody could fill.** "This decision supersedes that
  one" was set in 0 of 171 decision-logs. That wasn't laziness. Notes only recorded the
  day they were *written*, so 40 decisions shared one date and there was no "older"
  decision to supersede. The fix was two clocks (`occurred_on` / `captured_on`), and the
  mechanism started working.
- **The graph looked like +23 pp of recall. It was +4.** Measured honestly
  (leave-one-session-out instead of evaluating the log against itself), graph expansion
  barely helped, and query expansion did (+16.9 pp, 95% CI [+7.8, +26.5]). So the graph
  answers structured questions here and is not used to pad search results.
- **The first test suite couldn't fail.** When real bugs were reintroduced on purpose,
  two of three went undetected. Now no test counts until it has been seen going red.

## Try it in one minute

Python 3.9+ and nothing else.

```bash
git clone https://github.com/csmoya/open-company-brain && cd open-company-brain
export CB_BASE=example CB_TODAY=2026-10-06     # the fictional canon, with the clock pinned

python3 tools/cb.py stats       # the canon in numbers
python3 tools/cb.py gates       # what is red today, against which threshold, and why
python3 tools/cb.py cruce --canal WhatsApp --problema whatsapp-template
python3 tools/cb.py vecinos --nodo "Acme Build"
python3 tools/test_cb.py        # 23 tests against a synthetic fixture
```

The example is **Kestrel**, a made-up messaging SaaS with made-up customers (see
[`example/README.md`](example/README.md)). Real output:

```text
gates del canon · Kestrel · 2026-10-06

  [ROJO ] validacion.ciclo_de_vida              41.7 %  (gate 50 %)
  [AMBAR] caducidad.expiradas                        2  (gate 3)
  [AMBAR] temporal.recuperadas                  83.3 %  (gate 80 %)
  [ROJO ] contrato.sin_contrato                      1  (gate 0)
  [AMBAR] apuestas.vencidas_sin_cerrar               1  (gate 3)
  [verde] grafo.con_provenance                 100.0 %  (gate 100 %)
  [verde] log.con_notas_usadas                  83.3 %  (gate 50 %)
  [verde] log.con_session_id                   100.0 %  (gate 100 %)
```

```text
problemas compartibles · canal WhatsApp · problema ~whatsapp-template

  whatsapp-template-rejected-silently  (high)
      3 cliente(s) en total · 4 ocurrencia(s) · 2026-04-03 → 2026-08-27
      con el canal: Acme Build [declarado] Northwind Retail [declarado] Umbrella Health [declarado]
```

## Use it on your own company

1. Copy `skill/` into your Claude skills directory (or install it as a project skill).
2. Create a private repo for your canon with a `<project>/Context/` folder. Copy
   `example/Context/_skill-config/metrics.json` as a starting contract and set your own
   baselines.
3. Point the engine at it: `CB_BASE=path/to/<project> python3 tools/cb.py stats`.
4. Keep the engine as a submodule so improvements flow in one direction only. See
   [`docs/syncing.md`](docs/syncing.md), which also covers the pre-commit leak check.

## Principles

- **Markdown is the source of truth.** Indexes, graphs and queues are derived and
  regenerable, and they are sealed with a hash so a stale one says so.
- **The model proposes, a human decides.** Nothing is created, validated, linked or
  archived without explicit approval.
- **If a number can't go red, it doesn't take a slot.** Thresholds live in
  `metrics.json` with a written reason, never in the prompt.
- **Reported is not measured.** A figure a customer said on a call is
  `client-reported` and is never presented as a benchmark.
- **Deterministic, dependency-free, dry-run by default.** The instrument writes into
  thousands of files, so it has to be boring.

## Status

v0.7.1. It is used weekly and developed in the open alongside a private deployment. See
[`CHANGELOG.md`](CHANGELOG.md) for history, and
[`skill/references/estado-y-pendientes.md`](skill/references/estado-y-pendientes.md) for
what is blocked, what waits on human judgment and what is out of scope on purpose.
Known engine issues are listed in [`docs/known-issues.md`](docs/known-issues.md).

## Author

Built by **Carlos Moya** ([@csmoya](https://github.com/csmoya)). It grew out of a personal knowledge system (a ~10,500-note
second brain) and the question of what that would look like for a whole company.

MIT licensed.
