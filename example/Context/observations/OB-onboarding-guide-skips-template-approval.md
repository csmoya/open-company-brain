---
type: observation
title: "The onboarding guide never mentions WhatsApp template approval"
project: Kestrel
company_brain_track: canon
kind: gap-interno
shareable: false
layer: diagnosis
confidence: high
source_of_truth: vault
captured_via: extraction
source_id: "slack:cs-onboarding/1724"
owner: Tomás Reyes
captured_on: 2026-08-29
expires_on: 2027-08-29
validated: false
status: active
source_project: Kestrel
connections:
  - rel: extiende
    target: "[[OB-whatsapp-template-rejections-shown-as-sent]]"
    note: "half of the rejected templates were never submitted for the right category"
search_terms:
  - "[[Onboarding]]"
  - "[[Message templates]]"
  - "[[WhatsApp Business API]]"
---

# The onboarding guide never mentions WhatsApp template approval

Internal gap, not a customer problem. Our onboarding guide goes from "connect your number" to
"build your first flow" and skips template categories and approval entirely. New customers find
out when their first marketing-categorised reminder is rejected. Northwind Retail's ops lead
said it best on a call: they learned template categories from Meta's error codes.

The Slack thread this came from has no date we can trust (it was a forwarded export), so
`occurred_on` stays empty on purpose rather than copying `captured_on`.
