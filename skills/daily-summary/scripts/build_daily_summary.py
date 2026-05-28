#!/usr/bin/env python3
"""Collect local Claude Code/Codex session signals and render daily-summary HTML."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


CORRECTION_RE = re.compile(r"(不对|别|停|删掉|错了|不需要|不是这样|先别)")
ERROR_RE = re.compile(r"(Traceback|ERROR|Exception|Error:|failed|失败|报错)", re.I)
DELIVERY_RE = re.compile(r"\b(commit|pr|pull request|merge|release|tag|deploy|发布|合并|提交)\b", re.I)
SKIP_PREFIXES = ("<", "Base directory for this skill:")
SUMMARY_TRIGGER_RE = re.compile(r"^\s*(\$?daily-summary|总结今天.*工作|输出每日总结|根据对话整理日报)\s*$", re.I)
SUMMARY_ADMIN_RE = re.compile(r"(lark-cli|飞书|邮箱|授权|继续|安装好了)", re.I)


@dataclass
class Event:
    ts: datetime
    kind: str
    text: str
    source: str


@dataclass
class Project:
    name: str
    cwd: str
    source_files: set[str] = field(default_factory=set)
    events: list[Event] = field(default_factory=list)

    def add(self, event: Event) -> None:
        self.events.append(event)
        self.source_files.add(event.source)

    @property
    def users(self) -> list[Event]:
        return [e for e in self.events if e.kind == "user"]

    @property
    def commands(self) -> list[Event]:
        return [e for e in self.events if e.kind == "command"]


def parse_ts(raw: object, tz: ZoneInfo) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, timezone.utc).astimezone(tz)
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value).astimezone(tz)
    except ValueError:
        return None


def in_window(ts: datetime, day: date, start: time, end: time) -> bool:
    return ts.date() == day and start <= ts.time() < end


def clean_text(value: object, limit: int = 600) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        value = "\n".join(parts)
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    if not text or any(text.startswith(prefix) for prefix in SKIP_PREFIXES):
        return ""
    if text.startswith("{") and "tool_result" in text[:80]:
        return ""
    return text[:limit]


def project_key(cwd: str | None, fallback: str) -> tuple[str, str]:
    cwd = cwd or ""
    if cwd:
        return Path(cwd).name or cwd, cwd
    return fallback, ""


def add_project(projects: dict[str, Project], cwd: str | None, fallback: str) -> Project:
    name, normalized_cwd = project_key(cwd, fallback)
    key = normalized_cwd or name
    if key not in projects:
        projects[key] = Project(name=name, cwd=normalized_cwd)
    return projects[key]


def discover_claude_files(day: date, start: time, end: time, tz: ZoneInfo) -> list[Path]:
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        return []
    start_dt = datetime.combine(day, start, tzinfo=tz).timestamp()
    end_dt = datetime.combine(day, end, tzinfo=tz).timestamp()
    files = []
    for path in root.rglob("*.jsonl"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if start_dt <= mtime < end_dt:
            files.append(path)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def parse_claude(path: Path, projects: dict[str, Project], day: date, start: time, end: time, tz: ZoneInfo) -> None:
    current_cwd = None
    fallback = path.parent.name.lstrip("-").replace("-", "/") or "claude"
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = parse_ts(item.get("timestamp"), tz)
        if ts is None or not in_window(ts, day, start, end):
            continue
        current_cwd = item.get("cwd") or current_cwd
        typ = item.get("type")
        if typ == "user":
            text = clean_text(item.get("message", {}).get("content"))
            if text:
                add_project(projects, current_cwd, fallback).add(Event(ts, "user", text, str(path)))
        elif typ == "assistant":
            text = clean_text(item.get("message", {}).get("content"), limit=400)
            if text:
                add_project(projects, current_cwd, fallback).add(Event(ts, "assistant", text, str(path)))


def discover_codex_rollouts(day: date, start: time, end: time, tz: ZoneInfo) -> list[tuple[Path, str | None, str | None]]:
    db = Path.home() / ".codex" / "state_5.sqlite"
    found: dict[Path, tuple[str | None, str | None]] = {}
    if db.exists():
        start_epoch = int(datetime.combine(day, start, tzinfo=tz).timestamp())
        end_epoch = int(datetime.combine(day, end, tzinfo=tz).timestamp())
        try:
            con = sqlite3.connect(db)
            con.row_factory = sqlite3.Row
            for row in con.execute(
                """
                select title, cwd, rollout_path
                from threads
                where updated_at >= ? and updated_at < ?
                order by updated_at desc
                """,
                (start_epoch, end_epoch),
            ):
                rollout = row["rollout_path"]
                if rollout:
                    found[Path(os.path.expanduser(rollout))] = (row["cwd"], row["title"])
            con.close()
        except sqlite3.Error:
            pass
    session_root = Path.home() / ".codex" / "sessions" / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}"
    if session_root.exists():
        for path in session_root.glob("rollout-*.jsonl"):
            found.setdefault(path, (None, None))
    return [(path, cwd, title) for path, (cwd, title) in found.items() if path.exists()]


def parse_codex(path: Path, cwd_hint: str | None, title: str | None, projects: dict[str, Project], day: date, start: time, end: time, tz: ZoneInfo) -> None:
    current_cwd = cwd_hint
    fallback = title or path.stem
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = parse_ts(item.get("timestamp"), tz)
        typ = item.get("type")
        payload = item.get("payload") or {}
        if typ == "session_meta":
            current_cwd = payload.get("cwd") or current_cwd
        if ts is None or not in_window(ts, day, start, end):
            continue
        if typ == "event_msg" and payload.get("type") == "user_message":
            text = clean_text(payload.get("message"))
            if text:
                add_project(projects, current_cwd, fallback).add(Event(ts, "user", text, str(path)))
        elif typ == "event_msg" and payload.get("type") == "agent_message":
            text = clean_text(payload.get("message"), limit=500)
            if text:
                add_project(projects, current_cwd, fallback).add(Event(ts, "assistant", text, str(path)))
        elif typ == "event_msg" and payload.get("type") == "exec_command_end":
            command = clean_text(payload.get("command"), limit=300)
            exit_code = payload.get("exit_code")
            stdout = clean_text(payload.get("stdout"), limit=240)
            stderr = clean_text(payload.get("stderr"), limit=240)
            text = f"{command} -> exit {exit_code}"
            if stdout:
                text += f"; stdout: {stdout}"
            if stderr:
                text += f"; stderr: {stderr}"
            add_project(projects, payload.get("cwd") or current_cwd, fallback).add(Event(ts, "command", text, str(path)))
        elif typ == "response_item" and payload.get("type") == "function_call":
            name = clean_text(payload.get("name"), limit=80)
            args = clean_text(payload.get("arguments"), limit=220)
            if name:
                add_project(projects, current_cwd, fallback).add(Event(ts, "tool", f"{name} {args}", str(path)))


def summarize_project(project: Project) -> dict[str, object]:
    events = sorted(project.events, key=lambda e: e.ts)
    users = [e for e in events if e.kind == "user"]
    first = users[0] if users else events[0]
    last = users[-1] if users else events[-1]
    corrections = [e for e in users if CORRECTION_RE.search(e.text) or "Request interrupted" in e.text]
    errors = [e for e in events if ERROR_RE.search(e.text) or ("exit 0" not in e.text and e.kind == "command" and "exit None" not in e.text)]
    deliveries = [e for e in events if DELIVERY_RE.search(e.text)]
    return {
        "name": project.name,
        "cwd": project.cwd,
        "span": f"{first.ts:%H:%M}-{last.ts:%H:%M}",
        "user_turns": len(users),
        "sources": len(project.source_files),
        "first_user": users[0].text if users else "",
        "last_user": users[-1].text if users else "",
        "user_samples": [(e.ts.strftime("%H:%M"), e.text) for e in users[:8]],
        "last_assistant": next((e.text for e in reversed(events) if e.kind == "assistant"), ""),
        "commands": [(e.ts.strftime("%H:%M"), e.text) for e in project.commands[-8:]],
        "corrections": [(e.ts.strftime("%H:%M"), e.text) for e in corrections[:6]],
        "errors": [(e.ts.strftime("%H:%M"), e.text) for e in errors[:8]],
        "deliveries": [(e.ts.strftime("%H:%M"), e.text) for e in deliveries[:8]],
    }


def is_summary_generation_chat(project: Project) -> bool:
    users = [e.text for e in project.users]
    if not users or not any(SUMMARY_TRIGGER_RE.search(text) for text in users):
        return False
    neutral_re = re.compile(r"^\s*(hello|hi|你好|继续|a|ok|好的|嗯|1|2)?\s*$", re.I)
    for text in users:
        if SUMMARY_TRIGGER_RE.search(text):
            continue
        if neutral_re.search(text):
            continue
        if SUMMARY_ADMIN_RE.search(text):
            continue
        return False
    return True


def li(text: str) -> str:
    return f"<li>{html.escape(text)}</li>"


def render_html(day: date, summaries: list[dict[str, object]], counts: dict[str, int]) -> str:
    source_line = f"数据源：Claude Code {counts['claude_sessions']} 个会话 + Codex {counts['codex_threads']} 个线程（{counts['codex_rollouts']} 个 rollout）"
    if not summaries:
        body = "<p>复盘窗口内未抽取到可用会话信号。</p>"
    else:
        summary_items = []
        detail_items = []
        for item in summaries:
            headline = str(item["first_user"] or item["last_assistant"] or "有会话活动")
            summary_items.append(f"<li><strong>{html.escape(str(item['name']))}</strong>：{html.escape(headline[:90])}</li>")
            samples = "".join(li(f"{t} {text}") for t, text in item["user_samples"])
            commands = "".join(li(f"{t} {text}") for t, text in item["commands"]) or "<li>未捕获命令结果</li>"
            corrections = "".join(li(f"{t} {text}") for t, text in item["corrections"]) or "<li>未捕获明显打断或纠正</li>"
            errors = "".join(li(f"{t} {text}") for t, text in item["errors"]) or "<li>未捕获明显异常</li>"
            deliveries = "".join(li(f"{t} {text}") for t, text in item["deliveries"]) or "<li>未捕获明确交付节点</li>"
            detail_items.append(
                f"""
                <h3>{html.escape(str(item['name']))}</h3>
                <ul>
                  <li><strong>目录</strong>：<code>{html.escape(str(item['cwd'] or '未知'))}</code></li>
                  <li><strong>时段</strong>：{html.escape(str(item['span']))}，{item['user_turns']} 轮用户输入，{item['sources']} 个源文件</li>
                  <li><strong>起手问题</strong>：{html.escape(str(item['first_user']))}</li>
                  <li><strong>收尾状态</strong>：{html.escape(str(item['last_user'] or item['last_assistant']))}</li>
                  <li><strong>推进主线候选</strong><ul>{samples}</ul></li>
                  <li><strong>命令 / 工具证据</strong><ul>{commands}</ul></li>
                  <li><strong>被打断 / 被纠正</strong><ul>{corrections}</ul></li>
                  <li><strong>异常与报错</strong><ul>{errors}</ul></li>
                  <li><strong>交付节点</strong><ul>{deliveries}</ul></li>
                </ul>
                """
            )
        body = f"""
        <h2>摘要（可提交）</h2>
        <ul>{''.join(summary_items)}</ul>
        <hr>
        <h2>详细工作分析（本人复盘用）</h2>
        {''.join(detail_items)}
        """
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>每日工作总结 - {day:%Y-%m-%d}</title>
</head>
<body style="font-family:-apple-system,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;line-height:1.7;color:#1f2329;max-width:760px;margin:0 auto;padding:24px;">
<h1 style="font-size:24px;border-bottom:2px solid #3370ff;padding-bottom:8px;">每日工作总结 - {day:%Y-%m-%d}</h1>
{body}
<hr>
<p style="color:#8f959e;font-size:13px;">{html.escape(source_line)}</p>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect local Claude Code/Codex signals for daily-summary.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Local date, YYYY-MM-DD.")
    parser.add_argument("--start", default="09:00", help="Inclusive local start time, HH:MM.")
    parser.add_argument("--end", default="21:00", help="Exclusive local end time, HH:MM.")
    parser.add_argument("--timezone", default=os.environ.get("TZ") or "Asia/Shanghai", help="IANA timezone.")
    parser.add_argument("--output", default=None, help="HTML output path. Defaults to daily-summary-YYYY-MM-DD.html.")
    parser.add_argument("--json", action="store_true", help="Print collected project summaries as JSON instead of writing HTML.")
    parser.add_argument("--include-summary-chats", action="store_true", help="Include chats whose only purpose was generating/sending the daily summary.")
    args = parser.parse_args()

    day = date.fromisoformat(args.date)
    start = time.fromisoformat(args.start)
    end = time.fromisoformat(args.end)
    tz = ZoneInfo(args.timezone)
    projects: dict[str, Project] = {}

    claude_files = discover_claude_files(day, start, end, tz)
    for path in claude_files:
        parse_claude(path, projects, day, start, end, tz)

    codex_rollouts = discover_codex_rollouts(day, start, end, tz)
    for path, cwd, title in codex_rollouts:
        parse_codex(path, cwd, title, projects, day, start, end, tz)

    summaries = [
        summarize_project(project)
        for project in projects.values()
        if project.events and (args.include_summary_chats or not is_summary_generation_chat(project))
    ]
    summaries.sort(key=lambda item: (item["user_turns"], item["sources"]), reverse=True)
    counts = {
        "claude_sessions": len(claude_files),
        "codex_threads": len({cwd or title or str(path) for path, cwd, title in codex_rollouts}),
        "codex_rollouts": len(codex_rollouts),
    }

    if args.json:
        print(json.dumps({"date": args.date, "counts": counts, "projects": summaries}, ensure_ascii=False, indent=2))
        return 0

    output = Path(args.output or f"daily-summary-{day:%Y-%m-%d}.html")
    output.write_text(render_html(day, summaries, counts), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
