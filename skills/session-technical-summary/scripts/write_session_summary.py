#!/usr/bin/env python3
"""追加一次会话总结时间线条目，并渲染为独立 HTML。"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
from pathlib import Path
import re
import sqlite3
import sys


DEFAULT_ROOT = Path.home() / "文档" / "AI-Session"
DEFAULT_TITLE = "AI 会话技术总结"
OVERVIEW_START = "<!-- SESSION_SUMMARY_OVERVIEW_START -->"
OVERVIEW_END = "<!-- SESSION_SUMMARY_OVERVIEW_END -->"
TIMELINE_START = "<!-- SESSION_SUMMARY_TIMELINE_START -->"
OVERVIEW_HEADING_RE = re.compile(r"^## 总览总结\s*$", flags=re.MULTILINE)
TIMELINE_HEADING_RE = re.compile(r"^## 调用时间线\s*$", flags=re.MULTILINE)


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def truncate_utf8_bytes(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip()


def sanitize_segment(value: str, fallback: str = "session") -> str:
    value = value.strip()
    value = re.sub(r"[\x00-\x1f\x7f/\\:]+", "-", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"^[=._#\-\s]+|[=._#\-\s]+$", "", value)
    value = re.sub(r"-{2,}", "-", value).strip("-. ")
    if not value:
        return fallback
    return truncate_utf8_bytes(value, 120).strip("-. ") or fallback


def is_range_session(session_id: str) -> bool:
    return session_id.startswith("range-")


def codex_thread_display_title(session_id: str) -> str:
    if not session_id or is_range_session(session_id):
        return ""
    db = Path.home() / ".codex" / "state_5.sqlite"
    if not db.exists():
        return ""
    try:
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        row = con.execute(
            "select title, preview, first_user_message from threads where id = ?",
            (session_id,),
        ).fetchone()
        con.close()
    except sqlite3.Error:
        return ""
    if not row:
        return ""
    for key in ("title", "preview", "first_user_message"):
        value = row[key] or ""
        title = extract_display_title(value)
        if title:
            return title
    return ""


def extract_display_title(value: str) -> str:
    value = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", value or "")
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"[=*_#\-\s]{3,}", line):
            continue
        line = re.sub(r"^#+\s*", "", line).strip()
        line = re.sub(r"^\+\s*", "", line).strip()
        if not line:
            continue
        if len(line) > 100:
            line = line[:100].rstrip()
        return line
    compact = re.sub(r"\s+", " ", value).strip()
    return compact[:100].rstrip()


def read_update(args: argparse.Namespace) -> str:
    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        raise SystemExit("本次时间线条目为空")
    return text + "\n"


def read_overview(args: argparse.Namespace) -> str:
    if args.overall_file and args.overall_summary:
        raise SystemExit("--overall-file 和 --overall-summary 不能同时使用")
    if args.overall_file:
        text = Path(args.overall_file).read_text(encoding="utf-8")
    elif args.overall_summary:
        text = args.overall_summary
    else:
        text = ""
    return text.strip()


def update_document_header(text: str, title: str, timestamp: str, session_dir: Path) -> str:
    if re.search(r"^# .*$", text, flags=re.MULTILINE):
        text = re.sub(r"^# .*$", f"# {title}", text, count=1, flags=re.MULTILINE)
    if re.search(r"^- 最近更新: .*$", text, flags=re.MULTILINE):
        text = re.sub(
            r"^- 最近更新: .*$",
            f"- 最近更新: {timestamp}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if re.search(r"^- 输出目录: .*$", text, flags=re.MULTILINE):
        text = re.sub(
            r"^- 输出目录: .*$",
            f"- 输出目录: `{session_dir}`",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def document_session_id(text: str) -> str:
    match = re.search(r"^- Session ID:\s*`?([^`\n]+)`?\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def ensure_matching_session(text: str, session_id: str, md_path: Path) -> None:
    existing_session_id = document_session_id(text)
    if existing_session_id and session_id and existing_session_id != session_id:
        raise SystemExit(
            f"拒绝写入 Session ID 不匹配的归档: {md_path} "
            f"(existing={existing_session_id}, current={session_id})"
        )


def strip_internal_markers(text: str) -> str:
    for marker in (OVERVIEW_START, OVERVIEW_END, TIMELINE_START):
        text = text.replace(marker, "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def next_update_number(text: str) -> int:
    numbers = [
        int(m.group(1))
        for m in re.finditer(r"^### 第 (\d+) 次调用 -", text, re.MULTILINE)
    ]
    if not numbers:
        numbers = [
            int(m.group(1))
            for m in re.finditer(r"^### Update (\d+) -", text, re.MULTILINE)
        ]
    return max(numbers, default=0) + 1


def build_initial_document(title: str, date: str, session_id: str, timestamp: str, session_dir: Path) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "- 文档类型: AI 会话技术总结",
            f"- 日期: {date}",
            f"- Session ID: `{session_id}`",
            f"- 首次创建: {timestamp}",
            f"- 最近更新: {timestamp}",
            f"- 输出目录: `{session_dir}`",
            "",
            "## 总览总结",
            "",
            "待补充。",
            "",
            "## 调用时间线",
            "",
        ]
    )


def replace_overview(existing: str, overview: str) -> str:
    existing = strip_internal_markers(existing)
    if not overview:
        return existing
    overview_text = overview.rstrip()
    overview_match = OVERVIEW_HEADING_RE.search(existing)
    timeline_match = TIMELINE_HEADING_RE.search(existing)

    if overview_match and timeline_match and overview_match.end() <= timeline_match.start():
        return (
            existing[: overview_match.end()]
            + "\n\n"
            + overview_text
            + "\n\n"
            + existing[timeline_match.start() :]
        )

    overview_block = "## 总览总结\n\n" + overview_text + "\n\n"
    if timeline_match:
        return existing[: timeline_match.start()] + overview_block + existing[timeline_match.start() :]
    return existing.rstrip() + "\n\n" + overview_block


def append_update(existing: str, update: str, timestamp: str, overview: str) -> str:
    existing = replace_overview(existing, overview)
    number = next_update_number(existing)
    block = f"\n---\n\n### 第 {number} 次调用 - {timestamp}\n\n{update.rstrip()}\n"
    if TIMELINE_HEADING_RE.search(existing):
        return existing.rstrip() + block + "\n"
    return existing.rstrip() + "\n\n## 调用时间线\n" + block + "\n"


def render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def slugify_heading(text: str, index: int) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    if not text:
        text = f"section-{index}"
    return text[:80]


def extract_issue_nav(markdown: str) -> list[tuple[str, str]]:
    nav: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        match = re.match(r"^####\s+问题[:：]\s*(.+?)\s*$", line)
        if match:
            title = match.group(1).strip()
            nav.append((slugify_heading(f"问题-{title}", len(nav) + 1), title))
    return nav


def render_markdown(markdown: str, title: str) -> str:
    body: list[str] = []
    issue_nav = extract_issue_nav(markdown)
    heading_ids: dict[str, str] = {title: anchor for anchor, title in issue_nav}
    in_code = False
    code_lines: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            body.append("</ul>")
            in_ul = False
        if in_ol:
            body.append("</ol>")
            in_ol = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip("\n")

        if line.startswith("```"):
            if in_code:
                body.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_lists()
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            close_lists()
            continue

        if re.fullmatch(r"\s*<!--.*-->\s*", line):
            close_lists()
            continue

        if line.startswith("---") and set(line.strip()) == {"-"}:
            close_lists()
            body.append("<hr>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            close_lists()
            level = len(heading.group(1))
            heading_text = heading.group(2)
            attrs = ""
            issue_match = re.match(r"^问题[:：]\s*(.+?)\s*$", heading_text)
            if level == 4 and issue_match:
                issue_title = issue_match.group(1).strip()
                anchor = heading_ids.get(issue_title) or slugify_heading(f"问题-{issue_title}", len(heading_ids) + 1)
                attrs = f' id="{html.escape(anchor)}"'
            body.append(f"<h{level}{attrs}>{render_inline(heading_text)}</h{level}>")
            continue

        unordered = re.match(r"^\s*[-*]\s+(.+)$", line)
        if unordered:
            if in_ol:
                body.append("</ol>")
                in_ol = False
            if not in_ul:
                body.append("<ul>")
                in_ul = True
            body.append(f"<li>{render_inline(unordered.group(1))}</li>")
            continue

        ordered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if ordered:
            if in_ul:
                body.append("</ul>")
                in_ul = False
            if not in_ol:
                body.append("<ol>")
                in_ol = True
            body.append(f"<li>{render_inline(ordered.group(1))}</li>")
            continue

        if line.startswith(">"):
            close_lists()
            body.append(f"<blockquote>{render_inline(line.lstrip('> '))}</blockquote>")
            continue

        close_lists()
        body.append(f"<p>{render_inline(line)}</p>")

    if in_code:
        body.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    close_lists()

    page_title = html.escape(title)
    if issue_nav:
        nav_items = "\n".join(
            f'      <a href="#{html.escape(anchor)}">{html.escape(label)}</a>'
            for anchor, label in issue_nav
        )
    else:
        nav_items = '      <span class="empty-nav">暂无问题详情</span>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --paper: #ffffff;
      --text: #20242a;
      --muted: #657083;
      --border: #d9dee7;
      --code-bg: #f0f3f7;
      --accent: #1f6feb;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 16px/1.68 -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(210px, 280px) minmax(0, 980px);
      gap: 24px;
      max-width: 1320px;
      margin: 32px auto;
      padding: 0 24px;
      align-items: start;
    }}
    .sidebar {{
      position: sticky;
      top: 24px;
      max-height: calc(100vh - 48px);
      overflow: auto;
      padding: 20px;
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: 0 10px 24px rgba(20, 31, 48, 0.06);
    }}
    .sidebar strong {{
      display: block;
      margin-bottom: 12px;
      font-size: 0.95rem;
      color: #2b3440;
    }}
    .sidebar a {{
      display: block;
      padding: 9px 0;
      color: #24405f;
      text-decoration: none;
      border-top: 1px solid var(--border);
      font-size: 0.92rem;
      line-height: 1.45;
    }}
    .sidebar a:hover {{
      color: var(--accent);
    }}
    .empty-nav {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    main {{
      min-width: 0;
      padding: 36px 42px;
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: 0 12px 32px rgba(20, 31, 48, 0.08);
    }}
    h1, h2, h3, h4, h5, h6 {{
      line-height: 1.28;
      margin: 1.35em 0 0.55em;
    }}
    h1 {{
      margin-top: 0;
      padding-bottom: 0.45em;
      border-bottom: 1px solid var(--border);
      font-size: 2rem;
    }}
    h2 {{ font-size: 1.45rem; }}
    h3 {{ font-size: 1.18rem; color: #2b3440; }}
    h4 {{ font-size: 1rem; color: var(--accent); }}
    h4[id] {{
      scroll-margin-top: 24px;
      padding-top: 0.25em;
      border-top: 1px solid var(--border);
    }}
    p {{ margin: 0.55em 0; }}
    ul, ol {{ padding-left: 1.5em; }}
    li {{ margin: 0.28em 0; }}
    code {{
      padding: 0.1em 0.3em;
      border-radius: 4px;
      background: var(--code-bg);
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 0.92em;
    }}
    pre {{
      overflow-x: auto;
      padding: 14px 16px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--code-bg);
    }}
    pre code {{
      padding: 0;
      background: transparent;
    }}
    blockquote {{
      margin: 1em 0;
      padding: 0.1em 1em;
      color: var(--muted);
      border-left: 4px solid var(--border);
    }}
    hr {{
      border: 0;
      border-top: 1px solid var(--border);
      margin: 1.8em 0;
    }}
    @media (max-width: 900px) {{
      .layout {{
        display: block;
        margin: 0;
        padding: 0;
      }}
      .sidebar {{
        position: static;
        max-height: none;
        border-radius: 0;
        border-left: 0;
        border-right: 0;
        box-shadow: none;
      }}
      main {{
        margin: 0;
        padding: 24px 20px;
        border: 0;
        border-radius: 0;
      }}
      h1 {{ font-size: 1.55rem; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar" aria-label="问题导航">
      <strong>问题导航</strong>
{nav_items}
    </aside>
    <main>
{chr(10).join("    " + part for part in body)}
    </main>
  </div>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="归档根目录，默认 $HOME/文档/AI-Session")
    parser.add_argument("--date", help="会话日期目录，格式 YYYY-MM-DD")
    parser.add_argument("--session-id", default=os.environ.get("CODEX_THREAD_ID", ""), help="会话标识")
    parser.add_argument("--title", default="", help="文档标题；当前 Codex 会话默认使用线程显示标题")
    parser.add_argument("--input", help="本次时间线条目 Markdown 文件；省略时从 stdin 读取")
    parser.add_argument("--overall-file", help="总览总结 Markdown 文件；提供后会替换总览总结区域")
    parser.add_argument("--overall-summary", help="较短的总览总结文本；与 --overall-file 二选一")
    parser.add_argument("--render-only", action="store_true", help="只更新标题/元数据并重新渲染 HTML，不追加时间线")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    current = now_local()
    date = args.date or current.strftime("%Y-%m-%d")
    timestamp = current.strftime("%Y-%m-%d %H:%M:%S %z")
    provided_session_id = args.session_id.strip()
    session_id = provided_session_id or current.strftime("manual-%Y%m%d-%H%M%S")
    thread_title = codex_thread_display_title(session_id)
    if thread_title and not is_range_session(session_id):
        title = thread_title
    else:
        title = args.title.strip() or DEFAULT_TITLE
    update = "" if args.render_only else read_update(args)
    overview = read_overview(args)

    title_slug = sanitize_segment(title, "summary")
    if provided_session_id and is_range_session(session_id):
        session_folder = sanitize_segment(session_id, "session")
    else:
        session_folder = title_slug or sanitize_segment(session_id, "session")
    date_dir = Path(args.root).expanduser() / date
    session_dir = date_dir / session_folder
    legacy_dir = date_dir / sanitize_segment(session_id, "session")
    if (
        provided_session_id
        and not is_range_session(session_id)
        and legacy_dir != session_dir
        and legacy_dir.exists()
        and not session_dir.exists()
    ):
        legacy_dir.rename(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    md_path = session_dir / "summary.md"
    html_path = session_dir / "summary.html"

    if md_path.exists():
        document = md_path.read_text(encoding="utf-8")
        ensure_matching_session(document, session_id, md_path)
    elif args.render_only:
        raise SystemExit(f"summary.md 不存在，无法 render-only: {md_path}")
    else:
        document = build_initial_document(title, date, session_id, timestamp, session_dir)

    document = strip_internal_markers(update_document_header(document, title, timestamp, session_dir))
    if args.render_only:
        document = replace_overview(document, overview)
    else:
        document = append_update(document, update, timestamp, overview)
    md_path.write_text(document, encoding="utf-8")
    html_path.write_text(render_markdown(document, title), encoding="utf-8")

    print(f"summary_md={md_path}")
    print(f"summary_html={html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
