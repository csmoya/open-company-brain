---
type: decision-log
title: "Acme Build adds web chat after the pilot, routed to the same inbox"
project: Kestrel
company_brain_track: canon
layer: decision
confidence: high
source_of_truth: vault
captured_via: direct
owner: Jonas Berg
occurred_on: 2026-07-02
captured_on: 2026-07-03
expires_on: 2026-12-30
validated: false
status: active
source_project: Kestrel
client_name: "Acme Build"
client_id: cid-0001
supersedes: []
search_terms:
  - "[[Web chat]]"
  - "[[WhatsApp Business API]]"
  - "[[Salesforce]]"
  - "[[Routing rules]]"
---

# Acme Build adds web chat after the pilot, routed to the same inbox

**Decision (2026-07-02, pilot review).** Acme converts to an annual contract and turns on web
chat on the redesigned site. Web chat and WhatsApp land in the same inbox; routing rules send
anything with an order number to the dispatch team, everything else to sales.

**Why now.** The agency redesign shipped early, and the dispatch team asked for one inbox
instead of two after the pilot.

**Relationship to the pilot decision.** The March decision ([[DL-acme-build-whatsapp-only-pilot]])
deferred web chat for a reason that no longer exists. Whether that is a supersession or a
scope extension is a human call, and it has not been made.
