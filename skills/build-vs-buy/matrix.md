# Build vs Buy Decision Matrix

Version 1.3 (starting weights; wording generalized 2026-11-24, no scale or weight changed). Written to be handed to Claude Code so it can run the evaluation and report a score. The person running the evaluation is called the owner.

## Purpose

Before building any new piece of a project, evaluate whether to build it or adopt something that already exists. Every score must come from a checkable condition below, not a gut feel. Claude Code should gather the evidence (release dates, pricing pages, feature lists, docs), state the evidence next to each score, and flag any score it could not verify.

Options to evaluate: each candidate tool or platform, plus the build option (the owner's own code or script). A self-hosted open source tool is a candidate like any other. A hosted (cloud) version and a self-hosted version of the same tool are separate candidates and are scored separately.

## Step 0: Declare the context first

Before looking at any tool, write down all five of these and do not edit them after seeing the candidates. If any is missing, stop and ask the owner.

1. Must-have list for the job. Separate the list into must-haves now, deferred must-haves (required later, not today), and nice-to-haves. Deferred must-haves do not fail the gate, but an option that would be painful to extend to them loses a point on Fit. Nice-to-haves do not affect Fit.
2. Target environment: production, or a lower one (dev, test cluster). Pre-release software (an unstable beta or alpha) may be considered only for a lower environment, and only because it was declared up front. In production, an unstable beta or alpha fails the gate. The declared environment goes in the decision record so it cannot quietly drift upward later.
3. Business stage: pre-revenue, break-even or steady, or strong revenue. This sets the stage modifier on the cost score (see Monetary cost).
4. Expected growth: the volume or user count the owner expects to reach, for example ten times the current level. This is the yardstick for the scaling modifier on Fit.
5. Stack summary: what already runs, which deployment and operating models are in use, and which policies or guardrails constrain new tools. It is drafted from the repo docs, confirmed by the owner, and locked with the other items. The Integration alignment modifier and the policy penalty are judged against it.

## Step 1: Hard gates (pass or fail)

An option that fails any gate is out, regardless of score.

- Every must-have now is achievable (otherwise Fit would be 1).
- Security veto: if the final Security score (see below) is zero or less, the option is vetoed.
- Environment match: pre-release software is out of production.

## Step 2: Score each factor from 1 to 5

Higher is always better for the owner (easier, cheaper, safer, lighter). Scores are clamped to the range 1 to 5 after modifiers, except Security, which can reach zero or below to trigger the veto.

### Fit
- 5: every must-have is met out of the box.
- 4: every must-have is met, but one needs a small configuration workaround.
- 3: one must-have needs a plugin or custom glue code.
- 2: two or more must-haves need custom work.
- 1: a must-have cannot be done.
- Note: use the pricing tier that actually meets the must-haves, not the free tier if a must-have is paywalled.
- Deferred must-haves: minus one if the option would be painful to extend to them later.
- Scaling modifier (plus or minus one), judged against the expected growth declared in Step 0: plus one if it scales well past that growth on the same setup. Zero if it holds but needs a tier change or some configuration (for example moving from a free tier to a paid plan). Minus one if the owner would outgrow it and have to migrate. A minus one can be softened to zero if the option sits behind an interface the owner controls, so that outgrowing it is a cheap swap. State the interface explicitly if relying on this.

### Unused baggage
- Count the features that would actually be used against everything the tool offers, and score by percentage used.
- 5: 90% or more used. 4: 70 to 90%. 3: 50 to 70%. 2: 30 to 50%. 1: under 30%.
- Keep it simple: count features, do not try to weigh each one. For the build option, score 5.

### Install effort
- 5: under two hours.
- 4: about a day.
- 3: a few days.
- 2: a week or more.
- 1: needs special infrastructure or expertise the owner does not have.

### Integration effort
- 5: works with zero changes to the existing setup, just deploy it.
- 4: a small config change in one place (for example one config entry or one policy exception).
- 3: changes in two or three places, or a small adapter, under a day of work.
- 2: changes across several services, or glue code that takes a few days.
- 1: forces a change to how something existing works (auth model, deployment flow).
- Automatic minus one if it needs credentials or network access that breaks an existing policy or guardrail named in the stack summary.
- Alignment modifier (plus or minus one): plus one if it follows a deployment, config or operating model the stack summary lists as already in use, or it reuses a tool already running. Minus one if it brings its own separate model (its own UI-driven config, query language, or auth). Zero if neutral.

### Maintenance effort
- Hours per month for upgrades, patching, and babysitting, including breaking upgrades averaged out. CVE frequency is not scored separately because patching is assumed to be mostly a version bump in the declared stack. If the stack summary says otherwise, state it and adjust the hours.
- 5: under 1 hour per month.
- 4: 1 to 2 hours.
- 3: 2 to 4 hours.
- 2: 4 to 8 hours.
- 1: over 8 hours.
- Ownership-risk modifier (plus or minus one):
  - Minus one if the code or config is the owner's alone and sits in a sensitive area such as secrets or auth, because nobody reviews it.
  - Zero if it is the owner's alone but low stakes.
  - Plus one if a community or vendor shares the load, but only if the project passes the staleness check (release or meaningful commit within the last year). If it fails, the bonus falls back to zero.
  - If the project is more than two years stale, the modifier is minus one, because the owner would inherit an abandoned codebase.
- Maturity modifier (zero or minus one): zero for a stable release or a stable beta. Minus one for an unstable beta. Unstable means breaking changes shipped in the last six months, or pricing and features still moving. There is no special alpha rule: an alpha scores itself down through this modifier and the Security score, and it is already barred from production by the environment gate.

### Dependency count
- Count every new product that would have to be deployed, upgraded, or monitored separately. A sync layer plus a store behind it counts as two.
- 5: zero new products (reuses something already run). 4: one. 3: two. 2: three. 1: four or more.
- Modifier (plus or minus one): plus one if the dependency is stateless and easy to swap out, minus one if it holds state that must be backed up or has to run highly available.

### Lock-in and exit cost
- 5: data and config are in open formats, switching takes under a day, and it sits behind an interface the owner controls.
- 3: switching takes a few days to a week with manageable data migration.
- 1: proprietary data format or API with no practical export, switching takes weeks or more.
- Use 2 and 4 for in-between cases.
- Lock-in asks how hard it is to leave. The scaling modifier on Fit asks whether the option will still fit after growth. They are separate.

### Monetary cost
- Dollars per month at the owner's current scale, for the tier that meets the must-haves.
- 5: free. 4: up to $10. 3: up to $50. 2: up to $200. 1: over $200.
- Free self-hosted still carries its effort in the other factors, so do not double count it here.
- Stage modifier, set once per evaluation from the declared business stage: minus one when pre-revenue (every dollar hurts), zero at break-even or steady, plus one when revenue is strong enough that paying for convenience is fine. It applies to the cost score only. It does not touch the effort scores, because hosted options already score better on install and maintenance and a second nudge would double count.

### Time to value
- How long until it is working. For the build option, use the build estimate.
- 5: under a day. 4: about a week. 3: two to three weeks. 2: a month or two. 1: longer.

### Security
- Start at 5. Subtract one for each that applies: it holds or touches secrets, it exposes a new network surface, it needs elevated cluster permissions.
- Staleness modifier, based on the last release or meaningful commit: plus one if within six months, zero if within a year, minus one if between one and two years, minus two if over two years.
- The build option is the owner's own code, so skip staleness, but still apply the three subtractions.
- If the final number is zero or less, the option is vetoed. Do not clamp this one before checking.

### Core-ness (decides whether to build at all, not scored per tool)
- Ask: is this what makes the product distinctive, and would a customer notice or care if it were built differently? If not core, lean buy or adopt. If core, lean build.
- Use this to frame the decision. It is not added into the weighted total.

## Step 3: Weights (starting weights, expect to tune)

Weights say how much each factor matters. Scale of 1 to 3.

- Fit: 2
- Unused baggage: 1
- Install effort: 1
- Integration effort: 1
- Maintenance effort: 3
- Dependency count: 2
- Lock-in and exit cost: 1
- Monetary cost: 1
- Time to value: 2
- Security: 3

Total weight is 17, so the maximum weighted score is 85.

## Step 4: Calculate

1. Multiply each factor score by its weight.
2. Add them up.
3. Divide by 85 to get a percentage.

Higher percentage means that option is better for the owner. Compare options against each other, and also read the percentage:

- Under 40%: weak option.
- 40 to 60%: genuinely mixed. Write a short decision memo before choosing.
- Over 60%: strong option.

The winner is the highest-scoring option that passed the hard gates. If the top two are within about 10 points, say so and treat it as a judgment call. When options are that close, prefer the simplest one that sits behind an interface the owner controls, and plan to mature into the hosted option later (see Staged decisions).

## Step 5: Record the analysis

Write down, in the analysis record (the agent writes it as final.md plus one file per option; the owner makes the decision):

- The must-have list (now, deferred, nice-to-have), the declared environment, business stage, and expected growth, each option's scores with the evidence behind them, and the result.
- The conditions that would make the owner revisit the decision (for example the number of secrets passing a threshold, a new requirement like audit trails, the business stage changing, or volume nearing a free-tier ceiling).
- An exit note: how to switch away from the chosen option.
- Wrap any adopted vendor behind an interface the owner controls.

## Staged decisions

Some decisions are not final, they are a path. Build or adopt the simplest option now, behind an interface the owner controls, and re-run the matrix when the business stage changes (for example once revenue arrives) or volume grows. The stage modifier is what makes the same matrix give a different answer later. The scaling modifier is what flags, up front, that an option will need to be replaced, so the swap is planned instead of forced.

## Quick version (small decisions)

For small choices, skip the full matrix: write the must-haves, declare the environment, run the security veto, then score only Fit, Maintenance effort, Dependency count, Time to value, and Security with their normal weights. Compare the percentages of those five.

## Worked examples

See `docs/examples/`. They illustrate the method on two small decisions and were scored before the stage, maturity and scaling modifiers were final.

## Tuning notes

- The weights above are version one. After the first few real uses, compare where the matrix steered the decision against how it felt afterward, and adjust the weights.
- Claude Code should never silently change a scale or weight. Propose changes and record them with a date.
- Gaps found so far and now covered: no sense of business stage (stage modifier), no maturity signal (maturity modifier), no environment declaration (Step 0), no handling of deferred requirements (Step 0), no sense of growth headroom (scaling modifier on Fit and expected growth in Step 0).
- v1.3 (2026-11-24): wording generalized so the matrix carries no project-specific stack names. Stack facts come from the confirmed stack summary (new Step 0 item 5). No scale or weight changed.
