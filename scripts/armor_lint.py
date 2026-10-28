#!/usr/bin/env python3
"""Offline response audit v2. Exit 0: no blockers; 1: contract blocked; 2: invalid input."""

import argparse
import json
from pathlib import Path
import re
import sys

VERSION = "2.1.0"
MAX_BYTES = 1_000_000
KINDS = {"fact", "condition", "uncertainty", "boundary", "output"}
RULES = [
    ("A01", "身份替代回答", r"作为(?:一[个名位])?\s*(?:AI|人工智能|语言模型|大模型)",
     "确认身份说明是否与当前任务有关；若无关，改为具体能力边界。"),
    ("A02", "通用免责", r"仅供参考|不构成(?:任何)?(?:专业|投资|医疗|法律)?建议|风险自担",
     "检查是否属于用户要求的原文/条款；否则保留具体风险，压缩套话。"),
    ("A03", "社交填充", r"这是个(?:很|非常)?好的问题|希望(?:这些|以上|我的|这个)[^。！？\n]{0,12}对你有帮助|欢迎继续(?:提问|追问)|如果你还想了解更多[^。！？\n]{0,12}继续问",
     "若没有新增信息，删掉；不要删除真正的情绪回应。"),
    ("A04", "答案延后", r"^(?:关于(?:这个|你提到的)问题|为了给你更准确的建议|首先需要说明)",
     "核对开头是否可以直接给答案或真实阻塞原因。"),
    ("A05", "确定性过强", r"百分之百|毫无疑问|绝对不会|肯定没有问题",
     "核对证据与适用条件；有证明的确定判断不必改。"),
    ("A06", "假中立或无差别清单", r"多个维度综合考虑|多维度综合考虑|需要综合考虑|从多个(?:维度|方面)考虑|视情况而定|具体情况具体分析|各有(?:优劣|利弊)|没有一刀切|见仁见智|因(?:情况|项目|团队)而异",
     "若确实取决于条件，写明触发条件并给出首选；若信息已足够，收敛为有条件的选择。"),
    ("E01", "英文身份前置", r"\b(?:as|being)\s+an?\s+(?:ai|artificial intelligence|large language model|language model)\b",
     "英文仅基础模式覆盖：确认身份说明是否与当前任务有关；未命中不代表已审查。"),
    ("E02", "英文通用免责", r"for reference only|at your own risk|not (?:constitute|to be construed as)[^.\n]{0,40}advice|cannot provide (?:professional|legal|medical|financial) advice|please consult a (?:professional|specialist)",
     "英文仅基础模式覆盖：保留具体风险，压缩无信息免责。"),
    ("E03", "英文社交填充", r"(?:great|good) question|hope (?:this|that|it) helps|feel free to (?:ask|reach out)|let me know if you (?:have|need)",
     "英文仅基础模式覆盖：若没有新增信息，删掉；不要删除真正的情绪回应。"),
    ("E04", "英文假中立", r"it (?:really )?depends|each (?:option )?has its (?:pros and cons|trade-?offs)|there are (?:pros and cons|no one-size-fits-all)|multiple factors|case by case",
     "英文仅基础模式覆盖：是否给出有条件的选择与会使选择反转的条件。"),
    ("E05", "英文答案延后", r"^(?:that'?s a (?:great|good) question|before (?:i|we) (?:answer|dive in)|first(?:ly)?,?\s+(?:it'?s important to note|i (?:need|should|must) (?:note|mention|clarify)))",
     "英文仅基础模式覆盖：核对首句能否直接给答案或真实阻塞原因。"),
]
FIRST_SENTENCE_RULES = {"A04", "E05"}
COMPILED = [(rid, label, re.compile(pattern, re.IGNORECASE), fix) for rid, label, pattern, fix in RULES]
NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")
LIST_NUMBER = re.compile(r"(?m)^[ \t]{0,3}(?:[#*>-]{1,6}[ \t]*)?\(?(\d{1,3})\)?[.)、](?=[ \t]|$)")
STEP_NUMBER = re.compile(r"第[ \t]*(\d{1,3})[ \t]*[步条项点章节]")
SYNONYM_THRESHOLD = 0.6
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u00a0"), None)
_FULLWIDTH = {0xFF10 + i: ord("0") + i for i in range(10)}
_FULLWIDTH.update({0xFF21 + i: ord("A") + i for i in range(26)})
_FULLWIDTH.update({0xFF41 + i: ord("a") + i for i in range(26)})
_PUNCTUATION = dict.fromkeys(map(ord, " \t\r\n.,;:!?'\"`~_|/\\-—·、，。；：！？（）()[]{}<>"), " ")


