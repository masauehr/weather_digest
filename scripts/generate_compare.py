#!/opt/anaconda3/bin/python3
"""
generate_compare.py — Ollama記事とHaiku記事を並べた比較ページを生成する

使い方:
  python3 generate_compare.py \
    --week-file 0602 \
    --week-label "5/26〜6/1" \
    --year 2026
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import anthropic

PROJECT_DIR = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))
SONNET_MODEL = "claude-sonnet-4-6"


def log(msg: str) -> None:
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_api_key() -> bool:
    """~/.anthropic_env から ANTHROPIC_API_KEY を読み込む"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    env_file = Path.home() / ".anthropic_env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
                return True
    return False


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


def evaluate_with_sonnet(week_label: str, ollama_content: str, haiku_content: str) -> str:
    """Claude Sonnet で Ollama 記事と Haiku 記事を比較・評価する"""
    if not load_api_key():
        log("WARN: ANTHROPIC_API_KEY が未設定のため Sonnet 評価をスキップします")
        return ""

    log(f"Sonnet 評価を開始: {SONNET_MODEL}")
    client = anthropic.Anthropic()

    system_prompt = (
        "あなたは気象・気候・防災ニュースの専門的な評価者です。\n"
        "同じ週の気象ニュースについて、2つの異なるLLMモデルが生成した記事を比較・評価してください。\n\n"
        "## 評価の観点\n"
        "1. **情報の正確性・信頼性** — 気象庁など公的機関の情報が適切に引用されているか\n"
        "2. **トピックのカバレッジ** — 重要な気象イベント・気候変動・防災情報を網羅しているか\n"
        "3. **各モデルの独自性・強み** — 一方にしかない情報・視点は何か\n"
        "4. **読みやすさ・構成** — 見出し・要約・情報の整理がわかりやすいか\n"
        "5. **総合評価** — 今週はどちらがより有用な記事を書いたか、またその理由\n\n"
        "マークダウン形式で記述してください。各項目は2〜3文程度に簡潔にまとめること。"
    )

    user_message = (
        f"## 評価対象週: {week_label}\n\n"
        "---\n\n"
        "## 【Ollama / qwen3.6:35b-mlx の記事】\n\n"
        f"{ollama_content[:4000]}\n\n"
        "---\n\n"
        "## 【Claude Haiku の記事】\n\n"
        f"{haiku_content[:4000]}\n\n"
        "---\n\n"
        "上記2記事を評価してください。"
    )

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        evaluation = response.content[0].text
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


def update_top_page(
    week_label: str, week_file: str, year: str,
    ollama_content: str, haiku_content: str,
    evaluation: str = "",
) -> None:
    """index.md を最新比較コンテンツ + 過去記事グリッドで完全に書き換える"""
    compare_items = extract_li_items(PROJECT_DIR / "articles/compare/index.md")
    weekly_items  = extract_li_items(PROJECT_DIR / "articles/weekly/index.md")
    haiku_items   = extract_li_items(PROJECT_DIR / "articles/haiku_weekly/index.md")
    monthly_items = extract_li_items(PROJECT_DIR / "articles/monthly/index.md")

    # Liquid の {{ }} は f-string と衝突するので {{ }} にエスケープ
    baseurl = "{{ site.baseurl }}"
    eval_section = _evaluation_html(evaluation)

    index_md = f"""---
layout: compare
title: 気象ニュースダイジェスト
---

<div class="compare-header">
  <h1>🔬 モデル比較（{week_label}）</h1>
  <div class="compare-meta">
    <span class="badge ollama">🖥️ Ollama</span>
    <span style="font-family:monospace;font-size:0.82rem;color:#666">qwen3.6:35b-mlx（日曜 08:00 生成）</span>
    <span style="margin: 0 0.5rem;">vs</span>
    <span class="badge haiku">⚡ Claude</span>
    <span style="font-family:monospace;font-size:0.82rem;color:#666">claude-haiku-4-5（日曜 12:00 生成）</span>
  </div>
</div>

<div class="compare-wrapper">

<div class="compare-panel ollama-panel">
<div class="panel-header-bar">
  <span class="model-badge">🖥️ Ollama</span>
  <span class="model-name">qwen3.6:35b-mlx</span>
</div>
<div class="panel-body" markdown="1">

{ollama_content}

</div>
</div>

<div class="compare-panel haiku-panel">
<div class="panel-header-bar">
  <span class="model-badge">⚡ Claude Haiku</span>
  <span class="model-name">claude-haiku-4-5</span>
</div>
<div class="panel-body" markdown="1">

{haiku_content}

</div>
</div>

</div>
{eval_section}
<div class="past-articles">
<h2>📚 過去の記事</h2>
<div class="past-articles-grid">

<div class="past-col">
<h3>🔬 モデル比較</h3>
<ul class="article-list compact">
{compare_items}
</ul>
<a href="{baseurl}/articles/compare/" class="view-all">すべて見る →</a>
</div>

<div class="past-col">
<h3>🖥️ Ollama週次</h3>
<ul class="article-list compact">
{weekly_items}
</ul>
<a href="{baseurl}/articles/weekly/" class="view-all">すべて見る →</a>
</div>

<div class="past-col">
<h3>⚡ Haiku週次</h3>
<ul class="article-list compact">
{haiku_items}
</ul>
<a href="{baseurl}/articles/haiku_weekly/" class="view-all">すべて見る →</a>
</div>

<div class="past-col">
<h3>📅 月次まとめ</h3>
<ul class="article-list compact">
{monthly_items}
</ul>
<a href="{baseurl}/articles/monthly/" class="view-all">すべて見る →</a>
</div>

</div>
</div>
"""
    (PROJECT_DIR / "index.md").write_text(index_md, encoding="utf-8")
    log(f"index.md をトップ比較ページとして更新: {week_label}")


