# <Candidate name>

- Type: <hosted | self-hosted | build | library | other>
- Prerelease status: <none | stable_beta | unstable_beta | alpha>
- Researched: <YYYY-MM-DD>
- Gates: must-haves <pass|fail>, security veto <pass|fail>, environment <pass|fail>
- Weighted score: <N>/<max> (<pct>%), <weak|mixed|strong>

## Scoring

Every row names the matrix condition that produced the base score and the facts that satisfy it, so a reader can check and refute it. Security shows its pre-clamp value in Final.

| Factor | Base | Modifiers | Final | Why (matrix condition met) | Evidence (source, retrieved) | Status |
|---|---|---|---|---|---|---|
| Fit | <1-5> | <label +/-N, or none> | <1-5> | <condition and facts> | <URL, YYYY-MM-DD> | <verified / unverified / override> |
| Unused baggage | <1-5> | <none> | <1-5> | <features used / offered = pct> | <URL, date> | <status> |
| Install effort | <1-5> | <none> | <1-5> | <time estimate and basis> | <URL, date> | <status> |
| Integration effort | <1-5> | <label +/-N> | <1-5> | <places changed> | <URL, date> | <status> |
| Maintenance effort | <1-5> | <ownership, maturity> | <1-5> | <hours per month and basis> | <URL, date> | <status> |
| Dependency count | <1-5> | <stateless/stateful> | <1-5> | <products added> | <URL, date> | <status> |
| Lock-in and exit cost | <1-5> | <none> | <1-5> | <formats, switch time> | <URL, date> | <status> |
| Monetary cost | <1-5> | <stage +/-1> | <1-5> | <dollars per month, tier> | <URL, date> | <status> |
| Time to value | <1-5> | <none> | <1-5> | <time estimate> | <URL, date> | <status> |
| Security | <1-5> | <each subtraction, staleness> | <value, may be 0 or less> | <secrets, network surface, permissions, last release> | <URL, date> | <status> |

Weighted subtotal: <N>/<max>.

## Could not verify

- <fact, and where it was looked for, or "none">

## Owner overrides

- <factor: original score -> new score, owner's reason, or "none">
