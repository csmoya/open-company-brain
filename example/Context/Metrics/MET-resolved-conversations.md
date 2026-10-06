---
type: metric
title: "Resolved conversations"
project: Kestrel
company_brain_track: canon
layer: knowledge
confidence: high
source_of_truth: vault
captured_via: direct
owner: Lena Fischer
captured_on: 2026-07-10
last_validated: 2026-07-14
expires_on: 2027-01-06
validated: true
status: active
source_project: Kestrel
query_ref: "metabase:1042"
verify_hooks: [chart_exists, query_runs]
definition_includes: "Conversations closed by an agent or the bot with no new inbound message from the end customer within 72 hours of closing."
definition_excludes: "Conversations closed by auto-timeout, spam, test conversations from internal numbers, and the duplicate record a human handoff opens (counted once, on the original)."
search_terms:
  - "[[Conversation]]"
  - "[[Resolution]]"
  - "[[Human handoff]]"
---

# Resolved conversations

**Definition.** See `definition_includes` / `definition_excludes`. The unit is a
[[GL-conversation|conversation]], not a [[GL-session|session]].

**Canonical view.** Metabase question 1042, "Resolved conversations by workspace, weekly".
Any other chart with this name is a copy and may be wrong.

**Gotchas.**
- Auto-timeout closes look like resolutions in the raw table (`closed_by = system`). They are
  excluded, and that exclusion is the part people forget.
- Handoffs create a second conversation record ([[OB-handoff-double-counts-conversation-quota]]);
  the view dedupes on `root_conversation_id`. Raw counts are ~10 % higher.
- Since July this is also the billing unit for per-conversation customers, so a change to this
  definition is a pricing change. Finance signs off on edits.
