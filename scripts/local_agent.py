#!/opt/anaconda3/bin/python3
"""
local_agent.py — Ollama tool-calling エージェントで weather_digest 記事を自動生成する

使い方（run_weather_ollama.sh から呼ばれる）:
  python3 local_agent.py \
    --mode weekly|monthly \
    --week-file 0602 \
    --week-label "5/26〜6/1" \
    --year 2026 \
    --month 06 \
    [--model qwen3.6:35b-mlx]
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from ddgs import DDGS
import trafilatura

PROJECT_DIR = Path(__file__).resolve().parent.parent
OLLAMA_BASE = "http://localhost:11434"
JST = timezone(timedelta(hours=9))
DEFAULT_MODEL = "qwen3.6:35b-mlx"

# ------------------------------------------------------------------ #
# 比較エンジン定義
#   primary=True  … qwen。README・トップ index.md まで更新する（従来どおり）
#   primary=False … 比較用の追加ローカルLLM。自分の記事とアーカイブ一覧だけを
#                    更新し、README・トップ index.md には触れない
#                    （トップ index.md は generate_compare.py が毎回再生成する）
# ------------------------------------------------------------------ #

ENGINES = {
    "qwen": {
        "weekly_dir": "articles/weekly",
        "monthly_dir": "articles/monthly",
        "primary": True,
    },
    "ornith": {
        "weekly_dir": "articles/ornith_weekly",
        "monthly_dir": "articles/ornith_monthly",
        "primary": False,
    },
    "nemotron": {
        "weekly_dir": "articles/nemotron_weekly",
        "monthly_dir": "articles/nemotron_monthly",
        "primary": False,
    },
}

# 実行中のエンジン設定（main() で --slug に応じて差し替える）
ENGINE = {**ENGINES["qwen"], "slug": "qwen"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}

# ------------------------------------------------------------------ #
# ツール定義（Ollama /api/chat の tools パラメータ用）
# ------------------------------------------------------------------ #

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "DuckDuckGo でウェブ検索し、タイトル・URL・スニペットを返す。最新の気象ニュースを調べるときに使う。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（日本語・英語可）"},
                    "max_results": {"type": "integer", "description": "取得件数（省略時 8）", "default": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "指定 URL のページを取得し、メインテキストを返す。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "取得する URL"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_article",
            "description": "新しい記事ファイルを書き込む。既存ファイルが存在する場合はエラーを返す（上書き禁止）。パスは PROJECT_DIR からの相対パス。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "書き込み先（例: articles/weekly/2026-0602.md）"},
                    "content": {"type": "string", "description": "書き込む Markdown 内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "ファイルを読み込んで内容を返す。パスは PROJECT_DIR からの相対パス。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "読み込むファイルのパス"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_to_readme",
            "description": "README.md の週次まとめセクションに週次リンクを追加する。",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_label": {"type": "string", "description": "週次ラベル（例: 5/26〜6/1）"},
                    "week_path": {"type": "string", "description": "週次記事の相対パス（例: ./articles/weekly/2026-0602.md）"},
                    "month_label": {"type": "string", "description": "月次ラベル（例: 2026年6月）。月次モード以外は省略。"},
                    "month_path": {"type": "string", "description": "月次記事の相対パス。月次モード以外は省略。"},
                },
                "required": ["week_label", "week_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_index",
            "description": "GitHub Pages の index.md 記事リストを更新する。append_to_readme の直後に必ず呼ぶこと。",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_label": {"type": "string", "description": "週次ラベル（例: 5/26〜6/1）"},
                    "week_path": {"type": "string", "description": "週次記事の相対パス（例: ./articles/weekly/2026-0602.md）"},
                    "month_label": {"type": "string", "description": "月次ラベル。月次モード以外は省略。"},
                    "month_path": {"type": "string", "description": "月次記事の相対パス。月次モード以外は省略。"},
                },
                "required": ["week_label", "week_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit_push",
            "description": "変更ファイルを git add / commit / push する。記事と README の更新が完了してから呼ぶ。",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "コミット対象ファイルのリスト（PROJECT_DIR からの相対パス）"},
                    "message": {"type": "string", "description": "コミットメッセージ"},
                },
                "required": ["files", "message"],
            },
        },
    },
]

# ------------------------------------------------------------------ #
# ツール実装
# ------------------------------------------------------------------ #

def tool_search_web(query: str, max_results: int = 8) -> str:
    log(f"search_web: {query!r} (max={max_results})")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "検索結果なし"
        lines = []
        for r in results:
            lines.append(
                f"- [{r.get('title','')}]({r.get('href','')})\n"
                f"  {r.get('body','')[:200]}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"search_web エラー: {e}"


def tool_fetch_url(url: str) -> str:
    log(f"fetch_url: {url}")
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_links=True, favor_precision=True)
            if text:
                return text[:6000]
    except Exception:
        pass
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:6000]
    except Exception as e:
        return f"fetch_url エラー: {e}"


JEKYLL_FRONT_MATTER = "---\nlayout: default\n---\n"


def tool_write_article(path: str, content: str) -> str:
    full = PROJECT_DIR / path
    if full.exists():
        return f"エラー: {path} は既に存在します。上書き禁止。"
    full.parent.mkdir(parents=True, exist_ok=True)
    if not content.startswith("---"):
        content = JEKYLL_FRONT_MATTER + content
    full.write_text(content, encoding="utf-8")
    log(f"write_article: {path} ({len(content)} chars)")
    return f"書き込み完了: {path}"


def tool_read_file(path: str) -> str:
    full = PROJECT_DIR / path
    if not full.exists():
        return f"ファイルが存在しません: {path}"
    return full.read_text(encoding="utf-8")


def tool_append_to_readme(
    week_label: str, week_path: str,
    month_label: str = None, month_path: str = None,
) -> str:
    if not ENGINE["primary"]:
        log(f"append_to_readme: secondary エンジン（{ENGINE['slug']}）のためスキップ")
        return (
            "スキップ: このエンジンは README を更新しません。"
            "続けて update_index → git_commit_push を実行してください。"
        )
    readme = PROJECT_DIR / "README.md"
    lines = readme.read_text(encoding="utf-8").split("\n")
    new_week_line = f"- [{week_label}]({week_path})"
    new_month_line = f"- [{month_label}]({month_path})" if month_label else None
    result = []
    i = 0
    weekly_inserted = monthly_inserted = False
    while i < len(lines):
        result.append(lines[i])
        if not weekly_inserted and lines[i].strip() == "### 週次まとめ（Ollama / qwen）":
            if i + 1 < len(lines) and lines[i + 1].strip() == "":
                result.append(lines[i + 1])
                i += 1
            result.append(new_week_line)
            weekly_inserted = True
        if new_month_line and not monthly_inserted and lines[i].strip() == "### 月次まとめ":
            if i + 1 < len(lines) and lines[i + 1].strip() == "":
                result.append(lines[i + 1])
                i += 1
            result.append(new_month_line)
            monthly_inserted = True
        i += 1
    readme.write_text("\n".join(result), encoding="utf-8")
    log(f"append_to_readme: {new_week_line}")
    return f"README 更新完了: {new_week_line}"


def _insert_li_at_top_of_ul(md_path: Path, new_li: str) -> bool:
    if not md_path.exists():
        return False
    lines = md_path.read_text(encoding="utf-8").split("\n")
    result = []
    inserted = False
    for line in lines:
        result.append(line)
        if not inserted and line.strip() == '<ul class="article-list">':
            result.append(new_li)
            inserted = True
    if inserted:
        md_path.write_text("\n".join(result), encoding="utf-8")
    return inserted


def tool_update_index(
    week_label: str, week_path: str,
    month_label: str = None, month_path: str = None,
) -> str:
    # --- secondary エンジン: 自分のアーカイブ一覧だけを更新する ---
    if not ENGINE["primary"]:
        results = []
        w_stem = Path(week_path).stem
        w_year, w_mmdd = w_stem.split("-", 1)
        w_href = f"{ENGINE['weekly_dir']}/{w_year}-{w_mmdd}"
        w_date = f"{w_year}-{w_mmdd[:2]}-{w_mmdd[2:]}"
        week_li = (
            f'  <li><a href="{{{{ site.baseurl }}}}/{w_href}">'
            f'{week_label}</a><span class="date">{w_date}</span></li>'
        )
        if _insert_li_at_top_of_ul(PROJECT_DIR / ENGINE["weekly_dir"] / "index.md", week_li):
            results.append(f"{ENGINE['weekly_dir']}/index.md")

        if month_label and month_path:
            m_stem = Path(month_path).stem
            m_year, m_month = m_stem.split("-", 1)
            m_href = f"{ENGINE['monthly_dir']}/{m_year}-{m_month}"
            month_li = (
                f'  <li><a href="{{{{ site.baseurl }}}}/{m_href}">'
                f'{month_label}</a><span class="date">{m_year}-{m_month}</span></li>'
            )
            if _insert_li_at_top_of_ul(PROJECT_DIR / ENGINE["monthly_dir"] / "index.md", month_li):
                results.append(f"{ENGINE['monthly_dir']}/index.md")

        log(f"update_index (secondary {ENGINE['slug']}): {week_label} → {results}")
        return f"アーカイブ index 更新完了: {', '.join(results) if results else '変更なし'}"

    w_stem = Path(week_path).stem
    w_year, w_mmdd = w_stem.split("-", 1)
    w_href = f"articles/weekly/{w_year}-{w_mmdd}"
    w_date = f"{w_year}-{w_mmdd[:2]}-{w_mmdd[2:]}"
    week_li = (
        f'  <li><a href="{{{{ site.baseurl }}}}/{w_href}">'
        f'{week_label}</a><span class="date">{w_date}</span></li>'
    )

    month_li = None
    if month_label and month_path:
        m_stem = Path(month_path).stem
        m_year, m_month = m_stem.split("-", 1)
        m_href = f"articles/monthly/{m_year}-{m_month}"
        month_li = (
            f'  <li><a href="{{{{ site.baseurl }}}}/{m_href}">'
            f'{month_label}</a><span class="date">{m_year}-{m_month}</span></li>'
        )

    results = []
    top = PROJECT_DIR / "index.md"
    if top.exists():
        lines = top.read_text(encoding="utf-8").split("\n")
        out = []
        in_ollama = in_monthly = False
        ollama_done = monthly_done = False
        for line in lines:
            out.append(line)
            if '<h2 class="section-title">' in line:
                in_ollama = "🖥️ Ollama週次まとめ" in line
                in_monthly = "📅 月次まとめ" in line
            if in_ollama and not ollama_done and line.strip() == '<ul class="article-list">':
                out.append(week_li)
                ollama_done = True
            if month_li and in_monthly and not monthly_done and line.strip() == '<ul class="article-list">':
                out.append(month_li)
                monthly_done = True
        top.write_text("\n".join(out), encoding="utf-8")
        results.append("index.md")

    if _insert_li_at_top_of_ul(PROJECT_DIR / "articles/weekly/index.md", week_li):
        results.append("articles/weekly/index.md")

    if month_li and _insert_li_at_top_of_ul(PROJECT_DIR / "articles/monthly/index.md", month_li):
        results.append("articles/monthly/index.md")

    log(f"update_index: {week_label} → {results}")
    return f"index.md 更新完了: {', '.join(results)}"


def tool_git_commit_push(files: list, message: str) -> str:
    log(f"git_commit_push: {files}")
    try:
        for f in files:
            subprocess.run(["git", "add", f], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_DIR, check=True)
        return "git add / commit / push 完了"
    except subprocess.CalledProcessError as e:
        return f"git エラー: {e}"


TOOL_HANDLERS = {
    "search_web":       lambda a: tool_search_web(**a),
    "fetch_url":        lambda a: tool_fetch_url(**a),
    "write_article":    lambda a: tool_write_article(**a),
    "read_file":        lambda a: tool_read_file(**a),
    "append_to_readme": lambda a: tool_append_to_readme(**a),
    "update_index":     lambda a: tool_update_index(**a),
    "git_commit_push":  lambda a: tool_git_commit_push(**a),
}

# ------------------------------------------------------------------ #
# ロギング
# ------------------------------------------------------------------ #

def log(msg: str) -> None:
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ------------------------------------------------------------------ #
# システムプロンプト
# ------------------------------------------------------------------ #

SEARCH_KEYWORDS_BLOCK = """\
   - 「気象庁 プレスリリース 今週」
   - 「異常気象 今週 記録」
   - 「台風 最新情報」
   - 「大雨 洪水 被害 今週」
   - 「気候変動 温暖化 最新ニュース」
   - 「AI 気象予報 機械学習 最新」
   - 「防災 気象庁 新サービス」
   - 「WMO 世界気象 最新発表」
   - 「エルニーニョ ラニーニャ 最新」
   - 「気象 研究 論文 今週」"""

# --- primary エンジン（qwen）: README・トップ index.md まで更新する ---
SYSTEM_PROMPT_TMPL = """\
あなたは気象ニュースまとめライターです。
以下の手順に従い、ツールを使いながら週次まとめ記事を自動生成してください。

