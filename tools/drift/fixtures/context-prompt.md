/build-vs-buy:build-vs-buy email notifier

Answers for the interview. Give each answer when you ask the matching question:

- Must-haves now: send an email from the API when a report finishes, from our own domain (SPF and DKIM); retry a failed send without losing the message. Deferred: per-user opt-out; bounce and complaint handling; delivery status visibility. Nice-to-have: hosted templates; open and click tracking.
- Environment: production. Business stage: pre-revenue. Expected growth: 5,000 monthly active users in a year, from about 500; about 2,000 emails a month, from 200.
- Core-ness: not a core part of the product.
- Candidates: accept your proposal as long as it includes build and keeps hosted and self-hosted versions separate.

If you cannot find a document that describes the stack, use this text as the stack document:

Python 3.12 API (FastAPI) and a React front end, one repo. Postgres 16 (managed, single instance), no Redis, no message broker. Containers on a single small Kubernetes cluster, config as YAML in the repo. Secrets live in the cloud provider's secret manager, nothing in the repo. One engineer, part time. Guardrails: prefer managed over self-hosted; no new stateful component without a backup story; a new vendor needs a free tier or under 50 USD a month at current volume; no tool may hold production secrets outside the secret manager.

I confirm Checkpoint 1 in advance, exactly as you would show it. Do not wait for another message: write locked-context.md into the run directory right after you show Checkpoint 1, then stop. Do not start research.
