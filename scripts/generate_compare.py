#!/opt/anaconda3/bin/python3
"""
generate_compare.py — 複数モデルの週次記事を並べた比較ページを生成する

【2026-08-28 変更】
2モデル比較（Ollama qwen 対 Claude Haiku）から N モデル比較へ一般化した。
比較対象は ENGINES で定義する。現状:
  - qwen      : Ollama qwen3.6:35b-mlx            （日曜 08:00 / articles/weekly）
  - ornith    : Ollama ornith-1.5:35b             （日曜 09:30 / articles/ornith_weekly）
  - nemotron  : Ollama nemotron-3.5-lightning:30b-mlx（日曜 10:30 / articles/nemotron_weekly）
  - haiku     : Claude Haiku（claude-haiku-4-5）   （日曜 12:00 / articles/haiku_weekly）
最低条件は qwen と haiku の両記事が存在すること。ornith / nemotron は
その週の記事が存在するときだけパネルに追加される（欠けても生成は継続）。

【2026-07-25 変更】
Sonnet 評価は Anthropic API 直叩きではなく、ai_news プロジェクトと同じ
Claude Code CLI（Pro/Maxサブスクリプション）経由。ANTHROPIC_API_KEY は不要。

使い方:
  python3 generate_compare.py \
    --week-file 0602 \
    --week-label "5/26〜6/1" \
    --year 2026 \
    [--force]
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))
SONNET_MODEL = "claude-sonnet-4-6"
CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")

# ------------------------------------------------------------------ #
# 比較エンジン定義（順序 = パネルの並び順）
# ------------------------------------------------------------------ #

ENGINES = [
    {
        "slug": "qwen",
        "weekly_dir": "articles/weekly",
        "archive_index": "articles/weekly/index.md",
        "archive_href": "articles/weekly/",
        "display_name": "Ollama / qwen",
        "model_name": "qwen3.6:35b-mlx",
        "emoji": "🖥️",
        "badge_class": "ollama",
        "panel_class": "ollama-panel",
        "schedule": "日曜 08:00",
        "past_title": "🖥️ qwen週次",
    },
    {
        "slug": "ornith",
        "weekly_dir": "articles/ornith_weekly",
        "archive_index": "articles/ornith_weekly/index.md",
        "archive_href": "articles/ornith_weekly/",
        "display_name": "Ollama / ornith",
        "model_name": "ornith-1.5:35b",
        "emoji": "🦉",
        "badge_class": "ornith",
        "panel_class": "ornith-panel",
        "schedule": "日曜 09:30",
        "past_title": "🦉 ornith週次",
    },
    {
        "slug": "nemotron",
        "weekly_dir": "articles/nemotron_weekly",
        "archive_index": "articles/nemotron_weekly/index.md",
        "archive_href": "articles/nemotron_weekly/",
        "display_name": "Ollama / nemotron",
        "model_name": "nemotron-3.5-lightning:30b-mlx",
        "emoji": "🌩️",
        "badge_class": "nemotron",
        "panel_class": "nemotron-panel",
        "schedule": "日曜 10:30",
        "past_title": "🌩️ nemotron週次",
    },
    {
        "slug": "haiku",
        "weekly_dir": "articles/haiku_weekly",
        "archive_index": "articles/haiku_weekly/index.md",
        "archive_href": "articles/haiku_weekly/",
        "display_name": "Claude Haiku",
        "model_name": "claude-haiku-4-5",
        "emoji": "⚡",
        "badge_class": "haiku",
        "panel_class": "haiku-panel",
        "schedule": "日曜 12:00",
        "past_title": "⚡ Haiku週次",
    },
]

# 比較ページ生成に最低限そろっている必要があるエンジン
REQUIRED_SLUGS = {"qwen", "haiku"}


def log(msg: str) -> None:
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_claude_cli_text(prompt: str, model: str = "sonnet", budget_usd: str = "1.00", timeout_sec: int = 600) -> str:
    """Claude Code CLI（Pro/Maxサブスクリプション）にプロンプトを渡し、応答テキストを返す。
    ANTHROPIC_API_KEY は明示的に除去し、APIクレジットではなくサブスク認証を強制する。"""
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)

    cmd = [
        CLAUDE_BIN,
        "--print",
        "--dangerously-skip-permissions",
        "--model", model,
        "--max-budget-usd", budget_usd,
        "--allowedTools", "",
        "--input-format", "text",
    ]
    result = subprocess.run(
        cmd, input=prompt, text=True, cwd=PROJECT_DIR, env=env,
        capture_output=True, timeout=timeout_sec,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude Code CLI が終了コード {result.returncode} で失敗: {result.stderr[:500]}")
    return result.stdout.strip()


def strip_front_matter(content: str) -> str:
    """Jekyll front matter（--- ... ---）を除去して本文を返す"""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


def extract_li_items(md_path: Path, limit: int = 5) -> str:
    """index.md から <li> エントリを最大 limit 件取得して文字列で返す"""
    if not md_path.exists():
        return ""
    lines = md_path.read_text(encoding="utf-8").split("\n")
    items = [l for l in lines if l.strip().startswith("<li>")]
    return "\n".join(items[:limit])


def insert_li_at_top_of_ul(md_path: Path, new_li: str) -> bool:
    """<ul class="article-list"> の直後に new_li を挿入する（重複チェック付き）"""
    if not md_path.exists():
        return False
    content = md_path.read_text(encoding="utf-8")
    if new_li.strip() in content:
        return False  # 既に存在する場合はスキップ
    lines = content.split("\n")
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


# ------------------------------------------------------------------ #
# HTML ビルダー（比較ページ本文・トップページで共通利用）
# ------------------------------------------------------------------ #

def collect_present(year: str, week_file: str) -> list:
    """その週の記事が存在するエンジンを ENGINES の順で返す（content 付き）"""
    present = []
    for eng in ENGINES:
        path = PROJECT_DIR / eng["weekly_dir"] / f"{year}-{week_file}.md"
        if path.exists():
            content = strip_front_matter(path.read_text(encoding="utf-8"))
            present.append((eng, content))
    return present


def build_compare_header_html(week_label: str, present: list) -> str:
    """比較ヘッダー（タイトル + モデルバッジ行）の HTML"""
    meta_parts = []
    for eng, _ in present:
        meta_parts.append(
            f'    <span class="badge {eng["badge_class"]}">{eng["emoji"]} {eng["display_name"]}</span>\n'
            f'    <span style="font-family:monospace;font-size:0.82rem;color:#666">'
            f'{eng["model_name"]}（{eng["schedule"]} 生成）</span>'
        )
    sep = '\n    <span style="margin:0 0.4rem;color:#999">·</span>\n'
    meta_html = sep.join(meta_parts)
    return (
        '<div class="compare-header">\n'
        f'  <h1>🔬 モデル比較（{week_label}）</h1>\n'
        '  <div class="compare-meta">\n'
        f'{meta_html}\n'
        '  </div>\n'
        '</div>'
    )


def build_panels_html(present: list) -> str:
    """各モデルの記事パネルを並べた <div class="compare-wrapper"> の HTML"""
    panels = []
    for eng, content in present:
        panels.append(
            f'<div class="compare-panel {eng["panel_class"]}">\n'
            '<div class="panel-header-bar">\n'
            f'  <span class="model-badge">{eng["emoji"]} {eng["display_name"]}</span>\n'
            f'  <span class="model-name">{eng["model_name"]}</span>\n'
            '</div>\n'
            '<div class="panel-body" markdown="1">\n\n'
            f'{content}\n\n'
            '</div>\n'
            '</div>'
        )
    return '<div class="compare-wrapper">\n\n' + "\n\n".join(panels) + '\n\n</div>'


def evaluate_with_sonnet(week_label: str, present: list) -> str:
    """Claude Sonnet（Claude Code CLI経由）で各モデルの記事を比較・評価する"""
    log(f"Sonnet 評価を開始（Claude Code CLI方式）: {SONNET_MODEL} / 対象 {len(present)} モデル")

    model_list = "、".join(f'{eng["display_name"]}（{eng["model_name"]}）' for eng, _ in present)
    articles_block = ""
    for eng, content in present:
        articles_block += (
            "\n---\n\n"
            f'## 【{eng["display_name"]}（{eng["model_name"]}）の記事】\n\n'
            f"{content[:3000]}\n"
        )

    prompt = (
        "あなたは気象・気候・防災ニュースの専門的な評価者です。\n"
        f"同じ週の気象ニュースについて、{len(present)}個の異なるLLMモデルが生成した記事を比較・評価してください。\n"
        f"対象モデル: {model_list}\n\n"
        "## 評価の観点\n"
        "1. **情報の正確性・信頼性** — 気象庁など公的機関の情報が適切に引用されているか\n"
        "2. **トピックのカバレッジ** — 重要な気象イベント・気候変動・防災情報を網羅しているか\n"
        "3. **各モデルの独自性・強み** — そのモデルにしかない情報・視点は何か（モデルごとに簡潔に）\n"
        "4. **読みやすさ・構成** — 見出し・要約・情報の整理がわかりやすいか\n"
        "5. **総合評価** — 今週の順位付けと、最も有用な記事を書いたモデルとその理由\n\n"
        "マークダウン形式で記述してください。各項目は簡潔にまとめること。\n\n"
        f"## 評価対象週: {week_label}\n"
        f"{articles_block}\n"
        "---\n\n"
        "上記の記事を評価してください。"
    )

    try:
        evaluation = run_claude_cli_text(prompt, model="sonnet", budget_usd="1.00")
        log("Sonnet 評価完了")
        return evaluation
    except Exception as e:
        log(f"Sonnet 評価エラー: {e}")
        return ""


def _evaluation_html(evaluation: str) -> str:
    """Sonnet 評価セクションの HTML を返す（評価がない場合は空文字）"""
    if not evaluation:
        return ""
    return f"""
