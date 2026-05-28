---
name: daily-summary
description: Use when the user asks to summarize today's work, produce a daily report from local Claude Code/Codex conversations, review what was done today, or email a Feishu/Lark daily work summary from local agent session logs.
---

# Daily Summary

Generate a same-day work summary from local Claude Code and Codex session logs, render it as HTML, and send it to the user's own Feishu/Lark mailbox.

## Core Rules

- Use local time. Default review window: `09:00 <= timestamp < 21:00`.
- Use only evidence from session logs. Do not invent work, decisions, tests, commits, PRs, or delivery state.
- Skip summary-generation/admin chats unless they contain user-requested work worth reporting.
- Produce HTML directly. Do not create an intermediate Markdown report.
- Keep the top summary suitable for pasting into a daily report; put evidence and ambiguity in the detail section.
- Never hard-code email addresses or tokens. Query the current mailbox at send time.

## Workflow

1. Collect evidence:

   ```bash
   python3 ~/.agents/skills/daily-summary/scripts/build_daily_summary.py --date YYYY-MM-DD --json
   ```

   If the user does not specify a date, use today's local date. Override `--start`, `--end`, or `--timezone` only when the user asks for a different window.
   The script excludes chats that only generated/sent the daily summary. Add `--include-summary-chats` only when auditing the summary workflow itself.

2. Read the JSON output and revise the report mentally before writing final HTML:

   - Merge Claude Code and Codex sessions by `cwd`.
   - Treat user messages as demand/context, and command/tool output as delivery evidence.
   - Use assistant messages only as a clue; verify claimed completion against command results, file paths, commits, PRs, or releases.
   - Mark interruption/correction messages such as `[Request interrupted by user]`, `不对`, `别`, `停`, `删掉`, `错了`.
   - Preserve concrete identifiers: file paths, function names, command names, commit hashes, PR numbers, release tags, service URLs.

3. Render the first HTML draft:

   ```bash
   python3 ~/.agents/skills/daily-summary/scripts/build_daily_summary.py --date YYYY-MM-DD --output daily-summary-YYYY-MM-DD.html
   ```

4. Edit the HTML if needed. The script creates an evidence scaffold; the final report must be a human-quality summary, not a raw log dump.

5. Validate before sending:

   ```bash
   python3 ~/.agents/skills/daily-summary/scripts/build_daily_summary.py --date YYYY-MM-DD --json
   if grep -n "<button\\|<script\\|onclick" daily-summary-YYYY-MM-DD.html; then exit 1; fi
   lark-cli doctor
   ```

   The `grep` check should produce no matches.

6. Send to self:

   ```bash
   ME=$(lark-cli mail user_mailboxes profile --params '{"user_mailbox_id":"me"}' -q '.data.primary_email_address')
   lark-cli mail +send \
     --to "$ME" \
     --subject "每日工作总结 - YYYY-MM-DD" \
     --body "$(cat daily-summary-YYYY-MM-DD.html)" \
     --confirm-send
   ```

   If this is the first run in a new environment, or the user asks to review first, omit `--confirm-send` and report that a draft was created.

## Data Sources

Claude Code:

- `~/.claude/projects/<escaped-cwd>/*.jsonl`
- Relevant fields: `timestamp`, `cwd`, `type=user`, `type=assistant`, `message.content`.

Codex:

- `~/.codex/state_5.sqlite` for active threads and `rollout_path`.
- `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` and older archived rollout files when needed.
- Relevant events: `session_meta`, `user_message`, `agent_message`, `function_call`, `exec_command_end`, `function_call_output`.

## Report Shape

Use this two-layer structure:

- `摘要（可提交）`: unordered list by project. Each bullet is one readable sentence. Busy projects may use a short nested list.
- `详细工作分析（本人复盘用）`: per-project evidence with time span, first/last user message, main thread, corrections, errors, delivery nodes, and follow-ups.
- `跨项目观察`: include only when the evidence supports it, such as repeated decisions, context switching, unresolved work, or shared technical direction.
- Footer: `数据源：Claude Code X 个会话 + Codex Y 个线程（Z 个 rollout）`.

Quality bar:

- Prefer "未捕获明确交付节点" over pretending something shipped.
- If command output contradicts assistant text, trust command output and say so.
- If the summary is thin because logs are thin, state the limitation plainly.
- The default report should be concise. Expand the detail section only when the user asks for a long retrospective or the day has many corrections/failed attempts.

## HTML Requirements

- Use inline styles suitable for email clients.
- Use semantic tags: `h1`, `h2`, `h3`, `ul`, `li`, `ol`, `strong`, `code`, `hr`, `p`.
- Do not include `<button>`, `<script>`, `onclick`, external CSS, remote images, or JavaScript-dependent controls.
- Escape raw log text before inserting it into HTML.
- `assets/template.html` is a visual/style reference, not a required fill-in form.

## Failure Handling

- No Claude/Codex logs: generate a short HTML noting no usable session data and do not fabricate content.
- `state_5.sqlite` unavailable: scan `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` directly.
- `lark-cli doctor` fails: leave the HTML on disk and tell the user authorization must be refreshed.
- Mail send fails: keep the HTML path and report the exact failing command/exit signal.
