# Architecture

## The shape in one picture

```
            sources                     canon (Markdown + YAML, in git)                   derived (regenerable)
  ┌──────────────────────┐      ┌──────────────────────────────────────────┐     ┌──────────────────────────┐
  │ meeting transcripts  │      │ decision-logs   DL-   observations  OB-  │     │ entities.json            │
  │ Slack / email / docs │ ───► │ processes       PR-   context-maps  CM-  │ ──► │ entity-graph.jsonl       │
  │ a person explaining  │      │ metrics         MET-  glossary      GL-  │     │ manifest.json / .md      │
  └──────────────────────┘      │ tech: Sys- Run- Got- Ref- Plan- Inv-     │     │ validation-queue.json    │
        extract / capture       │ Sources/ (cached raw transcripts)        │     │ _reports/*               │
                                └──────────────────────────────────────────┘     └──────────────────────────┘
                                      ▲                 │                                    │
                                      │ validate        │ maintain / gates                   │ retrieve
                                   (a human,           ▼                                    ▼
                                    5 notes/week)   metrics.json ── runs.jsonl          answers, calibrated
                                                    bets.jsonl                          by known defects
```

**Markdown is the source of truth. Everything else can be rebuilt from it.** The one
exception is human judgment (typed note-to-note links, entity class overrides, bets).
That lives in files that are edited by hand and never regenerated.

## Two layers, two programs

| | `skill/SKILL.md` | `tools/cb.py` |
|---|---|---|
| What | A Claude skill: the eight actions in natural language | A measuring instrument: one file, standard library only |
| Judgment | Yes: classifies, proposes, asks | None: counts, joins, derives, checks thresholds |
| Writes | Only with explicit approval from the person (C2) | Only with `--write`; dry-run by default |
| Determinism | No | Yes: stable order everywhere, no sampling |

This split is the core design decision. Everything that needs judgment (is this a
decision or an observation? which customer? does B contradict A?) goes through the
model and a human. Everything that can be counted is counted by code, so that a number
in a report is reproducible and a gate can fail.

## The eight actions

| Action | What it does |
|---|---|
| `capture` | Documents something through a *recover-before-create* ladder: does it exist? is it stale? does it belong to someone else? is a 5-line note enough? is an index entry enough? Only then does it create a note. |
| `extract` | Bulk-ingests a raw source. Fingerprints it so the same source is never processed twice silently, deduplicates by `problem_tag`, and appends `occurrences` rather than creating new notes. |
| `maintain` | Passive staleness, `superseded_by` derivation, broken links and a prioritised validation queue. It never sets `validated: true` and never invents a hook result. |
| `retrieve` | Hybrid candidate search with calibration by **known defects**. Every result carries its status label. |
| `validate` | The only step that asks for human effort: a bounded weekly ritual of at most 5 notes. |
| `manifest` | A cheap index, so an agent can decide which note to open without grepping the whole tree. |
| `health` | Artifact hygiene plus `cb.py gates`. It reports and proposes; it never moves or deletes. |
| `enrich` | Normalises search terms against the ontology and proposes typed links. It never changes note bodies. |

## The note contract

Every note carries `type`, `owner`, `occurred_on`, `captured_on`, `expires_on`,
`validated`, `status`, `confidence`, `layer` and at least four `search_terms`. Each type
adds its own fields: `occurrences` with `evidence_basis` on observations, the three lint
pieces on metrics, and `contrasts_with` on glossary entries. The full contract is in
[`skill/references/contrato-de-notas.md`](../skill/references/contrato-de-notas.md).

Three rules do most of the work:

- **Expiry is a feature.** Every note is born with an expiry date that depends on its
  type (90 to 365 days). An old note isn't wrong, but nobody has looked at it, and the
  system says so.
- **Two clocks.** `occurred_on` (the event) and `captured_on` (the writing) are never
  conflated. See [findings §1](findings.md#1-a-mechanism-built-on-a-field-nobody-could-fill).
- **Reported vs measured.** A number a customer said on a call is
  `evidence_basis: client-reported`, and nothing downstream may present it as a
  measurement.

## Two graphs that never mix

| | `graph.jsonl` | `entity-graph.jsonl` |
|---|---|---|
| Is | human judgment, note ↔ note | mechanical derivation from frontmatter |
| Verbs | four closed verbs: `refuerza`, `contradice`, `extiende`, `depende-de` | `decide_sobre`, `observa_a`, `afecta_a` (dated), `trata_de`, `usa_canal`, `menciona` (weight 0.3)… |
| Written by | `enrich`, edge by edge, with confirmation | `cb.py grafo --write`, in seconds |
| If lost | **cannot be recovered**: it is judgment, not data | regenerated |

The derived graph includes the human edges *by reference*, marked `method: humano`, so
both can be walked together without the good edges ever being copied or regenerated.
Every edge records where it came from (`declared_on`, `declared_via`, `method`). An edge
without provenance can't be told apart from an invented one.

A contradiction between two notes never marks either note as `contradicted`. That flag
is reserved for checks against external reality. A note-vs-note contradiction puts both
notes at the top of the validation queue, and a human decides which one survives.

## Derived files are sealed

A derived file committed to git goes stale silently. It's still there and looks valid,
and it serves answers from the day before yesterday. Every derived artifact carries a
`_meta.firma`: a hash of every note's frontmatter, the config files and **the code of
`cb.py` itself**. Commands that read a derived file warn `OBSOLETO` when the signature no
longer matches.

## Measurement

`cb.py stats` produces every number. `metrics.json` decides which of those numbers
matter, in which unit and in which direction, with two thresholds (`gate` is the floor,
`aviso` is the target) and a written reason for each. `cb.py gates` evaluates them and
appends the run to `runs.jsonl`, so the history of the canon's health is itself data.
`cb.py surface` measures the instruction surface of the skill, because a prompt that
only grows is a prompt nobody prunes.

## Why there is no server

The skill queries the canon directly on the filesystem. That is a deliberate scope
decision, not a missing feature. A served index (MCP or otherwise) is an operational
cost. The retrieval levers that would need one (stemming, query expansion, lexical
boosts) are proven on the sibling personal vault first, and only move here if they
earn their place with a measured gain.