<div class="evaluation-section">
<div class="evaluation-header">
  <span class="model-badge">🤖 Sonnet評価</span>
  <span class="model-name">{SONNET_MODEL}</span>
</div>
<div class="evaluation-body" markdown="1">

{evaluation}

</div>
</div>
"""


def _compare_body(week_label: str, present: list, evaluation: str) -> str:
    """比較ページ本文 / トップページで共通の「ヘッダー + パネル + 評価」HTML"""
    return (
        f"{build_compare_header_html(week_label, present)}\n\n"
        f"{build_panels_html(present)}\n"
        f"{_evaluation_html(evaluation)}"
    )


def update_top_page(week_label: str, present: list, evaluation: str) -> None:
    """index.md を最新比較コンテンツ + 過去記事グリッドで完全に書き換える"""
    baseurl = "{{ site.baseurl }}"

    # 過去記事グリッド: モデル比較 + 各エンジン週次 + 月次まとめ
    cols = []
    cols.append(
        '<div class="past-col">\n'
        '<h3>🔬 モデル比較</h3>\n'
        '<ul class="article-list compact">\n'
        f'{extract_li_items(PROJECT_DIR / "articles/compare/index.md")}\n'
        '</ul>\n'
        f'<a href="{baseurl}/articles/compare/" class="view-all">すべて見る →</a>\n'
        '</div>'
    )
    for eng in ENGINES:
        cols.append(
            '<div class="past-col">\n'
            f'<h3>{eng["past_title"]}</h3>\n'
            '<ul class="article-list compact">\n'
            f'{extract_li_items(PROJECT_DIR / eng["archive_index"])}\n'
            '</ul>\n'
            f'<a href="{baseurl}/{eng["archive_href"]}" class="view-all">すべて見る →</a>\n'
            '</div>'
        )
    cols.append(
        '<div class="past-col">\n'
        '<h3>📅 月次まとめ</h3>\n'
        '<ul class="article-list compact">\n'
        f'{extract_li_items(PROJECT_DIR / "articles/monthly/index.md")}\n'
        '</ul>\n'
        f'<a href="{baseurl}/articles/monthly/" class="view-all">すべて見る →</a>\n'
        '</div>'
    )
    past_cols_html = "\n\n".join(cols)

    index_md = f"""---
