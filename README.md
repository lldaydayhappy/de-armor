# De-Armor / 破甲

**少一点自保，多一点结果。删掉套话，不能删掉事实。**
**Less self-defense, more results. Cut the filler, never the facts.**

[中文](#中文) · [English](#english)

![De-Armor demo](assets/screenshots/01-hero.png)

---

## 中文

### 它解决什么

AI 的回答经常不是「不会」，而是「不敢直接交付」：先免责、再铺垫、把查资料的工作退回用户、用「各有优劣」代替选择、把不确定说成确定，或者反过来把一句有用的话压成一句空话。

De-Armor（破甲）是一份任务导向的回复校准技能。它不靠禁词表打分，而是先锁定任务与不可丢失的信息，再改写；需要时可以调用本地只读审查器检查事实锚点、约束遗漏和新增数字。

### 什么时候用

- 有能力完成，却只给免责声明或把工作退回用户。
- 用户要推荐，却只列优缺点，不给有条件的选择。
- 非关键参数缺失，就连问一串问题，不给能先用的草案。
- 看似简短直接，实则丢掉条件、否定、不确定性或真实风险。
- 已写好长回复，需要保留实质内容并压掉社交填充。

正常的简短回答直接交付，不必强行改写。用户只说「破甲」时，修复上一条回答，不先讲技能介绍。

### 安装

```sh
# 从 ClawHub 安装
clawhub install de-armor
```

或把本目录放进你的 agent 技能目录（例如 `~/.hermes/skills/`、`~/.config/opencode/skills/`）。核心流程只依赖 `SKILL.md`，不装工具也能用。

### 工作方式

1. **定位实际任务**：要答案、要选择、要成品、要排查动作，还是要情绪支持。
2. **锁定不可丢失的信息**：事实、条件、不确定性、权限边界、本轮产物。
3. **从任务重写**：保留事实与条件，压缩重复与对冲，把答案或阻塞原因前置，补齐能做的交付。
4. **核对后交付**：事实与约束 → 任务完成度 → 表达负担；只对发现的问题再改一轮。

三条硬约束：不把未知改成确定，不把未执行写成已验证，不为减少拒绝而扩大权限。

### 本地审查器

`scripts/armor_lint.py` 只读、不联网、不生成回答、不自动改文本。引用、围栏代码和行内代码不按日常措辞计入。

```sh
# 普通审查
python3 scripts/armor_lint.py draft.txt --json

# 合同审查：对照基线，核对锚点、禁用断言与新增数字
python3 scripts/armor_lint.py revised.txt \
  --baseline draft.txt --contract contract.json --json

# 自测与展示页一致性检查
python3 -B scripts/selftest.py
python3 -B scripts/build_demo.py --check
```

文本可用 `-` 从标准输入传入。结果分三档：

- `BLOCKED`：缺少声明锚点或出现禁用断言。
- `REVIEW`：发现措辞或新增数字提示，或未提供信息合同。
- `CHECKED`：本次机器检查未发现问题——**不是语义正确性认证**。

退出码：`0` 无机器阻断（仍需人工核对）；`1` 合同阻断；`2` 输入错误。v2 已移除 `--min-score`，传入会明确报错。

### 案例与实验台

`assets/cases.json` 是 6 个场景的唯一数据源：故障排查、生产变更、技术选型、先交草案、诚实边界、保留人味。每个案例都带「改前 / 改后 / 反例 / 信息合同」，并由脚本复算。

`assets/de-armor-demo.html` 是可离线打开的交互实验台，直接读取同一份案例数据，不需要 API key，不上传任何内容。

| 改前 / 改后对比 | 机器审查 |
|---|---|
| ![Compare](assets/screenshots/02-compare.png) | ![Machine check](assets/screenshots/05-machine-check.png) |

| 保留边界 | 反例拦截 |
|---|---|
| ![Keep boundary](assets/screenshots/03-keep-boundary.png) | ![Counterexample](assets/screenshots/06-counterexample.png) |

### 目录结构

```text
de-armor/
├── SKILL.md                     # 技能入口
├── README.md                    # 本文件
├── _meta.json                   # 本地分发元数据
├── assets/
│   ├── cases.json               # 案例唯一数据源
│   ├── de-armor-demo.html       # 离线交互实验台
│   └── screenshots/             # 实际浏览器截图
├── references/
│   ├── theory.md                # 方法与取舍
│   ├── armor-patterns.md        # 检测协议与局限
│   ├── overcorrection.md        # 过度压缩反例
│   └── rewrite-examples.md      # 场景练习与复跑方法
└── scripts/
    ├── armor_lint.py            # 只读审查器
    ├── selftest.py              # 36 项自测
    └── build_demo.py            # 实验台构建/校验
```

### 边界

- 机检通过不等于事实正确；语义仍需人工判断。
- 不覆盖宿主指令、授权与真实安全限制；不用于绕过权限。
- 不联网、不上传数据、不自动改写文本。
- 案例是构造材料，规则结果由本地脚本计算；不冒充外部模型 A/B 实测。

---

## English

### What it does

The problem is usually not that the model can't answer. It is that the answer is optimized to look careful instead of being useful: disclaimers first, research pushed back to the user, "it depends" instead of a conditional recommendation, uncertainty flattened into certainty — or a useful sentence compressed into an empty one.

De-Armor is a task-oriented response calibration skill. Instead of scoring banned words, it locks the task and the information that must survive, then rewrites. Optionally, a local read-only auditor checks fact anchors, dropped constraints, and newly introduced numbers.

### When to use it

- The model can do the work but only returns disclaimers or pushes it back.
- The user asks for a recommendation and gets a pros/cons list with no decision.
- Non-critical details are missing, and the model blocks on questions instead of drafting.
- A reply looks short and direct but silently drops conditions, negations, uncertainty, or real risk.
- A long draft needs to keep its substance while losing social padding.

Short, healthy answers should ship as-is. When the user just says "de-armor", fix the previous answer — don't open with a skill introduction.

### Install

```sh
# From ClawHub
clawhub install de-armor
```

Or drop this folder into your agent's skills directory (e.g. `~/.hermes/skills/`, `~/.config/opencode/skills/`). The core workflow only needs `SKILL.md`; the tools are optional.

### How it works

1. **Locate the actual task**: an answer, a choice, a deliverable, a debugging step, or emotional support.
2. **Lock what must survive**: facts, conditions, uncertainty, permission boundaries, and the artifact due this turn.
3. **Rewrite from the task**: keep facts and conditions, compress repetition and hedging, move the answer or blocker to the front, complete what can be delivered.
4. **Verify before shipping**: facts and constraints → task completion → reading burden. Fix only what is actually broken, once.

Three invariants: never turn the unknown into certainty, never present an unexecuted action as verified, never widen permissions just to avoid saying no.

### Local auditor

`scripts/armor_lint.py` is read-only and offline. It does not generate answers or edit text. Quotes, fenced code, and inline code are excluded from everyday-wording checks.

```sh
# Plain review
python3 scripts/armor_lint.py draft.txt --json

# Contract review: compare against a baseline, check anchors, forbidden claims, and new numbers
python3 scripts/armor_lint.py revised.txt \
  --baseline draft.txt --contract contract.json --json

# Self-test and demo consistency check
python3 -B scripts/selftest.py
python3 -B scripts/build_demo.py --check
```

Pass `-` to read from stdin. Verdicts:

- `BLOCKED`: a declared anchor is missing or a forbidden claim appears.
- `REVIEW`: wording or new-number hints, or no information contract supplied.
- `CHECKED`: this machine pass found nothing — **not a certification of semantic correctness**.

Exit codes: `0` no machine block (human review still required); `1` contract block; `2` input error. `--min-score` was removed in v2 and now fails explicitly.

### Cases and demo

`assets/cases.json` is the single source of truth for six scenarios: incident triage, production change, technology choice, draft-first delivery, honest boundaries, and keeping the human tone. Each case ships with before/after text, a counterexample, and an information contract, all re-checked by the scripts.

`assets/de-armor-demo.html` is an offline interactive lab that reads the same case data. No API key, no uploads.

| Before / after | Machine check |
|---|---|
| ![Compare](assets/screenshots/02-compare.png) | ![Machine check](assets/screenshots/05-machine-check.png) |

| Keeping boundaries | Counterexample blocked |
|---|---|
| ![Keep boundary](assets/screenshots/03-keep-boundary.png) | ![Counterexample](assets/screenshots/06-counterexample.png) |

### Repository layout

```text
de-armor/
├── SKILL.md                     # Skill entry point
├── README.md                    # This file
├── _meta.json                   # Local distribution metadata
├── assets/
│   ├── cases.json               # Single source of truth for cases
│   ├── de-armor-demo.html       # Offline interactive lab
│   └── screenshots/             # Real browser screenshots
├── references/
│   ├── theory.md                # Method and trade-offs
│   ├── armor-patterns.md        # Detection protocol and limits
│   ├── overcorrection.md        # Over-compression counterexamples
│   └── rewrite-examples.md      # Practice scenarios and rerun guide
└── scripts/
    ├── armor_lint.py            # Read-only auditor
    ├── selftest.py              # 36 self-tests
    └── build_demo.py            # Build / verify the demo
```

### Boundaries

- Passing the machine check is not proof of factual correctness; semantics still need a human.
- It does not override host instructions, authorization, or real safety limits, and must not be used to bypass permissions.
- No network access, no data uploads, no automatic rewriting.
- Cases are constructed material and rule results are computed locally; they are not presented as external model A/B tests.
