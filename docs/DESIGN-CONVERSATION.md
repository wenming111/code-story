# 设计对话记录 — code-story

> 本文件是项目立项时一场「需求拷问(grill)」对话的整理稿,记录每个关键决策**当时为什么这么定**。
> 与 `REQUIREMENTS.md` 互补:那份讲「定了什么」,这份讲「为什么」。
> 日期:2026-06-20

## 0. 起点

需求:把每次 git commit 对应的 AI 对话导出并关联,构建仓库维度知识库,
让 agent 读代码/历史时能看到当时人和 AI 的对话,更好理解 commit 细节。

可行性确认:Claude 对话存为**每 session 一个 JSONL**,位于 `~/.claude/projects/<按cwd编码>/<sessionId>.jsonl`,
每行带 `timestamp` / `cwd` / `gitBranch` / `sessionId` / `message`。git commit 以 Bash tool_use 形式出现在 transcript 里。

---

## 决策记录(问题 → 选择 → 理由)

### 1. 关联机制:git hook 主动采集
- 候选:① git hook 主动 ② 解析 transcript 提 SHA ③ 时间戳邻近 ④ 混合
- **选 ① git hook**。理由:时间戳邻近噪声大;解析 transcript 只能覆盖「Claude 自己执行的 commit」,漏手敲 commit。hook 在提交那刻最可靠。
- 关键发现:`$CLAUDE_CODE_SESSION_ID` 在 Bash 子进程 env 里,hook 可直接读(但后续被时间窗法取代为辅助)。

### 2. 对话切片:上次 commit 以来的增量 → 升级为时间窗横扫所有 session
- 初版:取「当前活跃 session 自上次 commit 以来」的增量。
- **暴露漏洞**(用户提出):Day1 聊很多、改了码但没提交;Day2 新 session 才提交 → 按「当前 session」会丢 Day1。
- **修正**:改为**时间窗**(上次 commit 时间 → 现在)横扫**本仓所有 session**,按 `cwd` + `timestamp` 过滤。`$CLAUDE_CODE_SESSION_ID` 降级为「谁触发」。

### 3. 使用范围:随仓库共享给团队
- **选「随仓库走」**。数据提交进仓库、clone 即得、仓库内有说明文件教 agent 读。稀疏(没装钩子的 commit 无对话)可接受。

### 4. 存储形态:仓库内 markdown = 真相源
- 候选:① 仓库内文件 ② git notes ③ 独立分支 ④ 仓库外 DB
- ② 默认 clone 带不过来、④ 不进仓库 → 排除。**选「仓库内 markdown 文件」做真相源,git 做协作,Obsidian 仅作可选个人视图**(其多人协作弱,不当存储/协作层)。

### 5. 提交方式:塞进同一个 commit(方案 ④)
- 候选:① 后补一条上下文提交(commit 翻倍) ② 异步批量 ③ 独立分支 ④ 塞进同一 commit
- **选 ④**:`pre-commit` 在提交生成前写文件并 `git add`,对话与代码进**同一个 commit**,零翻倍、关联最强。
- 代价:对话混进代码 diff(用户表示 code review 不是问题)。
- 副带解决:commit id 提交前拿不到 → ④ 靠「文件物理在该 commit 内」做**结构性关联**,不需要 id。

### 6. 关联机制再确认:文件塞进 commit 树 vs 标记+旁路存储(参考 Story app)
- 用户出示了一个类似产品(疑似叫 Story)的截图:commit message 带 `[Story-Checkpoint: <id>]`,旁路存储,多 agent(Cursor/Claude Code)。
- 对比后**仍选「文件塞进 commit 树」**:唯一不可让步的是「随仓库走、队友零配置读」,文件法原生满足;标记法只有旁路存储也在仓库才满足,否则是悬空指针。
- **改进**:偷 Story 的优点 —— 可选在 commit message 加一行轻量 `AI-Session:` trailer 当 grep 指针(不负责存储)。

### 7. 架构:架构 I(写进仓库,agent-first)起步
- 讨论了「App + 外置 DB」(Story 那种):repo 干净、富 GUI,但**对 agent 不是零配置**(要 MCP/API)、要运维服务、数据不随仓库走、是「做产品」级工程。
- 区分:「零配置」对人(下 App)和对 agent(要集成)是两回事;主消费者是 agent → in-repo 结构上更优。
- **选架构 I 起步,低成本,后续可演进到混合**(外置富存储 + 仓库瘦投影 + 人用 GUI)。

