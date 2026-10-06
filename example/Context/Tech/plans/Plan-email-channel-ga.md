---
type: plan
title: "Email channel to GA by mid-December"
project: Kestrel
company_brain_track: tech
layer: application
confidence: medium
source_of_truth: vault
captured_via: direct
owner: Tomás Reyes
captured_on: 2026-08-01
expires_on: 2026-10-30
validated: false
status: active
source_project: Kestrel
client_name: "Beta Corp"
client_id: cid-0002
target_completion: 2026-12-15
version: 1.2
last_updated: 2026-09-22
involved_repos: ["kestrel-core", "kestrel-inbox-web"]
search_terms:
  - "[[Email]]"
  - "[[Inbox]]"
  - "[[Message router]]"
---

# Email channel to GA by mid-December

Beta Corp is the design partner: 60 % of their volume is email, and the per-conversation
pricing deal assumed email would be billable by Q4.

| phase | scope | status |
|---|---|---|
| 1 | IMAP ingest, threading by `Message-ID`/`References` | done |
| 2 | Outbound via customer's SMTP or our relay, DKIM | in progress |
| 3 | Email ↔ conversation merge (same customer on web chat and email) | not started |
| 4 | GA: billing, docs, onboarding guide | not started |

**Biggest risk.** Phase 3 decides whether an email thread and a web chat about the same order
are one [[GL-conversation|conversation]] or two. That is a billing decision dressed up as an
engineering one.

Scratch notes for this plan live next to it in `email-ga-scratch.md`, which has no frontmatter
and therefore shows up in `cb.py contract`.
