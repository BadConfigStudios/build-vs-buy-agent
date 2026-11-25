---
name: stops-at-checkpoint-1
tags: [checkpoint]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob, Grep]
---

/build-vs-buy secret rotation for a small Kubernetes cluster

Answers for the interview (the working directory is an empty sandbox, so the setup is described here instead of in repo docs):

- Must-haves now: scheduled rotation without downtime. Deferred: none. Nice-to-have: none.
- Environment: production. Business stage: pre-revenue. Expected growth: 50 secrets within a year.
- Core-ness: not a core part of the product.
- Stack summary: a single managed Kubernetes cluster on AWS, deployed with Helm through GitOps (Argo CD). Secrets are plain Kubernetes Secrets today. No policy constrains new tools beyond "no cluster-admin operators".

Propose candidates and show me the checkpoint.