### 8. 存什么:人话 + agent 所有文本段 + file_path 轻痕迹
- 用户定:砍工具结果/执行记录、砍 thinking(太多)。
- **两个坑修正**:
  - 「模型最终输出」**不是只留最后一段**——「为什么」常在中间叙述里 → **保留 agent 写给人的所有文本段**。
  - 「执行记录」**不能全砍**——聚焦和 blame 要靠 `file_path` → **保留一行轻量「编辑了 X」痕迹**,只砍结果正文。
- 另砍:tool_result、系统注入/isMeta、大 blob(留引用)、sidechain。

### 9. 噪声过滤:混合(原始无损 + 文件匹配只聚焦摘要/索引)
- 候选:(a) 时间窗内全收(无损但噪声) (b) 只留动过本次文件的 turn(精准但丢推理 + Bash/手改盲区)
- 数据印证:Edit/Write 带 `file_path`,但最常用的 **Bash 无 file_path**,手改更无 tool_use → 纯 (b) 会丢「为什么」。
- **选混合**:原始层走 (a) 无损,(b) 文件匹配只用来给**摘要/索引层**聚焦。正好用上三层渐进披露。

### 10. 渐进式披露:三层
- tier 0 索引(**按需生成,非共享文件 → 避免合并冲突**)/ tier 1 摘要(front-matter)/ tier 2 原始对话。

### 11. 摘要生成:钩子启发式(i)
- 演进:初定「agent 顺手写(A)」,但因时间窗横扫多 session、且采集必须由钩子做(确定性/全覆盖/多 agent),A 撤掉。
  - 澄清:agent **能**读磁盘 transcript(早先「只有钩子能看 day1」说法有误);选钩子的真实理由是**确定性 + 每次提交都触发 + 单一多 agent 机制**,不依赖 agent 是否配合。
- **选 (i) 钩子启发式**:commit message + 切片第一句人话。零成本;以后可升级为一次 LLM 调用(ii)。

### 12. 读取侧:按需 + agent 自判,锚 git blame;PR 维度按需派生
- 触发:**(2) 按需 + agent 判断**,不每次读文件都查。
- 定位:`git blame` → commit → 摘要(够则止)→ 原始对话。
- PR 维度:**按需派生、不写 git**(`base..head` 聚合);**自下而上自动**(代码→commit→PR,用户无需知道 PR 号);commit→PR 靠平台 API + git 兜底;**阶梯升级(甲)**:commit 不够才抬到 PR。

### 13. 隐私:写入前密钥正则脱敏(甲)
- 对话提交即永久进 git 历史 + 团队共享 → 必须管。
- 存储规则(不存工具输出)已挡掉最大泄露面(.env Read、env dump);残余(人粘贴/agent 回显的密钥)**写入前正则脱敏 → `[REDACTED]`**,非阻塞。PII 暂不做。

### 14. 钩子行为 & 安装
- 钩子 = git 的东西,与 agent 无关;失败安全(rebase/merge/amend 跳过、防递归、出错放行)。
- 时间窗起点用「上次 commit 时间」(无状态)。
- trailer 需 `prepare-commit-msg`(另一个钩子),v1 可省。
- 安装:**你**全局 `core.hooksPath` 装一次 + 按仓 `.ai-context/` 标记开关(甲);**队友**数据随 clone 自动有、钩子各装一次。

### 15. 多 source:v1 做 Claude + Codex
- 适配器架构,统一连接键 = **cwd**,统一 schema = 第 8 条。
- 探测结果:Claude / Codex 是文件型 JSONL(自带 cwd+时间戳,🟢易);Cursor / Trae 是 VSCode 套壳的 SQLite(`state.vscdb`,🔴需逆向、随版本变)。
- **v1 = Claude + Codex;v2 = Cursor + Trae。**

---

## 待办 / 未决
- 读取侧 skill 的具体提示词与触发边界,尚未细化(写入侧已确认无大问题)。
- trailer、LLM 摘要(ii)、外置 GUI、Cursor/Trae 适配器 —— 均为后续演进项。
