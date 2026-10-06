---
type: process
title: "How to get a WhatsApp template approved on the first try"
project: Kestrel
company_brain_track: canon
layer: application
confidence: high
source_of_truth: vault
captured_via: direct
owner: Maya Okafor
captured_on: 2026-09-01
last_validated: 2026-09-03
expires_on: 2026-11-30
validated: true
status: active
source_project: Kestrel
connections:
  - rel: depende-de
    target: "[[Got-whatsapp-24h-window]]"
    note: "templates exist because of the 24-hour window; if that rule changes this process changes"
search_terms:
  - "[[Message templates]]"
  - "[[WhatsApp Business API]]"
  - "[[Onboarding]]"
---

# How to get a WhatsApp template approved on the first try

1. **Pick the category before you write.** Utility (order, appointment, account) or marketing.
   If the message would still make sense with no purchase or appointment behind it, it is marketing.
2. **One variable per fact.** `{{1}}` for the name, `{{2}}` for the date. Never a variable that
   could hold a whole sentence: Meta reads that as a way to smuggle marketing.
3. **Submit from the customer's WABA, not ours.** Approval is per business account.
4. **Wait for `APPROVED`, then send one test to an internal number** and check the inbox shows a
   delivered tick, not just "sent" (see [[OB-whatsapp-template-rejections-shown-as-sent]]).
5. **Re-check monthly.** Meta re-categorises templates without notice.
