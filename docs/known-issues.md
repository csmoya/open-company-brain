# Known issues

These were found while building the example canon. Each one has a fixture case to write
first (C38: the test has to go red before the fix counts).

| # | Area | Issue | Workaround today |
|---|---|---|---|
| 1 | frontmatter | A block-list `supersedes:` (one `- "[[X]]"` per line) parses as empty, so `stats` and `contradicciones` count 0. This is the same class of bug as the scalar-vs-list `client_id` one that was already fixed. | Use the inline form `supersedes: ["[[X]]"]`. |
| 2 | frontmatter | `search_terms` is read as everything after the key up to the end of the frontmatter, so wikilinks under later keys (`supersedes`, `connections`, `contrasts_with`) count as search terms. | Put `search_terms` last. |
| 3 | `supersession` | It still proposes pairs that are already declared with `supersedes` / `status: superseded`. | Ignore declared pairs in the output. |
| 4 | `supersession` | It groups by the raw `client_name` instead of the resolved `client_id`, so "Acme Build Ltd." and "Acme Build" never pair up. | Use one spelling. |
| 5 | `cruce` | There is no `Email` channel family, and `cruce` ignores `canales_ontologia`. | None. |
| 6 | graph | The same client can have the same channel as both `usa_canal` and `menciona_canal`, because mentions are subtracted per note, not per client. | Read `[declarado]` first. |
| 7 | graph | A multi-client observation declares its channels for every client in its `client_id`. | Keep shared observations channel-neutral, or accept the over-attribution. |
| 8 | `graph.jsonl` | The node is built as `"Context/" + source + ".md"`. The skill documents `[[ID]]`, and bare IDs produce dangling nodes. | Write paths with their subfolder (`observations/OB-…`). |
| 9 | `vecinos` | `--saltos 2` repeats edges from both ends and walks back to the start node. | Use 1 hop plus `--rel`. |
| 10 | derived files | The signature hashes `cb.py`, so any engine change marks `example/` as `OBSOLETO` until it is regenerated. This is intended, but easy to forget before a release. | `CB_BASE=example python3 tools/cb.py grafo --write` before committing an engine change. |
| 11 | paths | `CB_BASE` is relative to the working directory. | Run from the repo root. |
