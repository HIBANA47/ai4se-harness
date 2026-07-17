# AGENTS.md — 执行 PLAN.md 须知

> 本文件是给执行 agent 的快速参考。PLAN.md 有 3800+ 行，这里只提炼**容易踩坑的关键约束**。

---

## 每个 Task 必做的工作流

冷启动验证暴露的核心问题：PLAN 只写了代码步骤，agent 会跳过工作流纪律。**以下步骤与代码步骤同等重要，不得跳过。**

### 开工前

```bash
# 必须用 worktree，不能直接在 main 开发
git worktree add ../harness-task-N feature/task-N
cd ../harness-task-N
```

### 完成后

1. **更新 PLAN.md**：把本 Task 的 `- [ ]` 改为 `- [x]`，附 commit hash
2. **更新 AGENT_LOG.md**，每条记录必须包含以下 7 个字段（缺一扣分）：
   - 时间戳 + task 编号
   - 触发的 Superpowers 技能（如 `subagent-driven-development`、`test-driven-development`）
   - 关键 prompt / context 配置
   - commit hash
   - **两阶段评审结果**：先 spec 合规检查（数据模型/接口是否与 SPEC 一致），再代码质量检查（TDD 是否完整、有无冗余代码）。两者都 ✅ 才能继续。
   - 人工干预（修改了什么、为什么）
   - 学到的教训
3. **推送分支到 origin，不要本地 merge**：
   ```bash
   git push origin feature/task-N
   # 然后通知用户在 GitHub 网页上手动合并 PR
   # 用户合并后，清理 worktree：
   git worktree remove ../harness-task-N
   ```

> **绝对不要自己执行 `git merge` 到 main。** 推送 feature 分支后停下来，让用户在 GitHub 上手动点合并按钮。这是 PR 工作流的硬性要求。

---

## .gitignore 规则

| 文件 | 是否提交 | 说明 |
|------|----------|------|
| `.harness.example.yaml` | ✅ 提交 | 示例配置，供参考 |
| `.harness.local.yaml` | ❌ gitignore | 本地覆盖配置，含个人偏好 |
| `.harness.yaml` | ❌ gitignore | 运行时生成的配置 |
| `docs/superpowers/` | ❌ gitignore | Superpowers 技能自动生成的中间产物，不是交付物 |
| `.env` | ❌ gitignore | 含凭据，绝对不能提交 |

---

## 交付物合规要求

| 交付物 | 课程条款 | 说明 |
|--------|----------|------|
| `.gitlab-ci.yml` 含 `unit-test` job | §五.6 | CI 必须从早期 Task 就配置，不能拖后 |
| `AGENT_LOG.md` 6 字段格式 | §4.9 | 每个 Task 完成后立即追加记录 |
| `README.md` 含安装/运行/安全/目录结构 | §五.4 | 后期覆盖 |
| git worktree + PR 工作流 | §4.6/§4.7 | 每个 Task 必须，直接在 main 开发是硬性违规 |
| mock-LLM 单测 | A.§A.6 | 核心机制必须有，可脱离真实 LLM 运行 |
| 机制演示（3 场景） | A.§A.6 | 治理护栏拦截 + 反馈闭环自修正 + 重点维度行为 |
