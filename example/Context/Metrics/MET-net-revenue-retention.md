---
type: metric
title: "Net revenue retention (NRR)"
project: Kestrel
company_brain_track: canon
layer: knowledge
confidence: low
source_of_truth: vault
captured_via: direct
owner: Lena Fischer
captured_on: 2026-09-02
expires_on: 2027-03-01
validated: false
status: active
source_project: Kestrel
query_ref: "TODO"
verify_hooks: [query_runs]
definition_includes: "Recurring revenue this month from customers who were paying 12 months ago, divided by their recurring revenue 12 months ago."
search_terms:
  - "[[Pricing]]"
  - "[[Retention]]"
---

# Net revenue retention (NRR)

**Not validated, on purpose.** Two of the three lint pieces are missing:

- **What does NOT count** is undecided. Do partner-resold accounts (Hooli Labs' end customers)
  count as one customer or many? Finance and Sales give different answers, and the number moves
  by about 6 points depending on which one you pick.
- **Canonical view** does not exist yet (`query_ref: TODO`). Three spreadsheets compute it three ways.

Until both are settled, nobody should quote NRR in a board deck. This note exists to make the
gap visible, not to paper over it.
