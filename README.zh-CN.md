<p align="center">
  <img src="docs/banner.svg" alt="de-armor" width="960">
</p>

<h1 align="center">🛡️ 破甲 De-Armor — 任务导向的回复校准</h1>

<p align="center"><strong>Version 2.1.0</strong></p>

<p align="center">
  <em>少一点自保，多一点结果。删掉套话，不能删掉事实。当 AI 开始推诿、铺垫、假中立或只讲原则不交付时，把回答拉回能推进任务的样子。</em>
</p>

<p align="center">
  <a href="https://github.com/ninetyhe-90/de-armor/stargazers"><img src="https://img.shields.io/github/stars/ninetyhe-90/de-armor?logo=github&label=Stars" alt="GitHub stars"></a>
  <a href="https://github.com/ninetyhe-90/de-armor"><img src="https://img.shields.io/badge/version-2.1.0-c6ff70?style=flat" alt="Version 2.1.0"></a>
  <a href="https://clawhub.ai/skills/de-armor"><img src="https://img.shields.io/badge/ClawHub-de--armor-6b8e23" alt="ClawHub de-armor"></a>
  <br>
  <img src="https://img.shields.io/badge/Python-%3E%3D3.9-3776AB?logo=python&logoColor=fff" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/tests-47%20passing-65a30d" alt="47 项自测通过">
  <img src="https://img.shields.io/badge/runtime-offline%20%C2%B7%20no%20API-1a73e8" alt="离线，无 API">
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">中文</a>
</p>

> **v2 重写了规则。** v1 用禁词分数和 90 分门槛裁决回复，v2 已移除。输出改为 `schema_version: 2`、`stats.score: null`，审查是任务导向的：事实、条件、不确定性、边界有没有保住，用户要的产物有没有交付。`--min-score` 现在会明确报错，不再静默忽略。

> **机检只是第二双眼睛，不是判决。** `armor_lint.py` 通过，只代表本次检查没有丢失声明锚点、没有出现禁用断言。它**不是**事实或语义正确性的认证。

## 目录

