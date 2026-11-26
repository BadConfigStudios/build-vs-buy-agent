import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_SH = ROOT / "tools" / "drift" / "run.sh"

FAKE_CLAUDE = """#!/usr/bin/env bash
# Test double for the claude CLI: logs its arguments and the model overrides it sees.
{
  printf 'ARGS:'
  for a in "$@"; do printf ' [%s]' "$a"; done
  printf '\\nENV_SUBAGENT_MODEL=%s FORCE=%s PWD=%s\\n' "${CLAUDE_CODE_SUBAGENT_MODEL-unset}" \\
    "${CLAUDE_CODE_SUBAGENT_MODEL_FORCE-unset}" "$PWD"
  printf 'ENV_ANTHROPIC=%s/%s/%s/%s\\n' "${ANTHROPIC_MODEL-unset}" "${ANTHROPIC_DEFAULT_SONNET_MODEL-unset}" \\
    "${ANTHROPIC_DEFAULT_OPUS_MODEL-unset}" "${ANTHROPIC_DEFAULT_HAIKU_MODEL-unset}"
  echo "PHYS=$(pwd -P)"
  if [ -f README.md ]; then echo README=yes; else echo README=no; fi
} >> "$FAKE_LOG"
if [ -n "${FAKE_FAIL-}" ]; then echo partial; exit 1; fi
case "$*" in
  *"/build-vs-buy:scorer"*) echo '{"result": "ok", "total_cost_usd": 0.01}' ;;
  *)
    [ -n "${FAKE_NOWRITE-}" ] && { echo '{"result": "ok"}'; exit 0; }
    mkdir -p docs/analysis/bvb-x-20261126
    [ -n "${FAKE_TWO-}" ] && { mkdir -p docs/analysis/other; : > docs/analysis/other/locked-context.md; }
    printf -- '---\\nmode: full\\n---\\n' > docs/analysis/bvb-x-20261126/locked-context.md
    echo '{"result": "ok", "total_cost_usd": 0.02}' ;;
esac
"""