# 基本情報
- 今日: {today}
- 実行モード: {mode}
- 週次ファイルパス: {weekly_dir}/{year}-{week_file}.md
- 週表示ラベル: {week_label}
{monthly_info}

# 作業手順
1. **情報収集** — search_web で以下のキーワードを順番に検索する（各キーワード1回ずつ）
{keywords}

2. **補足取得** — fetch_url で以下のサイトを直接確認する
   - https://www.jma.go.jp/jma/press/
   - https://public.wmo.int/en/media/news

3. **記事生成** — 収集した情報を統合して週次記事を write_article で保存する
   - ファイルパス: {weekly_dir}/{year}-{week_file}.md

4. **README 更新** — append_to_readme で週次リンクを追加する

5. **index.md 更新** — update_index でトップページの記事リストを更新する

{monthly_step}

6. **コミット** — git_commit_push でファイルをコミット・プッシュする
   - {weekly_dir}/{year}-{week_file}.md
   - README.md
   - index.md
   - {weekly_dir}/index.md

# 記事フォーマット
- タイトル行: `# 気象ニュースダイジェスト（{week_label}）`
- 最低 5 トピック以上（気象庁情報を必ず 1 件以上含める）
- 各情報源の URL を必ず記載
- 日本語で記述

# append_to_readme の引数
- week_label: "{week_label}"
- week_path: "./{weekly_dir}/{year}-{week_file}.md"

