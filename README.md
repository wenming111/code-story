# code-story

把**每次 git commit 背后的人机对话**采集下来,**存进同一个 commit**(`.ai-context/<...>.md`)。
日后任何 agent 读代码时,都能还原「这段代码当初**为什么**这么改」,而不只是「改了什么」。

- **面向 agent**:记录就在仓库里、紧挨代码。`git blame` 一行 → 读出产生那个 commit 的对话。
- **随 git 走**:clone/pull 就有,无需外部服务或数据库。
- **多 agent**:一个通用 git 钩子,适配 Claude Code、Codex、Cursor、Trae,以及手动/CI 提交。

## 工作原理

启用的仓库里,`pre-commit` 钩子(采集引擎)在每次提交时运行:

1. 按时间窗(自上次提交起)从本地 AI transcript 收集对话,跨 session。
2. 只保留人 + agent 的**文本**(丢弃工具输出、思考过程、系统噪声)。
3. **密钥脱敏**(key/token/私钥)后再写入。
4. 写 `.ai-context/<时间戳>-<来源>-<id>.md`,并 `git add` 进**同一个 commit**(不新增提交、不改 commit id)。

两条摘要路径:

- **② Agent 路径(首选)**:提交前 agent 把 2–4 行「为什么」写进 `.ai-context/.pending-summary`,钩子采用它(`summary_by: agent`)。
- **① 兜底**:手动/CI 提交用启发式摘要(最后一句人话 + 文件)(`summary_by: heuristic`)。

## 支持矩阵

| Agent | 对话采集 | Agent 摘要 | 启用方式 |
|---|---|---|---|
| **Claude Code** | ✅(`~/.claude`) | ✅ plugin skill + PreToolUse 强制 | plugin + 钩子 |
| **Codex** | ✅(`~/.codex`) | ✅ `AGENTS.md` 软提醒 | 钩子 + 片段 |
| **Cursor** | ⏳ v2(SQLite) | ✅ rules 软提醒 | 钩子 + rules |
| **Trae** | ⏳ v2(SQLite) | ✅ rules 软提醒 | 钩子 + rules |
| 手动 / CI | 无(无 transcript) | 启发式 | 钩子 |

`⏳ v2`:采集 Cursor/Trae 自身的对话正文需要逆向 SQLite,尚未完成——但钩子 + 你写的摘要现在就能记录。

## 安装

### 前置
- `git` 与 `python3`(仅标准库,无需 pip 包)。
- npm 方式额外需要 `node >= 14`。

### 方式 A:npm(推荐)
```sh
npm install -g code-story        # 或 npx code-story <命令>
code-story enable                # 在当前仓库启用
code-story enable /path/to/repo  # 指定仓库
code-story global                # 对你所有仓库启用(全局 core.hooksPath)
```
> npm 包名 `code-story` 若已被占用,请改用作用域名(如 `@你的用户名/code-story`)。

### 方式 B:克隆 + install.sh(无 node 环境)
```sh
git clone <code-story-仓库地址> ~/.code-story
~/.code-story/install.sh --enable            # 当前仓库
~/.code-story/install.sh --enable /path/to/repo
~/.code-story/install.sh --global            # 全局
```

无论 A/B,启用都会:把仓库的 `core.hooksPath` 指向 code-story 的 `hooks/`,并创建
`.ai-context/` 标记。把标记提交上去,队友 clone 后即继承:
```sh
git add .ai-context/README.md && git commit -m "chore: enable code-story"
```

> **全局方式的注意**:全局 `core.hooksPath` 会覆盖各仓库的 `.git/hooks` 和 husky 等工具。
> 用这些工具的话,建议用 `enable` 按仓启用,或自行做钩子链式调用。钩子只在带
> `.ai-context/` 标记的仓库里生效。

### 启用 Agent 摘要(②,按 agent)

**Claude Code** —— 安装 plugin(带 `code-story-commit` / `code-story-read` 两个 skill,
以及一个在缺 `.pending-summary` 时**阻止 `git commit`** 的 PreToolUse 强制钩子):
```
/plugin marketplace add <code-story-仓库地址>
/plugin install code-story
```
(对话采集仍依赖上面的 git 钩子。)强制仅对 Claude Code 生效;其它 agent 用下面的软提醒。

**Codex** —— 把片段追加到仓库的 `AGENTS.md`:
```sh
cat <code-story>/integrations/codex/AGENTS.md >> AGENTS.md
```

**Cursor**(可选)—— 拷贝规则:
```sh
mkdir -p .cursor/rules && cp <code-story>/integrations/cursor/code-story.mdc .cursor/rules/
```

**Trae**(可选)—— 把 `<code-story>/integrations/trae/code-story-rules.md` 添加为 Trae 项目规则。

### 队友
- **只读**(只想看历史对话):无需安装,`.ai-context/*.md` 随 `git clone` 自带。
- **也要采集**:每位队友在自己机器上做一次上面的安装。

## 存什么 / 隐私

每个 `.ai-context/*.md` 含 YAML front-matter(`source`、`model`、`steps`、`session_id`、
`parent`、`branch`、`summary`、`summary_by`、`files`)和对话正文。**不存**:工具结果/stdout、
思考过程、系统/meta 注入、子 agent(sidechain)。写入前对密钥做正则脱敏成 `[REDACTED]`。
对话会提交进仓库并随 git 共享——**请把启用的仓库放在可信(如内网)remote 上**。

## 读取知识

```sh
git blame -L <行>,<行> <文件>     # 行 -> commit
git show <commit> --name-only     # 找到它新增的 .ai-context/*.md
```
先读 front-matter 的 `summary`,需要细节再看正文。(更完整的读取侧 / PR 级视图在路线图上。)

## 目录结构

```
.claude-plugin/plugin.json       Claude Code plugin manifest
.claude-plugin/marketplace.json  marketplace 清单(/plugin marketplace add 用)
skills/code-story-commit/         写入侧 skill:提交前写 .pending-summary
skills/code-story-read/           读取侧 skill:blame→commit→对话
hooks/pre-commit                  通用采集引擎(自定位)
hooks/hooks.json + require-pending-summary.py  Claude PreToolUse 强制钩子
src/code_story/                   引擎:capture / adapters / redact / render
integrations/                     各 agent 片段(codex / cursor / trae)
bin/code-story.js                 npm CLI 入口
install.sh                        按仓 / 全局启用
.ai-context/                      采集记录(用户仓库里;本仓自身也 dogfood 保留)
```

## 注意 / 路线图

- Cursor/Trae 对话采集(SQLite)—— v2。
- 读取侧工具(blame→commit→对话、PR 聚合)—— 路线图。
- `commit-msg` 的 `AI-Session:` trailer、LLM 摘要 —— 后续。
- 全局 `core.hooksPath` 暂不会链式调用已有钩子/husky。
- 本仓库会 dogfood 自己(保留自身开发对话),因此**含内部内容,请放内网 remote**;
  发到公网时做一次「只导代码」的干净导出。
