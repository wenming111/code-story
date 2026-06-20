# Commit ↔ AI 对话知识库 — 需求文档

> 状态:需求阶段(本文件只描述需求与设计决策,不含实现代码)
> 最后更新:2026-06-20

## 1. 目标

每次 git commit 时,自动把「当时产生这次改动的人机对话」关联并存进仓库。
日后 agent(或人)阅读代码时,能查到「这段代码当初**为什么**这么改」,
形成一个**仓库维度的知识库**。

- 主消费者:**agent**(Claude / Cursor / Codex 等读代码时);人看是附加价值。
- 数据随仓库走(git 共享),队友 clone 即得。
- 稀疏可接受:没装钩子的人提交的 commit 没有对话,允许存在。

## 2. 总架构

**架构 I:数据写进仓库,agent-first,低成本起步。**
后续可演进到「外置富存储 + 仓库瘦投影」的混合形态,
以及参考 Story 那样的人用时间线 GUI。

---

## 3. 写入侧

| # | 决策 | 说明 |
|---|---|---|
| 3.1 | **机制** | git `pre-commit` 钩子(纯 git 脚本,与 agent 无关),提交时扫本地 transcript |
| 3.2 | **落地** | 对话 markdown **塞进同一个 commit**(方案 ④);可选 `prepare-commit-msg` 加 `AI-Session:` trailer 当 grep 指针(v1 可省) |
| 3.3 | **切片** | **时间窗**:上次 commit 时间 → 现在(无状态),横扫本仓所有 session,跨 session/跨天不漏 |
| 3.4 | **存什么** | 留:真人文本 + agent 所有文本段 + 轻量 `file_path` 痕迹。砍:thinking、工具结果正文、stdout、系统注入、大 blob、sidechain |
| 3.5 | **隐私** | 写入前正则**密钥脱敏** → `[REDACTED]`(AWS key / JWT / 私钥头 / password= / 高熵串等) |
| 3.6 | **摘要** | 钩子启发式:commit message + 切片第一句人话 +(文件列表)。零成本;以后可升级为一次 LLM 调用 |
| 3.7 | **失败安全** | rebase/merge/cherry-pick/amend 跳过;只暂存 `.ai-context` 时跳过(防递归);**任何错都放行提交(exit 0)** |

### 3.8 pre-commit 钩子行为流程
1. 判断是否跳过(rebase/merge/amend、防递归、窗口内无对话、出错放行)
2. 定时间窗(上次 commit 时间 → 现在)
3. 由仓库根定位对应的 transcript 目录,扫 `*.jsonl`,挑时间戳在窗口内、cwd 在仓库根下的事件
4. 按 3.4 过滤
5. 聚焦(混合):原始层无损 + `file_path ∩ 暂存文件` 只给摘要/索引聚焦
6. 密钥脱敏(3.5)
7. 生成摘要(3.6)
8. 写 `.ai-context/<时间戳>-<session短id>.md`(front-matter + 对话正文),`git add` 进本次 commit

### 3.9 文件 front-matter 字段
`agent`(claude-code/codex/...)、`model`、`steps`、`session_id`、`parent`(父提交)、
`branch`、`files`、`created_at`、`summary`。

---

## 4. 读取侧

| # | 决策 | 说明 |
|---|---|---|
| 4.1 | **触发** | 按需 + agent 自判,锚在 `git blame` |
| 4.2 | **三层渐进披露** | 索引(按需生成,非共享文件,避免合并冲突)/ 摘要(front-matter)/ 原始对话 |
| 4.3 | **聚焦** | 原始层无损 + `file_path ∩ 暂存文件` 只给摘要/索引聚焦 |
| 4.4 | **PR 维度** | **按需派生**(不存 git):`base..head` 聚合 commit 摘要;commit→PR 靠平台 API + git 兜底;自下而上自动、**阶梯升级**(commit 不够才抬到 PR) |

读取路径:代码行 → `git blame` → commit → 读该 commit 的摘要(够则止)→ 不够再读原始对话 → 仍要全貌才抬到 PR 维度。

---

## 5. 多 source(可扩展口子)

- **适配器架构**:钩子「找 transcript」一步泛化为「对每个 source 适配器,吐出 [时间窗] 内、[仓库根] 下的归一化事件」。
- **统一连接键 = cwd**(四个工具都记 cwd)。
- **统一 schema = 第 3.4 条**。

| 工具 | 存储 | 格式 | 难度 | 计划 |
|---|---|---|---|---|
| Claude Code | `~/.claude/projects/<按cwd>/*.jsonl` | JSONL | 🟢 | **v1** |
| Codex | `~/.codex/sessions/<年/月/日>/rollout-*.jsonl` | JSONL | 🟢 | **v1** |
| Cursor | `~/Library/.../Cursor/.../state.vscdb` | SQLite | 🔴 | v2 |
| Trae | `~/Library/.../Trae CN/User/globalStorage/state.vscdb` | SQLite | 🔴 | v2 |

---

## 6. 安装

- **你自己**:全局 `git config --global core.hooksPath <managed-dir>` 装一次 + 在想启用的仓库放 `.ai-context/` 标记开关。
- **队友**:数据随 clone 自动有;钩子需各自跑一次 setup 安装(git 安全机制不会自动执行仓库带的钩子配置,husky 等同类工具皆如此)。
- 注意:**数据随仓库走;钩子要每台机器单独装。**

---

## 7. 形态演进

- **v1** = Claude plugin(pre-commit 钩子 + 读取 skill + 安装命令),source 支持 Claude + Codex。
- **后续** → 多 agent 通吃(补 Cursor/Trae 适配器)→ 可选外置富存储 + 人用时间线 GUI(参考 Plaud/Story 的多视图摘要)。