def mask_protected(text):
    chars = list(text)

    def mask(start, end):
        for index in range(start, end):
            if chars[index] not in "\r\n":
                chars[index] = " "

    offset = 0
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            mask(offset, offset + len(line))
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not line[marker.end():].strip():
                fence = None
        elif marker:
            fence = marker.group(1)
            mask(offset, offset + len(line))
        elif re.match(r"^ {0,3}(?:>|#{1,6}\s)", line) or line.startswith(("    ", "\t")):
            mask(offset, offset + len(line))
        offset += len(line)
    masked = "".join(chars)
    for match in re.finditer(r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)", masked):
        mask(*match.span())
    return "".join(chars)


def number_scan_text(text):
    """Blank out list and step numbering so C03 does not report them as new numbers."""
    chars = list(text)
    for regex in (LIST_NUMBER, STEP_NUMBER):
        for match in regex.finditer(text):
            for index in range(*match.span(1)):
                chars[index] = " "
    return "".join(chars)


def normalize(value):
    """Fold width, case, zero-width characters and punctuation for literal comparison."""
    folded = value.translate(_FULLWIDTH).translate(_ZERO_WIDTH).casefold().translate(_PUNCTUATION)
    return folded.replace(" ", "")


def anchor_match(text, normalized_text, alternatives):
    for value in alternatives:
        if value in text:
            return True, "literal", value
    for value in alternatives:
        folded = normalize(value)
        if folded and folded in normalized_text:
            return True, "normalized", value
    return False, "none", None


def synonym_overlap(alternatives, normalized_text):
    """Best bigram overlap between any anchor alternative and the candidate text."""
    best = 0.0
    longest = 0
    for value in alternatives:
        folded = normalize(value)
        longest = max(longest, len(folded))
        grams = {folded[i:i + 2] for i in range(len(folded) - 1)}
        if grams:
            best = max(best, sum(1 for gram in grams if gram in normalized_text) / len(grams))
    return best, longest


def finding(text, rule, category, severity, start, end, hint):
    return {
        "rule": rule, "category": category, "severity": severity,
        "offset": start, "end": end,
        "match": "" if start is None else text[start:end],
        "snippet": "" if start is None else text[max(0, start - 12):min(len(text), end + 12)],
        "hint": hint, "fix": hint,
    }


def collect(text):
    masked = mask_protected(text)
    first = re.search(r"\S[^。！？\n]*", masked)
    hits = []
    for rule, label, regex, fix in COMPILED:
        if rule in FIRST_SENTENCE_RULES:
            if first is None:
                continue
            window, base = first.group(), first.start()
        else:
            window, base = masked, 0
        for match in regex.finditer(window):
            hits.append(finding(text, rule, label, "review", base + match.start(), base + match.end(), fix))
    return sorted(hits, key=lambda hit: hit["offset"])


def summarize(text, hits):
    return {
        "chars": len(re.sub(r"\s", "", text)),
        "counts": {kind: sum(h["severity"] == kind for h in hits) for kind in ("blocker", "review")},
        "score": None,
    }


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def validate_contract(contract):
    if not isinstance(contract, dict) or set(contract) != {"schema_version", "required", "forbidden"}:
        raise ValueError("contract requires exactly schema_version, required, forbidden")
    if type(contract["schema_version"]) is not int or contract["schema_version"] != 2:
        raise ValueError("contract schema_version must be 2")
    required = contract["required"]
    if not isinstance(required, list) or not 1 <= len(required) <= 100:
        raise ValueError("contract.required must contain 1..100 anchors")
    seen = set()
    for item in required:
        if not isinstance(item, dict) or set(item) != {"id", "kind", "label", "source", "any_of"}:
            raise ValueError("anchor requires id, kind, label, source, any_of")
        if not all(nonempty_string(item[key]) for key in ("id", "kind", "label", "source")):
            raise ValueError("anchor fields must be nonempty strings")
        if item["id"] in seen or item["kind"] not in KINDS:
            raise ValueError("anchor id must be unique and kind must be supported")
        seen.add(item["id"])
        alternatives = item["any_of"]
        if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 20 or not all(nonempty_string(s) for s in alternatives):
            raise ValueError("any_of requires 1..20 nonempty literal strings")
    forbidden = contract["forbidden"]
    if not isinstance(forbidden, list) or len(forbidden) > 100 or not all(nonempty_string(s) for s in forbidden):
        raise ValueError("forbidden must be a list of nonempty literal strings")
    return contract


