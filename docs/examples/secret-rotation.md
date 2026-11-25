# Worked example 1: secret rotation, HashiCorp Vault versus a rotation script

Context: a handful of API keys rotated every 90 days. Must-haves: store a few secrets, rotate on a schedule, deliver to the right workloads. Core-ness: not core to the product, so lean adopt unless the build is trivial. (Scored before the stage, maturity, and scaling modifiers existed; with a pre-revenue stage, cost drops one point for any paid option and the result does not change.)

Vault (self-hosted):
- Fit 5, times 2 is 10.
- Unused baggage 1 (about 10 to 15% used), times 1 is 1.
- Install 2, times 1 is 2.
- Integration 3, times 1 is 3.
- Maintenance 2 with a plus one community modifier, so 3, times 3 is 9.
- Dependencies 3 (one heavy, stateful product), times 2 is 6.
- Lock-in 3, times 1 is 3.
- Cost 5 (free self-hosted), times 1 is 5.
- Time to value 2, times 2 is 4.
- Security 5, minus one for secrets, minus one for elevated permissions, plus one for active releases, so 4, times 3 is 12.
- Total 55 out of 85, about 65%.

Rotation script:
- Fit 4, times 2 is 8.
- Unused baggage 5, times 1 is 5.
- Install 5, times 1 is 5.
- Integration 5 (4 plus alignment bonus, capped at 5), times 1 is 5.
- Maintenance 4 with a minus one ownership-risk modifier because it touches secrets alone, so 3, times 3 is 9.
- Dependencies 5, times 2 is 10.
- Lock-in 5, times 1 is 5.
- Cost 5, times 1 is 5.
- Time to value 4, times 2 is 8.
- Security 5, minus one for touching secrets, so 4, times 3 is 12.
- Total 72 out of 85, about 85%.

Result: the script wins clearly at the current scale. Revisit if the number of secrets or rotation targets grows past roughly ten, or if audit trails or per-customer isolation become requirements. If that happens, look at something lighter than Vault first (for example External Secrets Operator with a managed store) before Vault itself. Note that the script would score a scaling minus one once the secret count grows, which is exactly the warning the scaling modifier is meant to give.