# update_index の引数
- week_label: "{week_label}"
- week_path: "./{weekly_dir}/{year}-{week_file}.md"

# コミットメッセージ形式
```
{year}-{week_file} 週次まとめを追加（ローカルLLM生成）

Co-Authored-By: {model} via Ollama <noreply@local>
```
"""

# --- secondary エンジン（ornith / nemotron など比較用の追加ローカルLLM）: ---
#   自分の記事と自分のアーカイブ一覧だけを更新する。
#   README・トップ index.md には触れない（比較ページは generate_compare.py が生成）。
SYSTEM_PROMPT_SECONDARY_TMPL = """\
あなたは気象ニュースまとめライターです。
以下の手順に従い、ツールを使いながら週次まとめ記事を自動生成してください。

# 基本情報
- 今日: {today}
- 実行モード: {mode}
- 使用モデル: {model}（モデル比較用の追加ローカルLLM）
- 週次ファイルパス: {weekly_dir}/{year}-{week_file}.md
- 週表示ラベル: {week_label}
{monthly_info}

# 重要な制約
- 触ってよいファイルは自分の記事ファイルと {weekly_dir}/index.md（月次時は {monthly_dir}/index.md）だけです。
- README.md やトップの index.md には**絶対に触れないでください**。append_to_readme は呼ばないこと。
- 比較ページは後で別プロセス（generate_compare.py）が自動生成します。

