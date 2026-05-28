#!/usr/bin/env python3
"""采集指定日期范围内的本机 Claude Code / Codex 会话信号。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8 fallback
    ZoneInfo = None  # type: ignore[assignment]


CORRECTION_RE = re.compile(r"(不对|别|停|删掉|错了|不需要|不是这样|先别|Request interrupted)")
ERROR_RE = re.compile(r"(Traceback|ERROR|Exception|Error:|failed|失败|报错|exit [1-9]\d*)", re.I)
DELIVERY_RE = re.compile(r"\b(commit|pr|pull request|merge|release|tag|deploy|发布|合并|提交|创建|生成|写入)\b", re.I)
SKIP_PREFIXES = ("<environment_context>", "<permissions", "<collaboration_mode>", "<skills_instructions>")


def get_tz(name: str) -> dt.tzinfo:
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    if name in {"Asia/Shanghai", "PRC", "CST"}:
        return dt.timezone(dt.timedelta(hours=8), name)
    return dt.datetime.now().astimezone().tzinfo or dt.timezone.utc


def parse_ts(raw: object, tz: dt.tzinfo) -> dt.datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return dt.datetime.fromtimestamp(raw, dt.timezone.utc).astimezone(tz)
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def clean_text(value: object, limit: int = 700) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") in {"text", "input_text", "output_text"}:
                    parts.append(str(item.get("text") or ""))
            elif isinstance(item, str):
                parts.append(item)
        value = "\n".join(parts)
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    if not text or any(text.startswith(prefix) for prefix in SKIP_PREFIXES):
        return ""
    if text.startswith("{") and "tool_result" in text[:120]:
        return ""
    return text[:limit]


def in_range(ts: dt.datetime, start_dt: dt.datetime, end_dt: dt.datetime) -> bool:
    return start_dt <= ts <= end_dt


def project_name(cwd: str | None, fallback: str) -> str:
    if cwd:
        return Path(cwd).name or cwd
    return fallback


def add_event(projects: dict[str, dict[str, object]], cwd: str | None, fallback: str, event: dict[str, object]) -> None:
    key = cwd or fallback
    if key not in projects:
        projects[key] = {
            "name": project_name(cwd, fallback),
            "cwd": cwd or "",
            "events": [],
            "sources": set(),
        }
    project = projects[key]
    project["events"].append(event)  # type: ignore[index,union-attr]
    project["sources"].add(event["source"])  # type: ignore[index,union-attr]


def discover_claude_files(start_dt: dt.datetime, end_dt: dt.datetime) -> list[Path]:
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        return []
    start_epoch = start_dt.timestamp()
    files = []
    for path in root.rglob("*.jsonl"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= start_epoch:
            files.append(path)
    return sorted(files)


def parse_claude(path: Path, projects: dict[str, dict[str, object]], start_dt: dt.datetime, end_dt: dt.datetime, tz: dt.tzinfo) -> None:
    current_cwd = None
    fallback = path.parent.name.lstrip("-").replace("-", "/") or path.stem
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
        if ts is None or not in_range(ts, start_dt, end_dt):
            continue
        current_cwd = item.get("cwd") or current_cwd
        typ = item.get("type")
        text = ""
        kind = typ or "event"
        if typ == "user":
            text = clean_text(item.get("message", {}).get("content"))
        elif typ == "assistant":
            text = clean_text(item.get("message", {}).get("content"), limit=500)
        if text:
            add_event(
                projects,
                current_cwd,
                fallback,
                {"ts": ts.isoformat(), "kind": kind, "text": text, "source": str(path)},
            )


def codex_days(start_dt: dt.datetime, end_dt: dt.datetime) -> list[dt.date]:
    days = []
    day = start_dt.date()
    while day <= end_dt.date():
        days.append(day)
        day += dt.timedelta(days=1)
    return days


def discover_codex_rollouts(start_dt: dt.datetime, end_dt: dt.datetime) -> list[tuple[Path, str | None, str | None]]:
    found: dict[Path, tuple[str | None, str | None]] = {}
    db = Path.home() / ".codex" / "state_5.sqlite"
    if db.exists():
        try:
            con = sqlite3.connect(db)
            con.row_factory = sqlite3.Row
            for row in con.execute(
                """
                select title, cwd, rollout_path
                from threads
                where updated_at >= ? and updated_at <= ?
                order by updated_at desc
                """,
                (int(start_dt.timestamp()), int(end_dt.timestamp())),
            ):
                rollout = row["rollout_path"]
                if rollout:
                    found[Path(os.path.expanduser(rollout))] = (row["cwd"], row["title"])
            con.close()
        except sqlite3.Error:
            pass

    for day in codex_days(start_dt, end_dt):
        root = Path.home() / ".codex" / "sessions" / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}"
        if root.exists():
            for path in root.glob("rollout-*.jsonl"):
                found.setdefault(path, (None, None))
    return [(path, cwd, title) for path, (cwd, title) in found.items() if path.exists()]


def parse_codex(path: Path, cwd_hint: str | None, title: str | None, projects: dict[str, dict[str, object]], start_dt: dt.datetime, end_dt: dt.datetime, tz: dt.tzinfo) -> None:
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
        typ = item.get("type")
        payload = item.get("payload") or {}
        ts = parse_ts(item.get("timestamp") or payload.get("timestamp"), tz)
        if typ == "session_meta":
            current_cwd = payload.get("cwd") or current_cwd
            continue
        if ts is None or not in_range(ts, start_dt, end_dt):
            continue

        kind = ""
        text = ""
        if typ == "event_msg" and payload.get("type") == "user_message":
            kind = "user"
            text = clean_text(payload.get("message"))
        elif typ == "event_msg" and payload.get("type") == "agent_message":
            kind = "assistant"
            text = clean_text(payload.get("message"), limit=600)
        elif typ == "event_msg" and payload.get("type") == "exec_command_end":
            kind = "command"
            command = clean_text(payload.get("command"), limit=260)
            exit_code = payload.get("exit_code")
            stdout = clean_text(payload.get("stdout"), limit=260)
            stderr = clean_text(payload.get("stderr"), limit=260)
            text = f"{command} -> exit {exit_code}"
            if stdout:
                text += f"; stdout: {stdout}"
            if stderr:
                text += f"; stderr: {stderr}"
        elif typ == "response_item" and payload.get("type") == "function_call":
            kind = "tool"
            name = clean_text(payload.get("name"), limit=80)
            args = clean_text(payload.get("arguments"), limit=220)
            text = f"{name} {args}".strip()

        if text:
            add_event(
                projects,
                payload.get("cwd") or current_cwd,
                fallback,
                {"ts": ts.isoformat(), "kind": kind or typ, "text": text, "source": str(path)},
            )


def summarize_project(project: dict[str, object]) -> dict[str, object]:
    events = sorted(project["events"], key=lambda e: e["ts"])  # type: ignore[index]
    users = [e for e in events if e["kind"] == "user"]
    commands = [e for e in events if e["kind"] == "command"]
    corrections = [e for e in users if CORRECTION_RE.search(str(e["text"]))]
    errors = [e for e in events if ERROR_RE.search(str(e["text"]))]
    deliveries = [e for e in events if DELIVERY_RE.search(str(e["text"]))]
    first = events[0] if events else {}
    last = events[-1] if events else {}

    def slim(items: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
        return [{"ts": e["ts"], "kind": e["kind"], "text": e["text"]} for e in items[:limit]]

    timeline_candidates = users[:8] + commands[-6:] + deliveries[-6:] + errors[-6:]
    timeline = sorted({(e["ts"], e["kind"], e["text"]): e for e in timeline_candidates}.values(), key=lambda e: e["ts"])
    return {
        "name": project["name"],
        "cwd": project["cwd"],
        "span": [first.get("ts", ""), last.get("ts", "")],
        "event_count": len(events),
        "user_turns": len(users),
        "source_count": len(project["sources"]),  # type: ignore[arg-type]
        "sources": sorted(str(s) for s in project["sources"])[:12],  # type: ignore[index]
        "first_user": users[0]["text"] if users else "",
        "last_user": users[-1]["text"] if users else "",
        "last_assistant": next((e["text"] for e in reversed(events) if e["kind"] == "assistant"), ""),
        "timeline": slim(timeline, 24),
        "commands": slim(commands[-12:], 12),
        "corrections": slim(corrections[:8], 8),
        "errors": slim(errors[:10], 10),
        "deliveries": slim(deliveries[:10], 10),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", help="起始日期，YYYY-MM-DD")
    parser.add_argument("--end-date", help="结束日期，YYYY-MM-DD，默认今天")
    parser.add_argument("--days", type=int, help="包含今天的近 N 个自然日")
    parser.add_argument("--timezone", default=os.environ.get("TZ") or "Asia/Shanghai", help="IANA 时区，默认 Asia/Shanghai")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出采集结果")
    return parser.parse_args()


def resolve_range(args: argparse.Namespace, tz: dt.tzinfo) -> tuple[dt.datetime, dt.datetime]:
    today = dt.datetime.now(tz).date()
    if args.days is not None:
        if args.days <= 0:
            raise SystemExit("--days 必须大于 0")
        start_day = today - dt.timedelta(days=args.days - 1)
        end_day = today
    else:
        start_day = dt.date.fromisoformat(args.start_date) if args.start_date else today
        end_day = dt.date.fromisoformat(args.end_date) if args.end_date else start_day
    if end_day < start_day:
        raise SystemExit("结束日期不能早于起始日期")
    start_dt = dt.datetime.combine(start_day, dt.time.min, tzinfo=tz)
    end_dt = dt.datetime.combine(end_day, dt.time.max.replace(microsecond=0), tzinfo=tz)
    return start_dt, end_dt


def main() -> int:
    args = parse_args()
    tz = get_tz(args.timezone)
    start_dt, end_dt = resolve_range(args, tz)
    projects: dict[str, dict[str, object]] = {}

    claude_files = discover_claude_files(start_dt, end_dt)
    for path in claude_files:
        parse_claude(path, projects, start_dt, end_dt, tz)

    codex_rollouts = discover_codex_rollouts(start_dt, end_dt)
    for path, cwd, title in codex_rollouts:
        parse_codex(path, cwd, title, projects, start_dt, end_dt, tz)

    summaries = [summarize_project(project) for project in projects.values() if project["events"]]
    summaries.sort(key=lambda item: (item["span"][0], item["cwd"] or item["name"]))
    result = {
        "range": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "timezone": str(tz),
        },
        "counts": {
            "claude_files": len(claude_files),
            "codex_threads": len({cwd or title or str(path) for path, cwd, title in codex_rollouts}),
            "codex_rollouts": len(codex_rollouts),
            "projects": len(summaries),
        },
        "projects": summaries,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
