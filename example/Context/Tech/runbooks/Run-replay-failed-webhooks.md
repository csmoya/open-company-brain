---
type: runbook
title: "Replay customer webhooks from the dead-letter queue"
project: Kestrel
company_brain_track: tech
layer: application
confidence: high
source_of_truth: vault
captured_via: direct
owner: Priya Natarajan
captured_on: 2026-07-30
expires_on: 2026-10-28
validated: false
status: active
source_project: Kestrel
repo: "kestrel-core"
related_files: ["scripts/replay_dlq.py"]
modules: ["webhooks"]
search_terms:
  - "[[Webhooks]]"
  - "[[Retries]]"
  - "[[Message router]]"
---

# Replay customer webhooks from the dead-letter queue

1. Confirm the customer's endpoint is back: `curl -I` returns 2xx from our egress IP.
2. Dry run: `python scripts/replay_dlq.py --workspace <id> --since <iso> --dry-run`. Check the count.
3. Replay in order: same command without `--dry-run`. It throttles to 20 events/s.
4. Tell the customer the time range that was replayed. Their system may see duplicates if it
   received some events before failing; events carry `event_id` for dedup.