class RunSh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)
        bin_dir = self.dir / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.log = self.dir / "calls.log"
        # PATH is only the fake dir, a dir with python3, and the system dirs: the real claude is unreachable.
        tools = self.dir / "tools"
        tools.mkdir()
        (tools / "python3").symlink_to(shutil.which("python3"))
        system = os.pathsep.join(["/usr/bin", "/bin"])
        self.assertIsNone(shutil.which("claude", path=f"{tools}{os.pathsep}{system}"))
        self.tmpdir = self.dir / "tmp"
        self.tmpdir.mkdir()
        self.env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{tools}{os.pathsep}{system}",
                        TMPDIR=str(self.tmpdir), FAKE_LOG=str(self.log),
                        ANTHROPIC_MODEL="m", ANTHROPIC_DEFAULT_SONNET_MODEL="m",
                        ANTHROPIC_DEFAULT_OPUS_MODEL="m", ANTHROPIC_DEFAULT_HAIKU_MODEL="m",
                        CLAUDE_CODE_SUBAGENT_MODEL="haiku", CLAUDE_CODE_SUBAGENT_MODEL_FORCE="1")
        self.out = self.dir / "out"

    def run_sh(self, *args):
        return subprocess.run(["bash", str(RUN_SH), "--out", str(self.out), *args],
                              capture_output=True, text=True, env=self.env)

    def calls(self):
        return self.log.read_text(encoding="utf-8").splitlines()

    def n_reports(self):
        return len(list((ROOT / "tools" / "drift" / "fixtures" / "reports").glob("*.md")))

    def test_independent_makes_one_call_per_report_per_run(self):
        proc = self.run_sh("--runs", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = sorted((self.out / "scorer-independent-default").glob("run-*/*.out.json"))
        self.assertEqual(len(files), 2 * self.n_reports())
        self.assertEqual(json.loads(files[0].read_text())["total_cost_usd"], 0.01)

    def test_centralized_shuffles_and_records_order(self):
        proc = self.run_sh("--runs", "3", "--topology", "centralized", "--model", "opus")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        base = self.out / "scorer-centralized-opus"
        orders = [(base / f"run-{k}" / "order.txt").read_text().split() for k in (1, 2, 3)]
        for order in orders:
            self.assertEqual(len(order), self.n_reports())
            self.assertEqual(len(set(order)), self.n_reports())
        self.assertEqual(len(list(base.glob("run-*/all.out.json"))), 3)
        self.assertTrue(any("--model opus" in line for line in self.calls()))

    def test_every_call_is_capped_scoped_and_clean_of_overrides(self):
        self.run_sh("--runs", "1", "--budget", "0.75")
        lines = self.calls()
        arg_lines = [l for l in lines if l.startswith("ARGS:")]
        self.assertTrue(arg_lines)
        for line in arg_lines:
            for needle in ("[--plugin-dir]", "[--output-format] [json]",
                           "[--max-budget-usd] [0.75]", "[--allowedTools]"):
                self.assertIn(needle, line)
            self.assertNotIn("dangerously", line)
        for line in lines:
            if line.startswith("ENV_SUBAGENT_MODEL"):
                self.assertTrue(line.startswith("ENV_SUBAGENT_MODEL=unset FORCE=unset"), line)

    def test_context_mode_collects_locked_context_per_arm(self):
        for arm in ("with-docs", "no-docs"):
            proc = self.run_sh("--mode", "context", "--arm", arm, "--runs", "2")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            for k in (1, 2):
                self.assertTrue((self.out / f"context-{arm}" / f"run-{k}" / "locked-context.md").is_file())
        readme = [l for l in self.calls() if l.startswith("README=")]
        self.assertEqual(readme, ["README=yes"] * 2 + ["README=no"] * 2)

    def test_bad_usage_exits_2(self):
        out = ["--out", str(self.out)]
        for args in ([], out + ["--mode", "nope"], out + ["--runs", "x"], out + ["--topology", "diag"],
                     out + ["--arm", "both"], out + ["--bogus"],
                     out + ["--runs", "0"], out + ["--runs", "31"], out + ["--runs", "-1"],
                     out + ["--budget", "0"], out + ["--budget", "5.01"], out + ["--budget", "abc"],
                     out + ["--budget", "-1"], out + ["--tag", ".."], out + ["--tag", "a/b"],
                     out + ["--model", "x y"], out + ["--runs"], out + ["--tag"]):
            proc = subprocess.run(["bash", str(RUN_SH), *args], capture_output=True, text=True, env=self.env)
            self.assertEqual(proc.returncode, 2, args)
        self.assertFalse(self.log.exists())

    def test_model_env_overrides_are_unset(self):
        self.run_sh("--runs", "1", "--topology", "centralized")
        self.assertIn("ENV_ANTHROPIC=unset/unset/unset/unset", self.calls())

    def test_scorer_runs_from_repo_root(self):
        self.run_sh("--runs", "1", "--topology", "centralized")
        pwds = [l.split("PWD=")[1] for l in self.calls() if "PWD=" in l]
        self.assertEqual([os.path.realpath(p) for p in pwds], [os.path.realpath(ROOT)])

    def test_context_write_is_plain_and_sandbox_is_physical(self):
        self.run_sh("--mode", "context", "--runs", "1")
        text = self.log.read_text(encoding="utf-8")
        self.assertIn("[Write]", text)
        self.assertNotIn("Write(", text)
        pwd = re.search(r"PWD=(\S+)", text).group(1)
        phys = re.search(r"PHYS=(\S+)", text).group(1)
        self.assertEqual(pwd, phys)

    def test_missing_or_duplicate_locked_context_fails_the_run(self):
        for var in ("FAKE_NOWRITE", "FAKE_TWO"):
            env = dict(self.env, **{var: "1"})
            proc = subprocess.run(["bash", str(RUN_SH), "--out", str(self.dir / var), "--mode", "context",
                                   "--runs", "2"], capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("(missing)" if var == "FAKE_NOWRITE" else "(more than one)", proc.stderr)

    def test_refuses_nonempty_output_dir(self):
        self.assertEqual(self.run_sh("--runs", "1").returncode, 0)
        n = len(self.calls())
        proc = self.run_sh("--runs", "1")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not empty", proc.stderr)
        self.assertEqual(len(self.calls()), n)

    def test_refuses_repo_path_with_whitespace(self):
        spaced = self.dir / "a b"
        (spaced / "tools" / "drift").mkdir(parents=True)
        shutil.copy(RUN_SH, spaced / "tools" / "drift" / "run.sh")
        proc = subprocess.run(["bash", str(spaced / "tools" / "drift" / "run.sh"), "--out", str(self.out)],
                              capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("whitespace", proc.stderr)
        self.assertFalse(self.log.exists())

    def test_bounds_accepted_at_the_edges(self):
        proc = self.run_sh("--runs", "1", "--budget", "5.00", "--topology", "centralized")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("estimated max spend 5.00 USD", proc.stderr)

    def test_plugin_dir_and_isolation_flags_on_every_call(self):
        for extra in ([], ["--topology", "centralized"], ["--mode", "context"]):
            self.log.unlink(missing_ok=True)
            self.run_sh("--runs", "1", *extra)
            text = self.log.read_text(encoding="utf-8")
            n = text.count("ARGS:")
            self.assertGreater(n, 0)
            # The context prompt is multi-line, so count flags over the whole log.
            for needle in (f"[--plugin-dir] [{ROOT}]", "[--setting-sources] [project]", "[--strict-mcp-config]"):
                self.assertEqual(text.count(needle), n, needle)

    def test_centralized_shuffle_is_reproducible_and_matches_prompt(self):
        orders = []
        for name in ("a", "b"):
            self.log.unlink(missing_ok=True)
            out = self.dir / name
            proc = subprocess.run(["bash", str(RUN_SH), "--out", str(out), "--runs", "2",
                                   "--topology", "centralized"],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            base = out / "scorer-centralized-default"
            orders.append([(base / f"run-{k}" / "order.txt").read_text() for k in (1, 2)])
            prompts = [l for l in self.calls() if l.startswith("ARGS:")]
            for k, line in enumerate(prompts, start=1):
                in_prompt = [t for t in line.split() if "/reports/" in t and t.rstrip("]").endswith(".md")]
                in_prompt = [t.strip("[]") for t in in_prompt]
                self.assertEqual(in_prompt, orders[-1][k - 1].split())
        self.assertEqual(orders[0], orders[1])

    def test_failing_claude_exits_1_and_leaves_no_result_files(self):
        self.env["FAKE_FAIL"] = "1"
        for extra in ([], ["--topology", "centralized"], ["--mode", "context"]):
            proc = self.run_sh("--runs", "1", *extra)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("failed", proc.stderr)
        self.assertEqual(list(self.out.rglob("*.out.json*")), [])

    def test_sandbox_removed_after_run_and_on_failure(self):
        self.run_sh("--mode", "context", "--runs", "2")
        self.assertEqual(list(self.tmpdir.iterdir()), [])
        self.env["FAKE_FAIL"] = "1"
        self.run_sh("--mode", "context", "--runs", "1")
        self.assertEqual(list(self.tmpdir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