# 作業手順
1. **情報収集** — search_web で以下のキーワードを順番に検索する（各キーワード1回ずつ）
{keywords}

2. **補足取得** — fetch_url で以下のサイトを直接確認する
   - https://www.jma.go.jp/jma/press/
   - https://public.wmo.int/en/media/news

3. **記事生成** — 収集した情報を統合して週次記事を write_article で保存する
   - ファイルパス: {weekly_dir}/{year}-{week_file}.md

{monthly_step}

4. **アーカイブ更新** — update_index を呼ぶ（自分のアーカイブ一覧だけが更新される）
   - week_label: "{week_label}"
   - week_path: "./{weekly_dir}/{year}-{week_file}.md"

5. **コミット** — git_commit_push で以下をコミット・プッシュする
   - {weekly_dir}/{year}-{week_file}.md
   - {weekly_dir}/index.md
{monthly_commit}

# 記事フォーマット
- タイトル行: `# 気象ニュースダイジェスト（{week_label}）`
- 最低 5 トピック以上（気象庁情報を必ず 1 件以上含める）
- 各情報源の URL を必ず記載
- 日本語で記述

# コミットメッセージ形式
```
{year}-{week_file} {slug} 週次まとめを追加（ローカルLLM生成）

Co-Authored-By: {model} via Ollama <noreply@local>
```
"""


def build_system_prompt(args) -> str:
    today = datetime.now(JST).strftime("%Y-%m-%d")
    weekly_dir = ENGINE["weekly_dir"]
    monthly_dir = ENGINE["monthly_dir"]
    monthly_info = ""
    monthly_step = ""
    monthly_commit = ""
    if args.mode == "monthly":
        monthly_info = f"- 月次ファイルパス: {monthly_dir}/{args.year}-{args.month}.md"
        monthly_step = (
            f"**月次記事生成（週次記事の直後に実施）** — 前月の週次まとめを参照し、"
            f"月次まとめ（{monthly_dir}/{args.year}-{args.month}.md）を write_article で生成する\n"
        )
        monthly_commit = f"   - {monthly_dir}/{args.year}-{args.month}.md\n   - {monthly_dir}/index.md"

    tmpl = SYSTEM_PROMPT_TMPL if ENGINE["primary"] else SYSTEM_PROMPT_SECONDARY_TMPL
    return tmpl.format(
        today=today,
        mode=args.mode,
        year=args.year,
        week_file=args.week_file,
        week_label=args.week_label,
        weekly_dir=weekly_dir,
        monthly_dir=monthly_dir,
        monthly_info=monthly_info,
        monthly_step=monthly_step,
        monthly_commit=monthly_commit,
        keywords=SEARCH_KEYWORDS_BLOCK,
        slug=ENGINE["slug"],
        model=args.model,
    )

# ------------------------------------------------------------------ #
# Ollama チャットループ
# ------------------------------------------------------------------ #

def call_ollama(model: str, messages: list) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": 65536,
            "temperature": 0.3,
            "top_p": 0.9,
        },
    }
    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=600)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        log("ERROR: Ollama タイムアウト（600s）")
        raise
    except requests.exceptions.RequestException as e:
        log(f"ERROR: Ollama 接続エラー: {e}")
        raise


def run_agent(args) -> bool:
    system_prompt = build_system_prompt(args)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "記事生成を開始してください。"},
    ]

    log(f"Ollamaエージェント開始: model={args.model}, mode={args.mode}, week={args.week_file}")

    MAX_TURNS = 40
    LOOP_THRESHOLD = 2
    FORCE_WRITE_TURN = 12

    call_counts: dict = {}
    url_cache: dict = {}
    write_article_called = False
    force_write_prompted = False

    for turn in range(MAX_TURNS):
        log(f"--- ターン {turn + 1}/{MAX_TURNS} ---")

        if turn >= FORCE_WRITE_TURN and not write_article_called and not force_write_prompted:
            log("WARN: 情報収集ターン超過 → write_article を促進")
            post_steps = (
                "append_to_readme → update_index → git_commit_push"
                if ENGINE["primary"]
                else "update_index → git_commit_push"
            )
            messages.append({
                "role": "user",
                "content": (
                    "情報収集は十分です。今すぐ write_article で週次記事を生成してください。"
                    f"生成後、{post_steps} の順で後処理を行ってください。"
                ),
            })
            force_write_prompted = True

        data = call_ollama(args.model, messages)
        msg = data.get("message", {})
        tool_calls = msg.get("tool_calls", [])
        content = msg.get("content") or ""

        if content:
            log(f"モデル応答: {content[:300]}")

        if not tool_calls:
            log("ツール呼び出しなし → 完了")
            return write_article_called

        messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            raw_args = fn.get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    raw_args = {}

            args_key = json.dumps(raw_args, sort_keys=True, ensure_ascii=False)
            call_key = (name, args_key)
            call_counts[call_key] = call_counts.get(call_key, 0) + 1

            if call_counts[call_key] > LOOP_THRESHOLD:
                log(f"LOOP検出: {name} {call_counts[call_key]}回目 → スキップ")
                result = (
                    f"[重複スキップ] {name} の同一引数での呼び出しは {call_counts[call_key]} 回目です。"
                    "write_article ツールで記事を生成してください。"
                )
            elif name == "fetch_url" and raw_args.get("url") in url_cache:
                url = raw_args["url"]
                log(f"CACHE HIT: {url}")
                result = f"[取得済みキャッシュ]\n{url_cache[url][:1000]}\nwrite_article で記事を生成してください。"
            else:
                log(f"ツール呼び出し: {name}({args_key[:120]})")
                handler = TOOL_HANDLERS.get(name)
                if handler:
                    try:
                        result = handler(raw_args)
                    except Exception as e:
                        result = f"ツール実行エラー: {e}"
                else:
                    result = f"未知のツール: {name}"

                if name == "fetch_url" and not str(result).startswith("fetch_url エラー"):
                    url_cache[raw_args.get("url", "")] = str(result)
                if name == "write_article" and "書き込み完了" in str(result):
                    write_article_called = True
                    log("write_article 完了 → 後処理フェーズへ")

            log(f"ツール結果: {str(result)[:300]}")
            messages.append({"role": "tool", "content": str(result)})

            if name == "search_web":
                time.sleep(2)

    log(f"ERROR: 最大ターン数 ({MAX_TURNS}) に達しました")
    return write_article_called

# ------------------------------------------------------------------ #
# エントリポイント
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="weather_digest Ollama エージェント")
    parser.add_argument("--mode",       required=True, choices=["weekly", "monthly"])
    parser.add_argument("--week-file",  required=True, help="MMDD形式（例: 0602）")
    parser.add_argument("--week-label", required=True, help="例: 5/26〜6/1")
    parser.add_argument("--year",       required=True, help="例: 2026")
    parser.add_argument("--month",      required=True, help="例: 06")
    parser.add_argument("--model",      default=DEFAULT_MODEL, help="Ollama モデル名")
    parser.add_argument("--slug",       default="qwen", choices=sorted(ENGINES.keys()),
                        help="比較エンジン識別子（qwen=既存 / ornith・nemotron=追加ローカルLLM）")
    args = parser.parse_args()

    global ENGINE
    ENGINE = {**ENGINES[args.slug], "slug": args.slug}
    log(f"エンジン: slug={args.slug} weekly_dir={ENGINE['weekly_dir']} primary={ENGINE['primary']}")

    try:
        requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5).raise_for_status()
    except Exception as e:
        log(f"ERROR: Ollama に接続できません: {e}")
        sys.exit(1)

    success = run_agent(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
