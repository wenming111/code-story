# code-story

Capture the human↔AI conversation behind **every git commit** and store it
**inside the same commit** (`.ai-context/<...>.md`). Later, any agent reading the
code can recover *why* a change was made — not just what changed.

- **Agent-first**: the record lives in the repo, next to the code. `git blame` a
  line → read the conversation that produced that commit.
- **In-repo, travels with git**: clone/pull and the history is already there. No
  external service, no database.
- **Multi-agent**: one universal git hook works for Claude Code, Codex, Cursor,
  Trae, and even manual/CI commits.

## How it works

A `pre-commit` git hook (the *capture engine*) runs on every commit in an enabled
repo. It:

1. Collects the conversation since the last commit (time-window) from your local
   AI transcripts, across sessions.
2. Keeps only human + agent **text** (drops tool output, thinking, system noise).
3. **Redacts secrets** (keys, tokens, private keys) before writing.
4. Writes `.ai-context/<timestamp>-<source>-<id>.md` and `git add`s it into the
   **same commit** (no extra commit, no commit-id churn).

Two summary paths:

- **② Agent path (preferred)** — the agent writes a 2–4 line *why* to
  `.ai-context/.pending-summary` before committing; the hook uses it
  (`summary_by: agent`).
- **① Fallback** — manual/CI commits get a heuristic summary (last human message
  + files) (`summary_by: heuristic`).

## Support matrix

| Agent | Conversation capture | Agent-authored summary | Enablement |
|---|---|---|---|
| **Claude Code** | ✅ (`~/.claude`) | ✅ via plugin skill | plugin + `install.sh` |
| **Codex** | ✅ (`~/.codex`) | ✅ via `AGENTS.md` | `install.sh` + snippet |
| **Cursor** | ⏳ v2 (SQLite) | ✅ via rules | `install.sh` + rules |
| **Trae** | ⏳ v2 (SQLite) | ✅ via rules | `install.sh` + rules |
| Manual / CI | n/a (no transcript) | heuristic | `install.sh` |

`⏳ v2`: capturing Cursor/Trae's own conversation body needs SQLite reverse-engineering
and isn't done yet — but the hook + the summary you write are recorded today.

## Install

### Prerequisites
- `git` and `python3` (stdlib only — no pip packages).

### Step 1 — get code-story (once per machine)
```sh
git clone <code-story-repo-url> ~/.code-story
```

### Step 2 — enable it in a repo
Run from inside the target repo (or pass its path):
```sh
~/.code-story/install.sh --enable          # current repo
~/.code-story/install.sh --enable /path/to/repo
```
This points the repo's `core.hooksPath` at `~/.code-story/hooks` and creates the
`.ai-context/` marker. Commit the marker so teammates inherit it:
```sh
git add .ai-context/README.md && git commit -m "chore: enable code-story"
```

> Prefer the whole machine? `~/.code-story/install.sh --global` sets a global
> `core.hooksPath`. The hook still only acts in repos that have a `.ai-context/`
> marker. **Caveat:** a global `core.hooksPath` overrides per-repo `.git/hooks`
> and tools like husky. If you use those, prefer `--enable` per repo, or chain
> hooks manually.

### Step 3 — enable the agent-authored summary (per agent)

**Claude Code** — install the plugin (gives the `code-story` skill that tells
Claude to write `.pending-summary` before committing):
```
/plugin marketplace add <code-story-repo-url>
/plugin install code-story
```
(Capture still requires the git hook from Step 2.)

**Codex** — append the snippet to your repo's `AGENTS.md`:
```sh
cat ~/.code-story/integrations/codex/AGENTS.md >> AGENTS.md
```

**Cursor** *(optional)* — copy the rule into your repo:
```sh
mkdir -p .cursor/rules && cp ~/.code-story/integrations/cursor/code-story.mdc .cursor/rules/
```

**Trae** *(optional)* — add `~/.code-story/integrations/trae/code-story-rules.md`
as a Trae project rule.

### Teammates
- **Read-only** (just want to see past conversations): nothing to install — the
  `.ai-context/*.md` files come with `git clone`.
- **Also capture**: each teammate does Step 1–3 once on their machine.

## What's stored / privacy

Each `.ai-context/*.md` has YAML front-matter (`source`, `model`, `steps`,
`session_id`, `parent`, `branch`, `summary`, `summary_by`, `files`) and the
conversation body. **Not** stored: tool results/stdout, thinking, system/meta
injections, sidechains. Secrets are regex-redacted to `[REDACTED]` before writing.
Conversations are committed to the repo and shared via git — keep enabled repos on
trusted (e.g. internal) remotes.

## Reading the knowledge

```sh
git blame -L <line>,<line> <file>     # line -> commit
git show <commit> --name-only         # find its .ai-context/*.md
```
Read the front-matter `summary` first; open the body for detail. (A richer
read-side / PR-level view is on the roadmap.)

## Layout

```
.claude-plugin/plugin.json   Claude Code plugin manifest
skills/code-story/SKILL.md    Claude skill: write .pending-summary before commit
hooks/pre-commit              universal capture engine (self-locating)
src/code_story/               engine: capture, adapters, redact, render
integrations/                 per-agent snippets (codex / cursor / trae)
install.sh                    enable per repo or globally
.ai-context/                  captured records (in user repos; git-ignored here)
```

## Caveats / roadmap

- Cursor/Trae conversation capture (SQLite) — v2.
- Read-side tooling (blame→commit→conversation, PR aggregation) — roadmap.
- `commit-msg` trailer (`AI-Session:`) and LLM summaries — later.
- Global `core.hooksPath` does not chain to existing hooks/husky yet.
