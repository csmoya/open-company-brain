---
type: decision-log
title: "Outbound webhooks retry with exponential backoff, capped at 6 attempts"
project: Kestrel
company_brain_track: tech
layer: decision
confidence: high
source_of_truth: vault
captured_via: direct
owner: Priya Natarajan
occurred_on: 2026-04-22
captured_on: 2026-04-22
expires_on: 2026-10-19
validated: false
status: active
source_project: Kestrel
supersedes: []
search_terms:
  - "[[Webhooks]]"
  - "[[Message router]]"
  - "[[Retries]]"
---

# Outbound webhooks retry with exponential backoff, capped at 6 attempts

**Decision.** Failed outbound webhooks retry at 30 s, 2 min, 8 min, 32 min, 2 h, 8 h, then go to
the dead-letter queue. Before this, we retried every 10 s forever, and one customer's broken
endpoint took down the router for everyone (incident 2026-04-19).

**Trade-off.** A customer endpoint that is down for more than ~11 hours loses events until
someone replays them by hand — see [[Run-replay-failed-webhooks]].
