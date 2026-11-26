import json
import os
import pathlib
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
  if [ -f README.md ]; then echo README=yes; else echo README=no; fi
} >> "$FAKE_LOG"
case "$*" in
  *"/build-vs-buy:scorer"*) echo '{"result": "ok", "total_cost_usd": 0.01}' ;;
  *)
    mkdir -p docs/analysis/bvb-x-20261126
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
        self.env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                        FAKE_LOG=str(self.log),
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
                     out + ["--arm", "both"], out + ["--bogus"]):
            proc = subprocess.run(["bash", str(RUN_SH), *args], capture_output=True, text=True, env=self.env)
            self.assertEqual(proc.returncode, 2, args)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