layout: compare
title: 気象ニュースダイジェスト
---

{_compare_body(week_label, present, evaluation)}
<div class="past-articles">
<h2>📚 過去の記事</h2>
<div class="past-articles-grid">

{past_cols_html}

</div>
</div>
"""
    (PROJECT_DIR / "index.md").write_text(index_md, encoding="utf-8")
    log(f"index.md をトップ比較ページとして更新: {week_label}（{len(present)} モデル）")


def generate(week_file: str, week_label: str, year: str, force: bool = False) -> bool:
    compare_path = PROJECT_DIR / f"articles/compare/{year}-{week_file}.md"
    compare_index = PROJECT_DIR / "articles/compare/index.md"

    present = collect_present(year, week_file)
    present_slugs = {eng["slug"] for eng, _ in present}
    missing_required = REQUIRED_SLUGS - present_slugs
    if missing_required:
        log(f"SKIP: 必須エンジンの記事が未生成: {sorted(missing_required)}")
        return False

    log(f"比較対象: {[eng['slug'] for eng, _ in present]}")

    # Sonnet 評価（未生成 or --force 時に実行）
    evaluation = ""
    if not compare_path.exists() or force:
        evaluation = evaluate_with_sonnet(week_label, present)

    # 比較ページ（articles/compare/YYYY-MMDD.md）を生成
    if not compare_path.exists() or force:
        compare_md = f"""---
