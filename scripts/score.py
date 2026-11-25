#!/usr/bin/env python3
"""Deterministic math for the build-vs-buy matrix (matrix.md v1.3).

Usage: score.py [input.json]   (reads stdin when no path is given)
Writes JSON to stdout. Exits 2 with a message on stderr for invalid input.
"""
import json
import sys

WEIGHTS = {
    "fit": 2,
    "unused_baggage": 1,
    "install": 1,
    "integration": 1,
    "maintenance": 3,
    "dependencies": 2,
    "lock_in": 1,
    "cost": 1,
    "time_to_value": 2,
    "security": 3,
}
QUICK_FACTORS = ("fit", "maintenance", "dependencies", "time_to_value", "security")
ENVIRONMENTS = ("production", "lower")
PRERELEASE = ("none", "stable_beta", "unstable_beta", "alpha")
BLOCKED_IN_PRODUCTION = ("unstable_beta", "alpha")
CLOSE_CALL_POINTS = 10.0


def _clamp(value):
    return max(1, min(5, value))


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _factor_names(mode):
    if mode == "full":
        return tuple(WEIGHTS)
    if mode == "quick":
        return QUICK_FACTORS
    raise ValueError(f"mode must be 'full' or 'quick', got {mode!r}")


def _band(percentage):
    if percentage < 40:
        return "weak"
    if percentage <= 60:
        return "mixed"
    return "strong"


def _score_factor(option_name, factor, spec):
    if not isinstance(spec, dict):
        raise ValueError(f"{option_name}.{factor}: must be an object")
    base = spec.get("base")
    if not _is_int(base) or not 1 <= base <= 5:
        raise ValueError(f"{option_name}.{factor}: base must be an integer 1-5, got {base!r}")
    mods = spec.get("modifiers", [])
    if not isinstance(mods, list):
        raise ValueError(f"{option_name}.{factor}: modifiers must be a list")
    delta_total = 0
    for mod in mods:
        delta = mod.get("delta") if isinstance(mod, dict) else None
        if not _is_int(delta):
            raise ValueError(f"{option_name}.{factor}: modifier delta must be an integer, got {delta!r}")
        delta_total += delta
    raw = base + delta_total
    return base, delta_total, raw, _clamp(raw)


def _score_option(option, environment, names, max_total):
    if not isinstance(option, dict):
        raise ValueError("every option needs a name")
    name = option.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"every option needs a non-empty string name, got {name!r}")
    if not isinstance(option.get("must_haves_met"), bool):
        raise ValueError(f"{name}: must_haves_met must be true or false")
    prerelease = option.get("prerelease", "none")
    if prerelease not in PRERELEASE:
        raise ValueError(f"{name}: prerelease must be one of {PRERELEASE}, got {prerelease!r}")
    factors_in = option.get("factors", {})
    if not isinstance(factors_in, dict):
        raise ValueError(f"{name}: factors must be an object")
    missing = [n for n in names if n not in factors_in]
    if missing:
        raise ValueError(f"{name}: missing factors {missing}")

    factors_out = {}
    total = 0
    security_raw = None
    for factor in names:
        base, delta, raw, final = _score_factor(name, factor, factors_in[factor])
        weighted = final * WEIGHTS[factor]
        total += weighted
        factors_out[factor] = {
            "base": base,
            "modifier_total": delta,
            "raw": raw,
            "final": final,
            "weight": WEIGHTS[factor],
            "weighted": weighted,
        }
        if factor == "security":
            security_raw = raw

    gates = {
        "must_haves": "pass" if option["must_haves_met"] else "fail",
        "security": "pass" if security_raw > 0 else "fail",
        "environment": "fail"
        if environment == "production" and prerelease in BLOCKED_IN_PRODUCTION
        else "pass",
    }
    percentage = total / max_total * 100
    return {
        "name": name,
        "factors": factors_out,
        "security_raw": security_raw,
        "weighted_total": total,
        "percentage": round(percentage, 1),
        "band": _band(percentage),
        "gates": gates,
        "passed": all(v == "pass" for v in gates.values()),
    }


def evaluate(data):
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    mode = data.get("mode", "full")
    environment = data.get("environment")
    if environment not in ENVIRONMENTS:
        raise ValueError(f"environment must be one of {ENVIRONMENTS}, got {environment!r}")
    names = _factor_names(mode)
    options = data.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError("options must be a non-empty list")
    names_seen = [o["name"] for o in options if isinstance(o, dict) and isinstance(o.get("name"), str)]
    duplicates = sorted({n for n in names_seen if names_seen.count(n) > 1})
    if duplicates:
        raise ValueError(f"option names must be unique, duplicated: {duplicates}")
    max_total = 5 * sum(WEIGHTS[n] for n in names)

    results = [_score_option(o, environment, names, max_total) for o in options]
    passed = sorted((r for r in results if r["passed"]),
                    key=lambda r: (-r["weighted_total"], r["name"]))
    gap = None
    close = False
    if len(passed) >= 2:
        gap = round((passed[0]["weighted_total"] - passed[1]["weighted_total"]) / max_total * 100, 1)
        close = gap <= CLOSE_CALL_POINTS
    return {
        "mode": mode,
        "environment": environment,
        "max_total": max_total,
        "options": results,
        "ranking": [r["name"] for r in passed],
        "top_two_gap": gap,
        "close_call": close,
    }


def main(argv):
    try:
        if len(argv) > 1:
            with open(argv[1], encoding="utf-8") as handle:
                raw = handle.read()
        else:
            raw = sys.stdin.read()
        result = evaluate(json.loads(raw))
    except (ValueError, OSError) as exc:
        print(f"score.py: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
