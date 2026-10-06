---
type: observation
title: "The web chat launcher covers the cookie consent banner on mobile"
project: Kestrel
company_brain_track: canon
kind: anti-pattern
shareable: true
problem_tag: "web-chat-launcher-covers-consent-banner"
severity: medium
layer: diagnosis
confidence: medium
source_of_truth: vault
captured_via: extraction
source_id: "intercom:conv-55120"
owner: Maya Okafor
captured_on: 2026-09-16
expires_on: 2027-09-16
validated: false
status: active
source_project: Kestrel
client_name: "Gamma Labs"
client_id:
  - cid-0003
  - cid-0006
occurrences:
  - date: 2026-06-02
    client_id: "cid-0003"
    transcript_ref: "intercom:conv-55120"
    quote: "On iPhone the chat bubble sits on top of the Accept button, so visitors cannot dismiss the banner."
    evidence_basis: client-reported
  - date: 2026-08-11
    client_id: "cid-0006"
    transcript_ref: "support ticket KES-5102 (Initech)"
    quote: "Our consent rate on mobile dropped after we installed the widget."
    evidence_basis: client-reported
  - date: 2026-09-15
    client_id: "cid-0003"
    transcript_ref: "support ticket KES-5390 (Gamma Labs)"
    quote: "Still happening after the CSS workaround on Android."
    evidence_basis: client-reported
search_terms:
  - "[[Web chat]]"
  - "[[Launcher]]"
  - "[[Consent banner]]"
---

# The web chat launcher covers the cookie consent banner on mobile

The launcher uses a fixed `z-index` higher than most consent-management platforms, and on
viewports under 400 px it lands exactly on the bottom-right "Accept" button. Gamma Labs reported
it twice, Initech once. Initech's "consent rate dropped" is their reading of their own
analytics, not something we measured.

**Gap in this note.** It was extracted from the Intercom conversation in September, and nobody
filled `occurred_on` even though the source date is in `extraction-log.jsonl`.
`cb.py dates` proposes it.
