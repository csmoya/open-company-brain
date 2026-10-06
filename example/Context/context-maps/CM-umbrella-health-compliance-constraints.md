---
type: context-map
title: "Umbrella Health — compliance constraints on messaging"
project: Kestrel
company_brain_track: canon
layer: knowledge
confidence: high
source_of_truth: vault
captured_via: direct
owner: Maya Okafor
occurred_on: 2026-03-30
captured_on: 2026-04-02
last_validated: 2026-04-02
expires_on: 2026-07-01
validated: true
status: active
source_project: Kestrel
client_name: "Umbrella Health"
client_id: cid-0005
search_terms:
  - "[[HIPAA]]"
  - "[[WhatsApp Business API]]"
  - "[[Data retention]]"
  - "[[AI reply drafts]]"
---

# Umbrella Health — compliance constraints on messaging

- Patient-identifying data may not be stored outside the customer's region; message bodies are
  purged after 30 days ([[Data retention]]).
- WhatsApp is allowed only for appointment logistics, never for clinical content.
- AI features need a signed BAA with every sub-processor ([[DL-umbrella-health-no-ai-drafts-on-whatsapp]]).

**This note expired on 2026-07-01 and nobody revalidated it.** Umbrella renegotiated retention
in their August renewal, so the 30-day figure may already be wrong. `cb.py stats` counts it as
expired; `validate` should pick it up first.
