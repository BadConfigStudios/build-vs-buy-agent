# Sample project (drift fixture)

A small web app for a pre-revenue startup. Fictional stack, used only to exercise the build-vs-buy skill.

## Stack

- Python 3.12 API (FastAPI) and a React front end, one repo.
- Postgres 16 (managed, single instance). No Redis, no message broker yet.
- Deployed as containers on a single small Kubernetes cluster, config as YAML in this repo.
- Secrets live in the cloud provider's secret manager; nothing is stored in the repo.
- One engineer, part time. About 500 monthly active users, growth expected to 5,000 in a year.

## Guardrails

- Prefer managed services over self-hosted ones; no new stateful component without a backup story.
- New vendors need a free tier or a monthly cost under 50 USD at current volume.
- No tool may hold production secrets outside the secret manager.

## Open need

Users should get an email when a report finishes. Volume today is about 200 emails a month.
