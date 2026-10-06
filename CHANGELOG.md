# Changelog

## 0.7.1 — 2026-10-06 · first public release

The engine as it runs in a real deployment of about 1,300 notes, with the content
removed and the history condensed.

- **Engine** (`tools/cb.py`): 14 subcommands, standard library only, dry-run by default,
  deterministic. Commands: `stats`, `contract`, `entities`, `clients`, `dates`,
  `expiry`, `supersession`, `cruce`, `grafo`, `vecinos`, `normalizar`,
  `contradicciones`, `gates`, `surface`.
- **Tests** (`tools/test_cb.py`): 23 cases against a synthetic fixture, each one stating
  the bug or rule it exists for, and checked by mutation.
- **Skill** (`skill/SKILL.md`): eight actions, twelve note types in two tracks
  (business/product and tech), 39 constraints, 12 gotchas.
- **Example canon** (`example/`): Kestrel, a fictional SaaS company.
- **Leak check** (`tools/leak_check.py`): a pre-commit hook against a private denylist,
  plus generic patterns in CI.
- New: `project_name()`. Generated reports take the project name from the canon instead
  of a hardcoded value. `surface` falls back to `skill/SKILL.md`.

## How it got here (condensed)

| Version | What changed and why |
|---|---|
| 0.2 | The first version: four note types (context-map, observation, decision-log, process) with owner, expiry and validation. |
| 0.3.x | Added `metric` (with a three-piece lint) and `glossary`. Gave shareable observations structured `occurrences`. Added source fingerprinting so a transcript is never processed twice silently. One folder per type. |
| 0.4.0 | Added the tech track (system, runbook, gotcha, inventory, reference, plan), merged in from a separate technical-context skill. |
| 0.5.0 | Added the retrieval layer: an ontology with closed classes, typed note-to-note links with four closed verbs, and the `enrich` action. |
| 0.7.0 | Measurement. `cb.py` gained gates with written thresholds, two clocks (`occurred_on` / `captured_on`), the derived entity graph with provenance on every edge, retrieval-log schema 2 (`notas_usadas`, `session_id`), and bets as JSONL. The `bet` note type and the unjudged health check were retired. See [docs/findings.md](docs/findings.md). |
| 0.7.1 | Added `evidence_basis` (`measured` / `client-reported`) on every occurrence. A number someone said on a call is no longer presented as a measurement. |