- [它是什么](#它是什么)
- [什么时候用](#什么时候用)
- [安装](#安装)
- [预览](#预览)
- [使用](#使用)
- [工作方式](#工作方式)
- [本地审查器](#本地审查器)
- [案例与实验台](#案例与实验台)
- [目录结构](#目录结构)
- [边界](#边界)
- [更新日志](#更新日志)

---

## 它是什么

AI 的回答经常以一种很具体的方式失效：它被优化成「看起来很谨慎」，而不是「真的有用」。先免责、再铺垫、把查资料的工作退回用户、用「各有优劣」代替选择、把不确定说成确定——或者反过来，把一句有用的话压成一句空话。

**破甲（de-armor）** 是一份任务导向的回复校准技能，以可移植的 `SKILL.md` 分发，不绑定任何单一 agent 或平台。它先锁定任务和不可丢失的信息，再从任务重写，而不是从禁词表重写。事实、条件、否定、不确定性和权限边界留下；重复、身份前置和空对冲删掉。

| 你会得到 | 它做什么 |
|---|---|
| **任务定位** | 把真实需求——答案、选择、成品、排查动作或情绪支持——从表面礼貌里分出来 |
| **信息账本** | 保住事实、条件、不确定性、边界和本轮该交付的产物 |
| **任务优先改写** | 保留、压缩、重排、补齐；不为显得具体而编造事实 |
| **可选审查器** | 只读、离线的 Python 检查器，核对事实锚点、约束遗漏和新增数字 |
| **可复现案例** | 6 个场景，带改前/改后、反例和信息合同，全部由脚本复算 |

它不是「请简洁一点」提示词。短不是目标，交付才是。真实拒绝可以是对的答案，长回答也可以是对的答案。

---

## 什么时候用

- 有能力完成，却只给免责声明或把工作退回用户。
- 用户要推荐，却只列优缺点，不给有条件的选择。
- 非关键参数缺失，就连问一串问题，不给能先用的草案。
- 看似简短直接，实则丢掉条件、否定、不确定性或真实风险。
- 已写好长回复，需要保留实质内容并压掉社交填充。

正常的简短回答直接交付，不必强行改写。用户只说「破甲」时，修复上一条回答，不先讲技能介绍。

---

## 安装

破甲是一份可移植的 `SKILL.md` 加上可选的 `references/` 和 `scripts/`。里面没有任何东西绑定某个产品：没有 SDK、没有运行时、没有配置文件、没有厂商 API。任何能读技能文件或系统提示的 agent 都能用。

```sh
# 从 ClawHub 安装
clawhub install de-armor

# 或克隆后自行接入
git clone https://github.com/ninetyhe-90/de-armor.git
```

然后按你的 agent 原本加载技能的方式接入：

- **有技能目录的 agent**——把整个目录放进去即可；目录结构是约定，不是硬性要求。
- **靠规则/指令驱动的 agent**——把 `SKILL.md` 贴进它的规则文件、`AGENTS.md` 或系统提示。
- **没有技能机制**——把 `SKILL.md` 前置到对话上下文。

核心流程只依赖 `SKILL.md`。审查器是可选的，只用 Python 3.9+ 标准库，不需要第三方包。

## 预览

<p align="center">
  <img src="assets/screenshots/01-hero.png" alt="破甲离线实验台" width="820">
</p>

`assets/de-armor-demo.html` 是可离线打开的交互实验台，和脚本读取同一份 `assets/cases.json`。不需要 API key，不上传任何内容。

| 改前 / 改后对比 | 机器审查 |
|---|---|
| ![Compare](assets/screenshots/02-compare.png) | ![Machine check](assets/screenshots/05-machine-check.png) |

| 保留边界 | 反例拦截 |
|---|---|
| ![Keep boundary](assets/screenshots/03-keep-boundary.png) | ![Counterexample](assets/screenshots/06-counterexample.png) |

---

## 使用

技能由自然语言触发。常见说法：

```text
破甲
说人话，别绕
别给我一堆免责声明，直接给方案
审一下这段回复，保留事实和条件
```

用户没给额外内容时，技能修复上一条回答，不先输出一篇方法论。

---

## 工作方式

1. **定位实际任务**——要答案、要选择、要成品、要排查动作，还是要情绪支持。
2. **锁定不可丢失的信息**——事实、条件、不确定性、权限边界、本轮产物。
3. **从任务重写**——保留、压缩、重排、补齐。新推断显式标注；缺证据就核实，不编造。
4. **核对后交付**——事实与约束 → 任务完成度 → 表达负担。只对发现的问题再改一轮。

三条硬约束：

- 不把未知改成确定。
- 不把未执行写成已验证。
- 不为减少拒绝而扩大权限。

「可能」「建议」「抱歉」「不能」都**不是**禁词。删掉它们会改变置信度、权限或风险时，就保留。

<details>
<summary><strong>信息合同（v2）</strong></summary>

长文或明确要求审计时，可以用 JSON 合同核对：

```json
{
  "schema_version": 2,
  "required": [
    {
      "id": "status",
      "kind": "fact",
      "label": "观测到状态码 504",
      "source": "网关返回 504",
      "any_of": ["504"]
    },
    {
      "id": "unknown",
      "kind": "uncertainty",
      "label": "根因仍不能确定",
      "source": "没有完整链路，不能确定根因",
      "any_of": ["不能确定根因"]
    }
  ],
  "forbidden": ["根因就是数据库", "已经验证根因"]
}
```

`BLOCKED`：缺少声明锚点或出现禁用断言。`REVIEW`：发现措辞或新增数字提示，或未提供信息合同。`CHECKED`：本次机器检查未发现问题——仍不是语义认证。

</details>

---

## 本地审查器

`scripts/armor_lint.py` 只读、离线，不生成回答、不改文本、不联网。引用、围栏代码和行内代码不按日常措辞计入。

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

文本可用 `-` 从标准输入传入。

| 结果 | 含义 |
|---|---|
| `BLOCKED` | 缺少声明锚点或出现禁用断言 |
| `REVIEW` | 措辞或新增数字提示，或未提供信息合同 |
| `CHECKED` | 本次机器检查未发现问题——**不是**正确性认证 |

退出码：`0` 无机器阻断（仍需人工核对）；`1` 合同阻断；`2` 输入错误。

---

## 案例与实验台

`assets/cases.json` 是 6 个场景的唯一数据源。每个案例都带改前/改后、反例和信息合同，并由脚本复算。

| 案例 | 标签 | 它测什么 |
|---|---|---|
| 故障排查 | `DIAGNOSE` | 先给动作，根因仍未确定 |
| 生产变更 | `PRESERVE` | 风险要具体，但不编锁表时长 |
| 技术选型 | `DECIDE` | 给有条件的选择，不是优缺点清单 |
| 先交草案 | `DELIVER` | 交一版能用的，不再多问一轮 |
| 诚实边界 | `BE HONEST` | 说清做不到的，做完能做的 |
| 保留人味 | `STAY HUMAN` | 删社交填充，不删有效共情 |

展示页和截图使用同一份数据。案例是构造材料，规则结果由本地脚本计算，不冒充外部模型 A/B 实测。

---

## 目录结构

```text
de-armor/
├── SKILL.md                     # 技能入口
├── README.md                    # 英文 README
├── README.zh-CN.md              # 中文 README
├── _meta.json                   # 本地分发元数据
├── docs/
│   └── banner.svg               # README 横幅
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
    ├── selftest.py              # 47 项自测
    └── build_demo.py            # 实验台构建/校验
```

---

## 边界

- 机检通过不等于事实正确；语义仍需人工判断。
- 不覆盖宿主指令、授权与真实安全限制；不用于绕过权限。
- 不联网、不上传数据、不自动改写文本。
- 案例是构造材料，规则结果由本地脚本计算，不冒充外部模型 A/B 实测。
- 宿主真实边界、用户格式需求和必要工作流程不因本技能改变。

---

## 更新日志

- **2.1.0** — 检测面扩展但标准不变严：新增 A06 识别“各有优劣 / 需综合考虑”式假中立，写明触发条件的选择不受影响；新增 E01–E05 英文基础模式（身份前置、通用免责、赞美填充、假中立、答案延后），全部为提示级。合同锚点匹配前做全角/大小写/空白/标点归一化，疑似同义改写降级为提示而非阻断；C03 不再把有序列表编号和“第 N 步”当作新增数字。自测 36 → 47 项。
- **2.0.3** — 仅文档：安装说明完全平台无关——不写具体产品路径、不点名厂商，按你的 agent 原有方式加载 `SKILL.md` 即可。行为无变化。
- **2.0.2** — README 重做为居中、徽章优先的双语版本，并加入自定义横幅。行为无变化。
- **2.0.1** — 新增中英双语 README。
- **2.0.0** — 任务导向重写。移除禁词打分和 90 分门槛；新增 `schema_version: 2`、信息合同、新增数字检查、6 个可复现案例和离线实验台。
- **1.x** — 旧的 hard/soft/style 规则集与 `render` API，v2 已移除。
