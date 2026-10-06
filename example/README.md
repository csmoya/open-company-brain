# Example canon: Kestrel (fictional)

Kestrel is a **made-up** B2B SaaS company that sells a customer-messaging product (web chat,
WhatsApp, and an email channel that is not yet GA). Its customers are fictional too: Acme Build,
Beta Corp, Gamma Labs, Northwind Retail, Umbrella Health, Initech, and Hooli Labs (a reseller).
Vandelay Industries is a prospect and has no client id yet. Any resemblance to a real company is
accidental.

The canon under `Context/` has 26 notes plus the config `cb.py` reads. Every note type in the
contract is here: decision-logs, observations, context-maps, processes, metrics, glossary,
system, gotcha, runbook, plan and source-raw. It also has the usual problems of a real canon:

- **A decision that got reversed.** Beta Corp went from per-seat to per-conversation pricing, and
  that supersession is declared. Acme Build added web chat after a WhatsApp-only pilot, and
  nobody has judged that pair yet.
- **One problem seen by three customers.** Three customers had WhatsApp templates rejected by
  Meta that still showed as "sent". The `occurrences` record which numbers we measured and
  which ones the customer reported.
- **Notes that need attention.** Two notes have expired and nobody revalidated them. One note's
  event happened a year before anyone wrote it down. One file has no frontmatter, one bet is
  overdue, and one metric is deliberately left unvalidated because two of its three lint
  pieces are missing.

## Try it

Run these from the repo root. `CB_TODAY` pins the clock so the output matches the dates in
the notes. Leave it out and expiry gets counted against your real date.

```bash
export CB_BASE=example CB_TODAY=2026-10-06

python3 tools/cb.py stats          # corpus by type, validation, expiry, the two clocks, graph, bets
python3 tools/cb.py gates          # metrics.json evaluated: 2 red, 3 amber, 3 green, each with its reason
python3 tools/cb.py supersession   # decision-log pairs on the same customer with different event dates
python3 tools/cb.py cruce --canal WhatsApp --problema whatsapp-template
                                   # which WhatsApp customers hit the "template shown as sent" problem
python3 tools/cb.py grafo --write  # rebuild the derived entity graph (162 edges, 78 nodes)
python3 tools/cb.py vecinos --nodo "Acme Build"
                                   # Acme Build's record: decisions, account map, problems, channels, by date
python3 tools/cb.py vecinos --nodo whatsapp-template-rejected-silently --saltos 2
                                   # walk from a problem to its customers and to everything else about them
python3 tools/cb.py dates          # a note whose event date is sitting in extraction-log but not in the note
python3 tools/cb.py entities       # customers resolved from client-directory, aliases, the unresolved prospect
python3 tools/cb.py contract       # the scratch file in Context/ that pretends to be canon
```

Every command is a dry run unless you pass `--write`. Only `grafo --write` (and `entities --write`)
change files here. They regenerate `entity-graph.jsonl` and `entities.json`, which are derived
files and safe to rebuild.
