---
type: observation
title: "WhatsApp template messages rejected by Meta show as 'sent' in the inbox"
project: Kestrel
company_brain_track: canon
kind: anti-pattern
shareable: true
problem_tag: "whatsapp-template-rejected-silently"
severity: high
layer: diagnosis
confidence: high
source_of_truth: vault
captured_via: extraction
source_id: "fathom:9034"
owner: Maya Okafor
occurred_on: 2026-04-03
captured_on: 2026-04-06
last_validated: 2026-08-28
expires_on: 2027-04-06
validated: true
status: active
source_project: Kestrel
client_name: "Acme Build"
client_id:
  - cid-0001
  - cid-0004
  - cid-0005
occurrences:
  - date: 2026-04-03
    client_id: "cid-0001"
    transcript_ref: "fathom:9034 — Acme Build pilot review, 00:14:20"
    quote: "Dispatch sent the delivery-window template to forty foremen and half of them never got it, but the inbox says sent."
    evidence_basis: client-reported
  - date: 2026-05-21
    client_id: "cid-0004"
    transcript_ref: "support ticket KES-4471 (Northwind Retail)"
    quote: "Order-shipped notifications stopped arriving on Friday; Kestrel shows them all as sent."
    evidence_basis: client-reported
  - date: 2026-06-09
    client_id: "cid-0005"
    transcript_ref: "fathom:9277 — Umbrella Health weekly sync"
    quote: "Appointment reminders silently dropped after Meta re-categorised the template as marketing."
    evidence_basis: client-reported
  - date: 2026-08-27
    client_id: "cid-0004"
    transcript_ref: "delivery-status export, Northwind workspace, week 2026-08-20..27"
    quote: "31 of 212 template sends came back with Meta error 132015 and were displayed as sent."
    evidence_basis: measured
search_terms:
  - "[[WhatsApp Business API]]"
  - "[[Message templates]]"
  - "[[Delivery status]]"
  - "[[Inbox]]"
---

# WhatsApp template messages rejected by Meta show as "sent" in the inbox

**What happens.** When Meta rejects a template send asynchronously (paused template,
re-categorised to marketing, quality rating dropped), the rejection arrives as a later status
webhook. The message router stores the first `accepted` response and never downgrades it, so
the inbox keeps showing a single grey tick: "sent".

**Who it hit.** Acme Build, Northwind Retail (twice) and Umbrella Health — three customers,
four occurrences between April and August. The August occurrence is the only one with a
number we measured ourselves (31 of 212 sends in one week, from the delivery-status export);
the rest are what customers told us.

**Root cause (confirmed by Priya, 2026-08-28).** `status` is written once on the synchronous
response and the async `failed` webhook is dropped as "out of order". See [[Sys-message-router]]
and [[Got-whatsapp-24h-window]], which is a different trap that produces similar symptoms.

**Fix.** Shipped 2026-09-04: async failures now downgrade the status and raise an inbox
banner. `bet-0002` is open on whether this ends the reports.
