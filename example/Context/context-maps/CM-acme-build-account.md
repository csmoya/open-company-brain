---
type: context-map
title: "Acme Build — account map after the pilot"
project: Kestrel
company_brain_track: canon
layer: knowledge
confidence: medium
source_of_truth: vault
captured_via: direct
owner: Jonas Berg
occurred_on: 2026-08-12
captured_on: 2026-08-14
expires_on: 2026-11-12
validated: false
status: active
source_project: Kestrel
client_name: "Acme Build Ltd."
client_id: cid-0001
search_terms:
  - "[[WhatsApp Business API]]"
  - "[[Web chat]]"
  - "[[Salesforce]]"
  - "[[Routing rules]]"
---

# Acme Build — account map after the pilot

- **Who they are.** Building-materials supplier, 14 depots, 60 inbox users (dispatch + sales).
- **Channels.** WhatsApp since the March pilot, web chat since July
  ([[DL-acme-build-adds-web-chat]]). Email stays in their old helpdesk; they have no plans to move it.
- **Systems.** Salesforce is the source of truth for orders; Kestrel looks up the order number
  from the conversation and posts back a case.
- **People.** Dispatch lead is the champion. IT is a single contractor, so anything needing a
  DNS change takes two weeks.
- **Commercial.** Bought directly, not through Hooli Labs, although Hooli Labs pitched them first.
- **Known pain.** Template rejections shown as sent ([[OB-whatsapp-template-rejections-shown-as-sent]]).

`client_name` here is written "Acme Build Ltd." on purpose: `cb.py entities` resolves it to the
same client (`cid-0001`) and records the variant as an alias.
