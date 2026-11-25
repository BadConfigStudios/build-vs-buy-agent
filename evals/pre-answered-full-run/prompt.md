---
name: pre-answered-full-run
tags: [full-run]
runs: 1
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Read, Glob, Grep, Agent, Write, Bash, WebSearch, WebFetch]
---

Use the build-vs-buy skill to analyse: secret rotation for a small Kubernetes cluster (quick mode, `--quick`).

This is non-interactive, so every answer is given here. Do not ask questions; treat every checkpoint as confirmed.

- Must-haves now: rotate secrets on a schedule without downtime. Deferred: audit log. Nice-to-have: web UI.
- Environment: production.
- Business stage: pre-revenue.
- Expected growth: 50 secrets within a year.
- Core-ness: not a core part of the product.
- Stack summary (the working directory is an empty sandbox, so it is given here): a single managed Kubernetes cluster on AWS, deployed with Helm through GitOps (Argo CD). Secrets are plain Kubernetes Secrets today. No policy constrains new tools beyond "no cluster-admin operators".
- Candidates: build (a small script), External Secrets Operator, HashiCorp Vault.
- Checkpoint 1: confirmed as stated above.
- Checkpoint 2: scores are final, no challenges.

Write the analysis to docs/analysis/ and generate the HTML view.
