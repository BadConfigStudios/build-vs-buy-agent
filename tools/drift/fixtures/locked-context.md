---
topic: email notifier
date: 2026-11-26
matrix_version: 1.3
mode: full
environment: production
business_stage: pre-revenue
expected_growth: 5,000 monthly active users in a year, from about 500 (about 2,000 emails a month, from 200)
core_ness: not core
---

## Must-haves

- now: send an email from the API when a report finishes, from the owner's own domain (SPF and DKIM); retry a failed send without losing the message
- deferred: per-user opt-out; bounce and complaint handling; delivery status visibility
- nice-to-have: hosted templates; open and click tracking

## Stack summary

- Runs now: Python 3.12 API (FastAPI) and a React front end in one repo. Managed Postgres 16, single instance. No Redis and no message broker.
- Deployment: containers on a single small Kubernetes cluster, config as YAML in the repo.
- Secrets: kept in the cloud provider's secret manager; nothing stored in the repo. The provider is not named.
- Operations: one engineer, part time.
- Guardrails: prefer managed services over self-hosted ones; no new stateful component without a backup story; a new vendor needs a free tier or a monthly cost under 50 USD at current volume; no tool may hold production secrets outside the secret manager.

## Candidates

- Build (build)
- Amazon SES (hosted)
- Postmark (hosted)
- Resend (hosted)
- Postal (self-hosted)
