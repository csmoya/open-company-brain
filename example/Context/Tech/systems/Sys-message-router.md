---
type: system
title: "Message router: how inbound and outbound messages move between channels and the inbox"
project: Kestrel
company_brain_track: tech
layer: knowledge
confidence: high
source_of_truth: vault
captured_via: direct
owner: Priya Natarajan
captured_on: 2026-09-10
last_validated: 2026-09-10
expires_on: 2026-12-09
validated: true
status: active
source_project: Kestrel
repo: "kestrel-core"
related_files: ["services/router/dispatch.py", "services/router/status.py", "services/router/webhooks.py"]
modules: ["message-router", "delivery-status", "webhooks"]
verify_hooks:
  - type: file_exists
    target: related_files
  - type: grep_repo
    repo: kestrel-core
    pattern: "def downgrade_status"
    expect: present
search_terms:
  - "[[Message router]]"
  - "[[Delivery status]]"
  - "[[WhatsApp Business API]]"
  - "[[Webhooks]]"
---

# Message router

Every message, in or out, passes through `dispatch.py`. Channel adapters (web chat, WhatsApp
Cloud API, email over SMTP/IMAP) normalise to one envelope; the router writes it to the inbox
and fans out to customer webhooks.

**Delivery status** lives in `status.py`. Until 2026-09-04 a status could only move forward
(`queued → sent → delivered → read`), so an asynchronous failure after `sent` was dropped. That
is the root cause of [[OB-whatsapp-template-rejections-shown-as-sent]].
`downgrade_status()` now allows `sent → failed`.

**Customer webhooks** retry per [[DL-tech-webhook-retries-exponential-backoff]].
