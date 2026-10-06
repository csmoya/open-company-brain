---
type: decision-log
title: "Acme Build pilots Kestrel on WhatsApp only; web chat deferred"
project: Kestrel
company_brain_track: canon
layer: decision
confidence: medium
source_of_truth: vault
captured_via: extraction
source_id: "fathom:8930"
owner: Jonas Berg
occurred_on: 2026-03-12
captured_on: 2026-05-02
expires_on: 2026-10-29
validated: false
status: active
source_project: Kestrel
client_name: "Acme Build"
client_id: cid-0001
supersedes: []
search_terms:
  - "[[WhatsApp Business API]]"
  - "[[Web chat]]"
  - "[[Salesforce]]"
  - "[[Pilot scope]]"
---

# Acme Build pilots Kestrel on WhatsApp only; web chat deferred

**Decision (2026-03-12, pilot kickoff).** The 90-day pilot covers WhatsApp only. Web chat on
acmebuild.example is out of scope; their marketing agency owns the site and will not touch it
before the summer redesign.

**Why WhatsApp first.** 70 % of Acme's inbound orders from site foremen already arrive over
personal WhatsApp numbers (client-reported, not measured). Moving that to a shared inbox with
Salesforce lookup is the whole business case.

**Consequence we accepted.** No web chat means no deflection numbers for the pilot review, so
success is judged on order-capture time only.

> Note for whoever validates this: [[DL-acme-build-adds-web-chat]] (July) looks like it
> reverses this. Nobody has decided yet whether it *supersedes* it or just extends the scope.
> `cb.py supersession` flags the pair.
