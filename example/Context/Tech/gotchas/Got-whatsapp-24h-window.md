---
type: gotcha
title: "Free-form WhatsApp replies fail outside the 24-hour customer-service window"
project: Kestrel
company_brain_track: tech
severity: high
layer: diagnosis
confidence: high
source_of_truth: vault
captured_via: direct
owner: Priya Natarajan
captured_on: 2026-04-08
last_validated: 2026-04-08
expires_on: 2027-04-08
validated: true
status: active
source_project: Kestrel
repo: "kestrel-core"
related_files: ["services/router/adapters/whatsapp.py"]
modules: ["whatsapp-adapter"]
search_terms:
  - "[[WhatsApp Business API]]"
  - "[[Message templates]]"
  - "[[Delivery status]]"
---

# Free-form WhatsApp replies fail outside the 24-hour window

An agent can only send a free-form WhatsApp message within 24 hours of the end customer's last
inbound message. After that, only an approved template goes through. The API accepts the
request and fails it later, asynchronously — which, before the September fix, looked exactly
like the "shown as sent" bug.

First hit in the Acme Build pilot: dispatch replied to Friday's messages on Monday morning.
The composer now greys out free text and offers templates when the window is closed.