def audit(text, baseline=None, contract=None):
    if not nonempty_string(text):
        raise ValueError("candidate must be nonempty text")
    if baseline is not None and not nonempty_string(baseline):
        raise ValueError("baseline must be nonempty text")
    if contract is not None:
        validate_contract(contract)
    hits = collect(text)
    checks = []
    normalized_text = normalize(text)
    if contract is not None:
        for item in contract["required"]:
            matched, matched_by, evidence = anchor_match(text, normalized_text, item["any_of"])
            checks.append({"id": item["id"], "kind": item["kind"], "label": item["label"],
                           "matched": matched, "matched_by": matched_by,
                           "evidence": [evidence] if matched else [], "source": item["source"]})
            if not matched:
                overlap, longest = synonym_overlap(item["any_of"], normalized_text)
                if overlap >= SYNONYM_THRESHOLD and longest >= 4:
                    hit = finding(text, "C01", "锚点疑似同义改写", "review", None, None,
                                  "未字面命中：" + item["label"] + "。用词高度接近，人工确认是否同义改写，"
                                  "确认后更新合同的 any_of；不要据此认定已保留。")
                else:
                    hit = finding(text, "C01", "声明锚点缺失", "blocker", None, None,
                                  "核对是否遗漏或改写了：" + item["label"] + "。同义改写需人工核实后更新合同。")
                hit["anchor_id"] = item["id"]
                hit["anchor_overlap"] = round(overlap, 3) if not matched else None
                hits.append(hit)
        for phrase in contract["forbidden"]:
            start = text.find(phrase)
            if start >= 0:
                hits.append(finding(text, "C02", "命中声明禁用断言", "blocker", start, start + len(phrase),
                                    "核对合同禁止的断言，不要自动删除引用中的内容。"))
    added = []
    if baseline is not None:
        sources = "" if contract is None else "\n".join(item["source"] for item in contract["required"])
        known = set(NUMBER.findall(number_scan_text(baseline) + "\n" + sources))
        scan_text = number_scan_text(text)
        added = sorted(set(NUMBER.findall(scan_text)) - known)
        for number in added:
            match = next(m for m in NUMBER.finditer(scan_text) if m.group() == number)
            hits.append(finding(text, "C03", "新增数字待核实", "review", match.start(), match.end(),
                                "基线和声明来源中没有该数字；确认是否是有依据的新信息或步骤编号。"))
    stats = summarize(text, hits)
    blocked = stats["counts"]["blocker"] > 0
    verdict = "BLOCKED" if blocked else ("REVIEW" if hits or contract is None else "CHECKED")
    return {
        "schema_version": 2, "engine_version": VERSION,
        "passed": not blocked, "verdict": verdict,
        "scope": "literal-contract-and-surface-review",
        "semantic_review_required": True,
        "stats": stats, "violations": hits,
        "anchors": {"total": len(checks), "matched": sum(c["matched"] for c in checks), "items": checks},
        "numbers": {"checked": baseline is not None, "added": added},
    }


def render_report(report):
    anchors = report["anchors"]
    lines = ["de-armor v%s | %s | anchors=%s/%s | blockers=%s | review=%s" % (
        VERSION, report["verdict"], anchors["matched"], anchors["total"],
        report["stats"]["counts"]["blocker"], report["stats"]["counts"]["review"])]
    for hit in report["violations"]:
        lines.append("[%s][%s] %s: %s" % (hit["rule"], hit["severity"], hit["category"], hit["hint"]))
    lines.append("Scope: literal checks only; semantic review is still required. No quality score.")
    return "\n".join(lines)


def read_text(source):
    if source == "-":
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
    else:
        with Path(source).open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("input exceeds 1 MB")
    return data.decode("utf-8-sig")


def main():
    parser = argparse.ArgumentParser(description="de-armor v2: offline, non-generative response audit")
    parser.add_argument("source", help="UTF-8 file path, or - for stdin")
    parser.add_argument("--baseline", help="original answer file")
    parser.add_argument("--contract", help="v2 information contract JSON file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-score", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.min_score is not None:
        parser.error("v2 removes --min-score; use --contract and review verdict/violations")
    if args.baseline == "-" or args.contract == "-":
        parser.error("only source may read stdin")
    try:
        text = read_text(args.source)
        baseline = None if args.baseline is None else read_text(args.baseline)
        contract = None if args.contract is None else json.loads(read_text(args.contract))
        if args.contract is not None:
            validate_contract(contract)
        report = audit(text, baseline, contract)
    except (OSError, UnicodeError, ValueError) as exc:
        print("input error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_report(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