layout: compare
title: モデル比較（{week_label}）
---

{_compare_body(week_label, present, evaluation)}"""
        compare_path.parent.mkdir(parents=True, exist_ok=True)
        compare_path.write_text(compare_md, encoding="utf-8")
        log(f"比較ページ生成完了: {compare_path}")
    else:
        log(f"比較ページは既に存在します（スキップ）: {compare_path} （--force で再生成可）")

    # articles/compare/index.md を更新
    date_str = f"{year}-{week_file[:2]}-{week_file[2:]}"
    href = f"articles/compare/{year}-{week_file}"
    li = (
        f'  <li><a href="{{{{ site.baseurl }}}}/{href}">'
        f'{week_label}</a><span class="date">{date_str}</span></li>'
    )
    if insert_li_at_top_of_ul(compare_index, li):
        log("articles/compare/index.md 更新完了")

    # トップページを最新比較コンテンツで完全書き換え
    update_top_page(week_label, present, evaluation)

    # git commit & push
    files = [
        f"articles/compare/{year}-{week_file}.md",
        "articles/compare/index.md",
        "index.md",
    ]
    commit_msg = (
        f"{year}-{week_file} モデル比較ページを追加・トップページを更新\n\n"
        f"Co-Authored-By: generate_compare.py <noreply@local>"
    )
    try:
        for f in files:
            subprocess.run(["git", "add", f], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_DIR, check=True)
        log("git commit & push 完了")
    except subprocess.CalledProcessError as e:
        log(f"git エラー: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="複数モデル比較ページ生成（Sonnet評価付き）")
    parser.add_argument("--week-file",  required=True, help="MMDD形式（例: 0602）")
    parser.add_argument("--week-label", required=True, help="例: 5/26〜6/1")
    parser.add_argument("--year",       required=True, help="例: 2026")
    parser.add_argument("--force",      action="store_true", help="既存の比較ページを Sonnet 評価付きで再生成する")
    args = parser.parse_args()

    success = generate(args.week_file, args.week_label, args.year, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