def generate(week_file: str, week_label: str, year: str, force: bool = False) -> bool:
    ollama_path   = PROJECT_DIR / f"articles/weekly/{year}-{week_file}.md"
    haiku_path    = PROJECT_DIR / f"articles/haiku_weekly/{year}-{week_file}.md"
    compare_path  = PROJECT_DIR / f"articles/compare/{year}-{week_file}.md"
    compare_index = PROJECT_DIR / "articles/compare/index.md"

    if not ollama_path.exists():
        log(f"SKIP: Ollama記事が存在しません: {ollama_path}")
        return False
    if not haiku_path.exists():
        log(f"SKIP: Haiku記事が存在しません: {haiku_path}")
        return False

    ollama_content = strip_front_matter(ollama_path.read_text(encoding="utf-8"))
    haiku_content  = strip_front_matter(haiku_path.read_text(encoding="utf-8"))

    # Sonnet 評価（未生成 or --force 時に実行）
    evaluation = ""
    if not compare_path.exists() or force:
        evaluation = evaluate_with_sonnet(week_label, ollama_content, haiku_content)

    eval_section = _evaluation_html(evaluation)

    # 比較ページ（articles/compare/YYYY-MMDD.md）を生成
    if not compare_path.exists() or force:
        compare_md = f"""---
layout: compare
title: モデル比較（{week_label}）
---

<div class="compare-header">
  <h1>🔬 モデル比較（{week_label}）</h1>
  <div class="compare-meta">
    <span class="badge ollama">🖥️ Ollama</span>
    <span style="font-family:monospace;font-size:0.82rem;color:#666">qwen3.6:35b-mlx（日曜 08:00 生成）</span>
    <span style="margin: 0 0.5rem;">vs</span>
    <span class="badge haiku">⚡ Claude</span>
    <span style="font-family:monospace;font-size:0.82rem;color:#666">claude-haiku-4-5（日曜 12:00 生成）</span>
  </div>
</div>

<div class="compare-wrapper">

<div class="compare-panel ollama-panel">
<div class="panel-header-bar">
  <span class="model-badge">🖥️ Ollama</span>
  <span class="model-name">qwen3.6:35b-mlx</span>
</div>
<div class="panel-body" markdown="1">

{ollama_content}

</div>
</div>

<div class="compare-panel haiku-panel">
<div class="panel-header-bar">
  <span class="model-badge">⚡ Claude Haiku</span>
  <span class="model-name">claude-haiku-4-5</span>
</div>
<div class="panel-body" markdown="1">

{haiku_content}

</div>
</div>

</div>
{eval_section}"""
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
    update_top_page(week_label, week_file, year, ollama_content, haiku_content, evaluation)

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
    parser = argparse.ArgumentParser(description="Ollama vs Haiku 比較ページ生成（Sonnet評価付き）")
    parser.add_argument("--week-file",  required=True, help="MMDD形式（例: 0602）")
    parser.add_argument("--week-label", required=True, help="例: 5/26〜6/1")
    parser.add_argument("--year",       required=True, help="例: 2026")
    parser.add_argument("--force",      action="store_true", help="既存の比較ページを Sonnet 評価付きで再生成する")
    args = parser.parse_args()

    success = generate(args.week_file, args.week_label, args.year, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
