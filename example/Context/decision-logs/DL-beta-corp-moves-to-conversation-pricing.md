---
type: decision-log
title: "Beta Corp moves to per-conversation pricing mid-contract"
project: Kestrel
company_brain_track: canon
layer: decision
confidence: high
source_of_truth: vault
captured_via: extraction
source_id: "fathom:9310"
owner: Lena Fischer
occurred_on: 2026-06-18
captured_on: 2026-06-19
last_validated: 2026-07-01
expires_on: 2026-12-16
validated: true
status: active
source_project: Kestrel
client_name: "Beta Corp"
client_id: cid-0002
supersedes: ["[[DL-beta-corp-per-seat-pricing]]"]
search_terms:
  - "[[Pricing]]"
  - "[[Conversation quota]]"
  - "[[Human handoff]]"
  - "[[Email]]"
---

# Beta Corp moves to per-conversation pricing mid-contract

**Decision (2026-06-18).** Beta Corp switches from 42 seats to a per-conversation plan
(EUR 0.38 per resolved conversation, floor of EUR 1,100/month) from 1 July, without waiting
for the renewal.

**What changed since [[DL-beta-corp-per-seat-pricing]].** Their CFO stopped caring about seat
forecasts once Q2 volume dropped 40 % and they were still paying for 42 seats. The argument
that won in February ("we can forecast seats") lost to "we are paying for chairs nobody sits in".

**Open risk.** Per-conversation pricing makes the quota counter a billing system. The counter
double-counts conversations that go through a human handoff — see
[[OB-handoff-double-counts-conversation-quota]]. Until that is fixed, every Beta Corp invoice
needs a manual check by RevOps.

**Bet.** `bet-0001` in `bets.jsonl` predicted this would end Beta Corp's billing complaints.
It did not (closed 2026-08-21, with evidence).
