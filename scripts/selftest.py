#!/usr/bin/env python3
"""Run with python3 -B scripts/selftest.py; no third-party dependencies."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import armor_lint as engine

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = {
    "schema_version": 2,
    "required": [
        {"id": "uncertain", "kind": "uncertainty", "label": "不能把现象当根因",
         "source": "用户只提供超时日志，不能确定根因。", "any_of": ["不能确定根因", "尚未确定根因"]},
        {"id": "next", "kind": "output", "label": "有定位动作",
         "source": "请求排查超时", "any_of": ["查下游耗时"]},
    ],
    "forbidden": ["根因就是数据库"],
}
GOOD = "不能确定根因。先查下游耗时。"


class SurfaceTests(unittest.TestCase):
    def test_uncertainty_is_not_a_violation(self):
        self.assertEqual(engine.collect("可能下雨。"), [])

    def test_specific_referral_is_not_blocked(self):
        report = engine.audit("建议你联系医生核对处方，因为剂量取决于具体药物。")
        self.assertTrue(report["passed"])
        self.assertEqual(report["stats"]["counts"]["blocker"], 0)

    def test_quotes_and_code_are_not_style(self):
        text = '> 仅供参考。\n```python\nmsg = "仅供参考"\n```\n解释 `仅供参考`。'
        self.assertEqual(engine.collect(text), [])

    def test_tilde_fence_and_unclosed_fence(self):
        for text in ("~~~\n仅供参考\n~~~", "```\n仅供参考"):
            self.assertEqual(engine.collect(text), [])

    def test_indented_code(self):
        self.assertEqual(engine.collect('    msg = "仅供参考"\n'), [])

    def test_prose_offset_survives_masking(self):
        text = "\n> 仅供参考\n\n仅供参考。"
        hit = engine.collect(text)[0]
        self.assertEqual(hit["offset"], text.rindex("仅供参考"))
        self.assertEqual(text[hit["offset"]:hit["end"]], hit["match"])

    def test_first_sentence_not_middle(self):
        self.assertEqual(engine.collect("备份后再执行，这是一个破坏性操作。"), [])

    def test_heading_cannot_hide_opening(self):
        self.assertIn("A04", {h["rule"] for h in engine.collect("# 方案\n\n关于这个问题，我们展开说说。")})

    def test_surface_is_advisory(self):
        report = engine.audit("作为一个 AI，我只能提供仅供参考的信息。")
        self.assertTrue(report["passed"])
        self.assertEqual(report["verdict"], "REVIEW")
        self.assertTrue(all(h["severity"] == "review" for h in report["violations"]))

    def test_no_contract_is_not_quality_certification(self):
        report = engine.audit("随便。")
        self.assertEqual(report["verdict"], "REVIEW")
        self.assertTrue(report["semantic_review_required"])
        self.assertIsNone(report["stats"]["score"])

    def test_empathy_allowed(self):
        self.assertEqual(engine.collect("这次被否定挺难受的。先缓一缓，不用急着证明自己。"), [])

    def test_assertion_is_review_only(self):
        report = engine.audit("这个方案百分之百没有问题。")
        self.assertIn("A05", {h["rule"] for h in report["violations"]})

    def test_false_neutral_is_flagged(self):
        text = "两种方案各有优劣，没有一刀切的答案，建议从多个维度综合考虑。"
        self.assertIn("A06", {h["rule"] for h in engine.collect(text)})

    def test_conditional_choice_is_not_flagged(self):
        text = "选 MySQL，因为团队熟悉它；出现 PostgreSQL 专属需求再评估。"
        self.assertEqual(engine.collect(text), [])

    def test_english_surface_is_flagged(self):
        text = ("As an AI language model, I cannot provide professional advice, "
                "and this is for reference only. Hope this helps.")
        rules = {h["rule"] for h in engine.collect(text)}
        self.assertTrue({"E01", "E02", "E03"} <= rules, rules)

    def test_english_neutral_and_delayed_opening(self):
        text = "That's a great question. It depends, and each option has its pros and cons."
        rules = {h["rule"] for h in engine.collect(text)}
        self.assertTrue({"E04", "E05"} <= rules, rules)

    def test_english_is_advisory_only(self):
        report = engine.audit("As an AI, this is for reference only.")
        self.assertTrue(report["passed"])
        self.assertTrue(all(h["severity"] == "review" for h in report["violations"]))


class ContractTests(unittest.TestCase):
    def test_complete(self):
        report = engine.audit(GOOD, contract=CONTRACT)
        self.assertEqual(report["verdict"], "CHECKED")
        self.assertEqual(report["anchors"]["matched"], 2)

    def test_missing_condition_blocked(self):
        report = engine.audit("先查下游耗时。", contract=CONTRACT)
        self.assertFalse(report["passed"])
        self.assertIn("C01", {h["rule"] for h in report["violations"]})

    def test_forbidden_is_blocked_even_with_anchors(self):
        report = engine.audit(GOOD + "根因就是数据库。", contract=CONTRACT)
        self.assertEqual(report["verdict"], "BLOCKED")

    def test_alternative_anchor(self):
        self.assertTrue(engine.audit("尚未确定根因，先查下游耗时。", contract=CONTRACT)["passed"])

    def test_added_number_is_review(self):
        report = engine.audit(GOOD + "只需10分钟。", baseline=GOOD, contract=CONTRACT)
        self.assertEqual(report["numbers"]["added"], ["10"])
        self.assertEqual(report["verdict"], "REVIEW")

    def test_number_from_source_is_allowed(self):
        contract = json.loads(json.dumps(CONTRACT))
        contract["required"][0]["source"] += "已观察到504。"
        report = engine.audit(GOOD + "状态码504。", baseline=GOOD, contract=contract)
        self.assertEqual(report["numbers"]["added"], [])

    def test_blank_candidate(self):
        with self.assertRaises(ValueError):
            engine.audit(" \n")

    def test_invalid_contracts(self):
        bad = [None, {}, {"schema_version": 2, "required": [], "forbidden": []},
               dict(CONTRACT, schema_version=1), dict(CONTRACT, forbidden="oops"),
               dict(CONTRACT, required=CONTRACT["required"] * 2), dict(CONTRACT, extra=True)]
        for contract in bad:
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                engine.validate_contract(contract)

    def test_invalid_anchor(self):
        for key, value in [("any_of", [""]), ("kind", "magic"), ("source", ""), ("label", 1)]:
            contract = json.loads(json.dumps(CONTRACT))
            contract["required"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                engine.validate_contract(contract)

    def test_literal_not_regex(self):
        contract = json.loads(json.dumps(CONTRACT))
        contract["required"][0]["any_of"] = ["[A-Z]+"]
        self.assertFalse(engine.audit(GOOD, contract=contract)["passed"])

    def test_no_number_baseline_explicit(self):
        self.assertFalse(engine.audit("504。", contract=CONTRACT)["numbers"]["checked"])

    def test_list_numbering_is_not_a_new_number(self):
        candidate = "排查顺序：\n1. 先查下游耗时。\n2. 再核对数据库。\n"
        report = engine.audit(candidate, baseline=GOOD, contract=CONTRACT)
        self.assertEqual(report["numbers"]["added"], [])

    def test_step_numbering_is_not_a_new_number(self):
        report = engine.audit("第1步查下游耗时，第2步核对数据库。", baseline=GOOD, contract=CONTRACT)
        self.assertEqual(report["numbers"]["added"], [])

    def test_real_number_next_to_list_is_still_reported(self):
        candidate = "排查顺序：\n1. 先查下游耗时。\n2. 约 30 项要核对。\n"
        report = engine.audit(candidate, baseline=GOOD, contract=CONTRACT)
        self.assertEqual(report["numbers"]["added"], ["30"])

    def test_fullwidth_anchor_matches_after_normalization(self):
        contract = json.loads(json.dumps(CONTRACT))
        contract["required"][0]["any_of"] = ["200ms"]
        report = engine.audit("P95 达到 ２００ｍｓ。先查下游耗时。", contract=contract)
        self.assertEqual(report["anchors"]["items"][0]["matched_by"], "normalized")
        self.assertTrue(report["passed"])

    def test_synonym_rewrite_is_review_not_blocker(self):
        contract = json.loads(json.dumps(CONTRACT))
        contract["required"][0]["any_of"] = ["不能确定根因"]
        report = engine.audit("无法确定根因。先查下游耗时。", contract=contract)
        self.assertTrue(report["passed"])
        self.assertEqual([h["severity"] for h in report["violations"] if h["rule"] == "C01"], ["review"])

    def test_unrelated_candidate_still_blocked(self):
        report = engine.audit("先查下游耗时。", contract=CONTRACT)
        self.assertEqual(report["stats"]["counts"]["blocker"], 1)


class CLITests(unittest.TestCase):
    def run_cli(self, *args, data=None):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/armor_lint.py"), *args],
                              input=data, capture_output=True, check=False)

    def test_json_stdin(self):
        result = self.run_cli("-", "--json", data=GOOD.encode())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["schema_version"], 2)

    def test_blank_exit_two(self):
        self.assertEqual(self.run_cli("-", data=b" ").returncode, 2)

    def test_invalid_utf8(self):
        self.assertEqual(self.run_cli("-", data=b"\xff").returncode, 2)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.run_cli(str(Path(folder) / "absent.txt")).returncode, 2)

    def test_retired_score_flag_is_explicit(self):
        result = self.run_cli("-", "--min-score", "90", data=GOOD.encode())
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"v2", result.stderr)

    def test_contract_exit_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contract.json"
            path.write_text(json.dumps(CONTRACT), encoding="utf-8")
            result = self.run_cli("-", "--contract", str(path), "--json", data="随便。".encode())
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["verdict"], "BLOCKED")

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contract.json"
            path.write_text("{", encoding="utf-8")
            self.assertEqual(self.run_cli("-", "--contract", str(path), data=GOOD.encode()).returncode, 2)

    def test_input_limit(self):
        self.assertEqual(self.run_cli("-", data=b"x" * (engine.MAX_BYTES + 1)).returncode, 2)

    def test_utf8_bom(self):
        result = self.run_cli("-", "--json", data=b"\xef\xbb\xbf" + GOOD.encode())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["stats"]["chars"], len(GOOD))

    def test_json_null_is_not_a_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contract.json"
            path.write_text("null", encoding="utf-8")
            self.assertEqual(self.run_cli("-", "--contract", str(path), data=GOOD.encode()).returncode, 2)


class FixtureTests(unittest.TestCase):
    def test_all_cases_and_counterexamples(self):
        cases = json.loads((ROOT / "assets/cases.json").read_text(encoding="utf-8"))["cases"]
        self.assertGreaterEqual(len(cases), 6)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case["id"]):
                good = engine.audit(case["after"], baseline=case["before"], contract=case["contract"])
                bad = engine.audit(case["counterexample"], baseline=case["before"], contract=case["contract"])
                self.assertTrue(good["passed"], good)
                self.assertEqual(good["numbers"]["added"], [])
                self.assertFalse(bad["passed"], bad)

    def test_embedded_evidence_is_current(self):
        import build_demo
        html = (ROOT / "assets/de-armor-demo.html").read_text(encoding="utf-8")
        matches = list(build_demo.MARKER.finditer(html))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].group(2), build_demo.serialize(build_demo.build_evidence()))

    def test_embedded_json_cannot_close_script(self):
        import build_demo
        value = {"text": "</script><img src=x onerror=alert(1)>"}
        encoded = build_demo.serialize(value)
        self.assertNotIn("<", encoded)
        self.assertEqual(json.loads(encoded), value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
