# SPEC Process — Coding Agent Harness

## 概览

本文档记录与 AI agent 协作生成 SPEC.md 和 PLAN.md 的过程。Agent 使用 brainstorming 技能，通过结构化追问和方案对比，逐步细化设计。

---

## Brainstorming 关键节点

### 1. 初始场景选择 (5 个候选 → Bug 修复)

Agent 主动追问"主要面向什么编程场景"，给出 5 个候选（bug 修复、重构、新功能、代码审查、混合），并要求我分析每个对六维度的适配度。

**我的处理：** 倾向 bug 修复，但不确定。Agent 分析后给出明确推荐："Bug 修复是 sweet spot，护栏/反馈闭环都能充分展现"。我采纳。

**反思：** Agent 的分析表格对决策帮助很大。如果只问"你想做什么"，我可能会选"混合模式"导致 scope 爆炸。

---

### 2. 深度维度选择 (治理护栏 vs 反馈闭环)

我倾向治理护栏，Agent 没有直接反对，但引导我思考两个维度的可测性差异：

- "护栏容易写 mock 单测（给定操作 → 被拦截/通过）"
- "反馈闭环的收敛判断更复杂，但也更能展现自修复能力"

**我的处理：** 最终选择反馈闭环，理由是"更符合 agentic 系统的核心价值"。

**AI 建议采纳：** Agent 建议"反馈闭环比护栏更适合做深"，我采纳。

---

### 3. 反馈信号源设计 (多信号 vs 单信号)

Agent 问"反馈闭环的迭代信号源是什么"，给了 4 个选项。我回答"肯定都要"。

**我的原始设计：** 同时用编译错误、测试结果、LLM-as-Judge。

**Agent 的追问：** "LLM-as-Judge 成本高、难单测，MVP 做吗？"

**我的修正：** 改为分阶段流水线（build → test → optional judge），MVP 不做 judge。

**反思：** 这个追问避免了 MVP 过载。如果没有这个追问，我可能会在 MVP 里加入 LLM-as-Judge，导致项目复杂度爆炸。

---

### 4. 收敛策略 (3 轮迭代)

**第 1 轮：** 我提出"自适应收敛 + 置信度驱动"。

**第 2 轮：** Agent 追问"置信度从哪来？"，我意识到 OpenAI API 不直接返回置信度。

**第 3 轮：** Agent 建议"换成确定性指标：连续 N 轮无有效 edit_file"。

**最终设计：** 
- 硬性上限（max_iterations）
- 停滞检测（连续 N 轮错误数不变）
- 无编辑检测（连续 N 轮没有 edit_file 调用）

**AI 建议采纳：** Agent 建议砍掉置信度，用确定性指标替代。我采纳，理由是"更符合 §A.4-B 机制是代码不是提示词"。

---

### 5. HITL 机制设计 (同步阻塞 vs 异步挂起)

Agent 问"HITL 的暂停机制如何实现"，给了两个选项：
- 同步阻塞（agent 卡住等用户响应）
- 异步任务挂起（状态序列化，进程可退出）

**我的初始倾向：** 不确定，两者都行。

**Agent 分析：** "课程项目周期短，同步阻塞最简单。异步挂起状态管理复杂，对 MVP 是过度设计。"

**我的处理：** 选择同步阻塞，但加了一个约束"HITL 超时 300 秒自动拒绝"。

**反思：** Agent 的分析帮我省略了不必要的复杂度。如果我自己设计，可能会尝试异步挂起，导致项目延期。

---

## 关键迭代（≥3 轮）

### 迭代 1：WebUI 范围 (第 1 轮 → 第 2 轮)

**第 1 轮：** 我回答"交互式界面"，agent 理解为"完整 IDE 风格"。

**Agent 追问：** "WebUI + WebSocket + 完整 IDE 会吃掉大量时间，六个维度 + 凭据 + Docker + CI 已经够多了。建议砍到最小。"

**我的修正：** 改为"MVP 只做 3 个功能：提交 bug、看日志流、HITL 审批"。

**差异对比：**
```diff
- 完整 IDE 风格（代码编辑器、文件树、终端）
+ 3 个 MVP 功能（表单、日志、审批）
```

---

### 迭代 2：记忆持久化 (第 1 轮 → 第 2 轮)

**第 1 轮：** 我回答"保留对话历史就行，修复日志没必要"。

**Agent 追问：** "§A.4-D 明确说记忆最低实现必须能跨会话。纯内存列表连跨会话都不支持，可能不够。建议加 JSON 文件持久化。"

**我的修正：** 加 JSON 文件持久化（session 结束写 `~/.cache/harness/memory.json`）。

**差异对比：**
```diff
- In-memory list (no persistence)
+ In-memory list + JSON file persistence
```

**反思：** 这个追问暴露了我对课程要求的理解不足。如果没有这个追问，我可能会提交一个"记忆维度不够最低实现"的项目。

---

