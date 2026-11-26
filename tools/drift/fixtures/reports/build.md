<!-- Frozen build estimate. Written by hand in the shape the orchestrator writes in Step 2. Every number is an estimate, not a measurement. -->

# Build: outbox, worker and self-run mail server

1. **Identity**: a custom notifier. A Postgres outbox table written by the API when a report finishes, a small worker that sends from the outbox, and a self-run mail server (Postfix) that delivers directly to recipients' mail servers. Build, self-hosted, no license.
2. **Release and staleness**: not applicable, it does not exist yet. prerelease: none
3. **Must-have coverage**: send on report finish: met, via the outbox row. Own domain with SPF and DKIM: needs configuration (DNS records and a DKIM key on the mail server). Retry without loss: met by the outbox, estimate. Deferred: opt-out needs custom glue; bounce and complaint handling needs custom glue and a mailbox to read bounces from; delivery status visibility needs custom glue. Nice-to-have: hosted templates cannot be done without building a template layer; open and click tracking cannot be done without building it.
4. **Features used versus offered**: all features built are features used, 0 offered but unused (estimate).
5. **Install and operations**: components: outbox table, worker, Postfix. The outbox is state in the existing Postgres. Postfix needs a persistent queue and a backup story. High availability not needed at this volume. Estimated 3 to 5 days to build and deploy (estimate, basis: one engineer, part time, no prior mail-server experience stated). Needs outbound port 25 open and a fixed IP with a reverse DNS record; whether the cluster provider allows port 25 is unknown.
6. **Integration facts**: new code in the existing repo. Config as YAML like the rest of the stack. Needs database credentials for the worker and DKIM private key storage; the stack's guardrail says no production secrets outside the secret manager, so the DKIM key must come from the secret manager.
7. **Maintenance facts**: upgrades to Postfix and the worker are on the owner. Estimated 4 to 8 hours a month (estimate, basis: queue and deliverability monitoring, patching, blocklist checks). Maintained by the owner alone.
8. **Cost**: estimated up to 10 USD a month for a fixed IP or small server if the cluster cannot provide one (estimate, unverified); otherwise 0 USD.
9. **Security facts**: holds secrets (DKIM key and database credentials). Exposes a new network surface (an SMTP service reachable from the internet is not required for sending, but outbound port 25 and the mail server's own ports need review). Needs no elevated cluster permissions (estimate).
10. **Lock-in**: none to a vendor. Switching to a hosted service later means replacing the worker's send call, estimated 0.5 to 1 day.
11. **Scaling**: no limit at 2,000 emails a month. Deliverability and IP reputation, not volume, are the limit; a new sending IP has no reputation.
12. **Sources**: none. This report is an estimate from the stack summary.
13. **Could not verify**: whether port 25 is open from the cluster; the cost of a fixed IP; every effort and maintenance figure above.
