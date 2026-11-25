import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import score  # noqa: E402

FULL = list(score.WEIGHTS)


def option(name, scores, mods=None, **extra):
    mods = mods or {}
    factors = {
        f: {
            "base": s,
            "modifiers": [{"label": label, "delta": d} for label, d in mods.get(f, [])],
        }
        for f, s in scores.items()
    }
    opt = {"name": name, "must_haves_met": True, "prerelease": "none", "factors": factors}
    opt.update(extra)
    return opt


def uniform(value, **overrides):
    scores = {f: value for f in FULL}
    scores.update(overrides)
    return scores


VAULT = option(
    "Vault",
    {"fit": 5, "unused_baggage": 1, "install": 2, "integration": 3, "maintenance": 2,
     "dependencies": 3, "lock_in": 3, "cost": 5, "time_to_value": 2, "security": 5},
    {"maintenance": [("community", 1)],
     "security": [("secrets", -1), ("elevated", -1), ("active releases", 1)]},
)
SCRIPT = option(
    "Script",
    {"fit": 4, "unused_baggage": 5, "install": 5, "integration": 4, "maintenance": 4,
     "dependencies": 5, "lock_in": 5, "cost": 5, "time_to_value": 4, "security": 5},
    {"integration": [("alignment", 1)],
     "maintenance": [("ownership risk", -1)],
     "security": [("secrets", -1)]},
)


def run(options, environment="production", mode="full"):
    return score.evaluate({"mode": mode, "environment": environment, "options": options})


def by_name(result, name):
    return next(o for o in result["options"] if o["name"] == name)


class WorkedExamples(unittest.TestCase):
    def test_vault_matches_matrix_example(self):
        result = run([VAULT])
        vault = by_name(result, "Vault")
        self.assertEqual(vault["weighted_total"], 55)
        self.assertEqual(result["max_total"], 85)
        self.assertAlmostEqual(vault["percentage"], 64.7, places=1)
        self.assertEqual(vault["band"], "strong")

    def test_script_matches_matrix_example(self):
        script = by_name(run([SCRIPT]), "Script")
        self.assertEqual(script["weighted_total"], 72)
        self.assertAlmostEqual(script["percentage"], 84.7, places=1)

    def test_ranking_puts_script_first(self):
        result = run([VAULT, SCRIPT])
        self.assertEqual(result["ranking"], ["Script", "Vault"])


class Clamping(unittest.TestCase):
    def test_clamps_high_and_low(self):
        scores = uniform(3)
        opt = option("A", scores, {"fit": [("up", 2)], "install": [("down", -5)]})
        a = by_name(run([opt]), "A")
        self.assertEqual(a["factors"]["fit"]["raw"], 5)
        self.assertEqual(a["factors"]["install"]["raw"], -2)
        self.assertEqual(a["factors"]["fit"]["final"], 5)
        self.assertEqual(a["factors"]["install"]["final"], 1)

    def test_raw_keeps_unclamped_value(self):
        opt = option("A", uniform(3), {"fit": [("up", 4)]})
        self.assertEqual(by_name(run([opt]), "A")["factors"]["fit"]["raw"], 7)


class Gates(unittest.TestCase):
    def test_security_veto_at_zero(self):
        opt = option("V", uniform(4, security=5),
                     {"security": [("a", -1), ("b", -1), ("c", -1), ("d", -2)]})
        result = run([opt])
        v = by_name(result, "V")
        self.assertEqual(v["security_raw"], 0)
        self.assertEqual(v["gates"]["security"], "fail")
        self.assertFalse(v["passed"])
        self.assertEqual(v["factors"]["security"]["final"], 1)
        self.assertEqual(result["ranking"], [])

    def test_security_one_passes(self):
        opt = option("V", uniform(4, security=5),
                     {"security": [("a", -1), ("b", -1), ("c", -1), ("d", -1)]})
        self.assertTrue(by_name(run([opt]), "V")["passed"])

    def test_must_haves_gate(self):
        opt = option("M", uniform(4), must_haves_met=False)
        m = by_name(run([opt]), "M")
        self.assertEqual(m["gates"]["must_haves"], "fail")
        self.assertFalse(m["passed"])

    def test_alpha_blocked_in_production_only(self):
        alpha = option("Al", uniform(4), prerelease="alpha")
        self.assertFalse(by_name(run([alpha], "production"), "Al")["passed"])
        self.assertTrue(by_name(run([alpha], "lower"), "Al")["passed"])

    def test_unstable_beta_blocked_in_production(self):
        beta = option("B", uniform(4), prerelease="unstable_beta")
        self.assertEqual(by_name(run([beta], "production"), "B")["gates"]["environment"], "fail")

    def test_stable_beta_allowed_in_production(self):
        beta = option("B", uniform(4), prerelease="stable_beta")
        self.assertTrue(by_name(run([beta], "production"), "B")["passed"])