### 迭代 3：edit_file 多匹配行为 (审查反馈)

**审查反馈：** "你的 edit_file 设计没说如果 `old_string` 匹配多个位置怎么办。"

**我的原始设计：** 未定义。

**Agent 建议：** "明确定义：0 匹配报错，多匹配报错（要求更精确上下文），恰好 1 匹配才执行。"

**我的采纳：** 立即加入 SPEC。

**差异对比：**
```diff
 edit_file(path, old_string, new_string):
-  Behavior: not specified
+  Boundary Conditions:
+    - 0 matches → ToolResult(success=False, error="no_match")
+    - >1 matches → ToolResult(success=False, error="multiple_matches")
+    - 1 match → execute replacement
```

---

## AI 建议的采纳与推翻

### 采纳的建议

| 建议 | 理由 |
|------|------|
| 选 bug 修复场景 | "六个维度都能充分展现，且场景聚焦不失控" |
| 反馈闭环做深 | "比护栏更适合展现自修复能力，且 mock 可测性强" |
| 砍掉 LLM-as-Judge | "成本高、难单测，MVP 不需要" |
| 用确定性指标替代置信度 | "更符合 §A.4-B 机制是代码不是提示词" |
| 同步阻塞 HITL | "课程项目周期短，状态管理简单" |
| 加 JSON 文件持久化 | "满足跨会话最低实现要求" |
| 明确 edit_file 三态匹配 | "边界条件必须定义" |

### 推翻的建议

| 建议 | 我的理由 |
|------|----------|
| Story 8 拆成两个用户故事 | "WebUI 是一个功能单元，拆开失去叙事完整性。数量已经 8 个，不差这一个" |

**反思：** 在 Story 8 上，我坚持了自己的判断。Agent 过度拆分反而会让 spec 失去可读性。

---

## 对 brainstorming 技能的反思

### 做得好的地方

1. **结构化追问**：不是开放式"你还想做什么"，而是给出候选选项 + 分析适配度。这让我更快做出决策。

2. **暴露隐性假设**：比如"置信度从哪来"、"edit_file 多匹配怎么办"。如果我自己设计，这些边界条件很容易被忽略。

3. **课程要求对齐**：Agent 主动检查 SPEC 是否符合 refs/ 要求，发现了 HITL、WebUI、凭据等遗漏。

### 让我不满的地方

1. **过度拆分倾向**：建议拆 Story 8，实际上没必要。Agent 应该先问"你有多少用户故事"，再决定是否拆分。

2. **缺少成本分析**：在讨论 WebUI 范围时，Agent 只说"会吃掉大量时间"，没有给出具体估时。如果能说"WebSocket 双向通信调试可能要 2-3 天"，我会更快做出裁剪决策。

3. **冷启动验证未提前规划**：§4.5 要求用另一个 agent 试做 task，但 Agent 在 brainstorming 阶段没有提醒我"需要提前准备另一个 agent"。这个要求在 SPEC_PROCESS.md 里才暴露，如果能在计划阶段就提醒，我可以提前准备。

---

## 总结

Brainstorming 技能帮助我从"模糊想法"走向"具体 spec"，核心贡献是：
- 暴露隐性假设（置信度来源、edit_file 多匹配）
- 课程要求对齐（HITL、WebUI、凭据）
- 结构化决策（场景选择、深度维度、收敛策略）

主要不足是缺少成本分析和提前规划冷启动验证。整体而言，brainstorming 技能对 spec 质量有显著正面影响。

---

## 冷启动验证结果

于 2026-07-17 用另一个 agent（独立 session，无对话历史）完成验证。

### 验证 agent 信息

- **Agent 类型：** 独立 session（非原 agent）
- **输入文件：** SPEC.md + PLAN.md 仅两个文件
- **执行 Task：** Task 1（脚手架）、Task 2（数据模型）、Task 3（配置加载）

### 结果

23 个测试全部通过，**零暂停点**。新 agent 无需提问即可自主推进。

### 暴露的 spec/plan 缺陷

| 缺陷 | 修复 |
|------|------|
| Plan Task 1 缺 venv 创建步骤 | 已补充 `python3 -m venv .venv` 和激活命令 |
| Plan Task 1 的 git init 无判断 | 已改为 `git rev-parse --is-inside-work-tree 2>/dev/null \|\| git init` |
| pytest-asyncio 版本锁定 | 已改为 `>=0.24.0` |

### 反思

Spec 和 Plan 的清晰度通过了冷启动验证——新 agent 能直接上手，无需额外解释。暴露的 3 个问题都是环境配置层面的细节，而非设计层面的缺陷，说明 spec 本身足够健壮。

### 对 SPEC/PLAN 的修订

- PLAN.md: Task 1 Step 5 增加了 venv 创建步骤
- PLAN.md: Task 1 Step 7 增加了 git init 判断
- PLAN.md: pyproject.toml 的 pytest-asyncio 版本锁定为 `>=0.24.0`
