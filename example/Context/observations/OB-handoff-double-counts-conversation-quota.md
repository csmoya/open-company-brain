---
type: observation
title: "Human handoff opens a second conversation and double-counts the quota"
project: Kestrel
company_brain_track: canon
kind: anti-pattern
shareable: true
problem_tag: "quota-double-count-on-handoff"
severity: medium
layer: diagnosis
confidence: high
source_of_truth: vault
captured_via: extraction
source_id: "fathom:8812"
owner: Lena Fischer
occurred_on: 2026-02-10
captured_on: 2026-04-20
expires_on: 2027-04-20
validated: false
status: active
source_project: Kestrel
client_name: "Beta Corp"
client_id:
  - cid-0002
  - cid-0007
  - cid-0004
occurrences:
  - date: 2026-02-10
    client_id: "cid-0002"
    transcript_ref: "fathom:8812 — Beta Corp Q1 business review, 00:31:05"
    quote: "Every chat that goes to a human seems to cost us twice."
    evidence_basis: client-reported
  - date: 2026-05-14
    client_id: "cid-0007"
    transcript_ref: "partner call, Hooli Labs reseller desk"
    quote: "Three of our end customers asked why escalations eat two conversations."
    evidence_basis: client-reported
  - date: 2026-07-09
    client_id: "cid-0004"
    transcript_ref: "billing export, Northwind workspace, June 2026"
    quote: "1,184 of 9,960 billed conversations were counted twice; every one of them had a handoff."
    evidence_basis: measured
search_terms:
  - "[[Conversation quota]]"
  - "[[Human handoff]]"
  - "[[Web chat]]"
  - "[[Pricing]]"
---

# Human handoff opens a second conversation and double-counts the quota

**What happens.** When the bot hands a [[GL-conversation|conversation]] to a human agent, the
inbox opens a new conversation record instead of re-assigning the existing one. The quota
counter sees two conversations.

**Why it matters more now.** Under per-seat pricing this was an annoyance. Since Beta Corp moved
to per-conversation pricing ([[DL-beta-corp-moves-to-conversation-pricing]]) it is a billing
error with a customer's name on it.

**Evidence quality.** Beta Corp and Hooli Labs reported the symptom; Northwind's June billing
export is the only measurement (about 12 % of billed conversations double-counted). Do not
quote "12 %" for the other two customers: we never measured theirs.