class CloseCall(unittest.TestCase):
    def test_close_when_gap_within_ten_points(self):
        a = option("A", uniform(4))
        b = option("B", uniform(4, maintenance=3))
        result = run([a, b])
        self.assertTrue(result["close_call"])
        self.assertAlmostEqual(result["top_two_gap"], 3.5, places=1)

    def test_not_close_when_gap_large(self):
        result = run([option("A", uniform(4)), option("B", uniform(3))])
        self.assertFalse(result["close_call"])
        self.assertAlmostEqual(result["top_two_gap"], 20.0, places=1)

    def test_single_passer_has_no_gap(self):
        result = run([option("A", uniform(4)), option("B", uniform(4), must_haves_met=False)])
        self.assertFalse(result["close_call"])
        self.assertIsNone(result["top_two_gap"])


class Bands(unittest.TestCase):
    def test_band_edges(self):
        self.assertEqual(score._band(39.9), "weak")
        self.assertEqual(score._band(40.0), "mixed")
        self.assertEqual(score._band(60.0), "mixed")
        self.assertEqual(score._band(60.1), "strong")


class QuickMode(unittest.TestCase):
    QUICK = ("fit", "maintenance", "dependencies", "time_to_value", "security")

    def test_quick_needs_five_factors_and_max_is_sixty(self):
        opt = option("Q", {f: 5 for f in self.QUICK})
        result = run([opt], mode="quick")
        q = by_name(result, "Q")
        self.assertEqual(result["max_total"], 60)
        self.assertEqual(q["weighted_total"], 60)
        self.assertEqual(q["percentage"], 100.0)

    def test_full_mode_rejects_missing_factor(self):
        opt = option("Q", {f: 5 for f in self.QUICK})
        with self.assertRaises(ValueError):
            run([opt], mode="full")


class Validation(unittest.TestCase):
    def test_bad_base(self):
        with self.assertRaises(ValueError):
            run([option("X", uniform(6))])

    def test_bad_environment(self):
        with self.assertRaises(ValueError):
            run([option("X", uniform(4))], environment="staging")

    def test_bad_prerelease(self):
        with self.assertRaises(ValueError):
            run([option("X", uniform(4), prerelease="rc")])

    def test_no_options(self):
        with self.assertRaises(ValueError):
            run([])

    def test_non_integer_delta(self):
        opt = option("X", uniform(4))
        opt["factors"]["fit"]["modifiers"] = [{"label": "x", "delta": 0.5}]
        with self.assertRaises(ValueError):
            run([opt])


class Cli(unittest.TestCase):
    def call(self, payload):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "score.py")],
            input=payload, capture_output=True, text=True,
        )

    def test_stdin_roundtrip(self):
        payload = json.dumps({"environment": "production", "options": [VAULT]})
        proc = self.call(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["options"][0]["weighted_total"], 55)

    def test_invalid_json_exits_2(self):
        proc = self.call("{not json")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("score.py:", proc.stderr)


class MalformedShapes(unittest.TestCase):
    def _with(self, mutate):
        opt = option("X", uniform(4))
        mutate(opt)
        return opt

    def test_factors_null(self):
        with self.assertRaises(ValueError):
            run([self._with(lambda o: o.__setitem__("factors", None))])

    def test_factors_list(self):
        with self.assertRaises(ValueError):
            run([self._with(lambda o: o.__setitem__("factors", ["fit"]))])

    def test_modifiers_null(self):
        with self.assertRaises(ValueError):
            run([self._with(lambda o: o["factors"]["fit"].__setitem__("modifiers", None))])

    def test_modifiers_scalar(self):
        with self.assertRaises(ValueError):
            run([self._with(lambda o: o["factors"]["fit"].__setitem__("modifiers", 5))])

    def test_options_scalar(self):
        with self.assertRaises(ValueError):
            score.evaluate({"environment": "production", "options": 5})


class CloseCallBoundary(unittest.TestCase):
    # Integer weighted totals over max 85 can never give a gap of exactly 8.5
    # points (10.0%), so test the largest reachable gap at or under 10 and the
    # smallest reachable gap over 10.
    def test_largest_gap_within_ten_is_close(self):
        # maintenance final 2 (-6 weighted), dependencies final 3 (-2) => diff 8 => 9.4%
        a = option("A", uniform(4))
        b = option("B", uniform(4, maintenance=2, dependencies=3))
        result = run([a, b])
        self.assertEqual(result["top_two_gap"], 9.4)
        self.assertTrue(result["close_call"])

    def test_smallest_gap_over_ten_is_not_close(self):
        # maintenance final 1 (-9 weighted) => diff 9 => 10.6%
        a = option("A", uniform(4))
        b = option("B", uniform(4, maintenance=1))
        result = run([a, b])
        self.assertEqual(result["top_two_gap"], 10.6)
        self.assertFalse(result["close_call"])


class CliInvalidShape(unittest.TestCase):
    def test_parseable_but_empty_options_exits_2(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "score.py")],
            input='{"environment":"production","options":[]}',
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("score.py:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
