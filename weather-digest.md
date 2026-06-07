# weather_digest — 気象ニュース自動生成システム

気象・気候・防災に関する最新情報を週次・月次で自動収集し、
Markdown記事としてGitHubに公開する自動化システム。

---

## 概要

macOS の launchd から Ollama（ローカルLLM）と Claude Haiku（Anthropic API）を呼び出し、
情報収集 → 記事生成 → git push までを自動化する。  
同じ週のニュースを2モデルで記事化し、Claude Sonnet が評価付き2カラム比較ページを自動生成する。

| タイミング | エンジン | 処理内容 |
|---|---|---|
| 毎週日曜 08:00 | Ollama（qwen3.6:35b-mlx） | 直近7日間の気象ニュースを収集 → 週次記事を生成・push |
| 毎月第1日曜 08:00 | Ollama | 週次記事に加えて月次まとめ記事も生成・push |
| 毎週日曜 12:00 | Claude Haiku（Anthropic API） | 同じ週の記事を別ファイルに生成・push |
| 毎月第1日曜 12:00 | Claude Haiku | 週次記事に加えて Haiku 月次まとめ記事も生成・push |
| 12:00 以降（Haiku完了後） | Claude Sonnet | 両記事を読んで評価 → 評価付き比較ページを生成・push |

> **変更履歴**
> - 2026-05-31: プロジェクト新規作成
> - 2026-06-07: Haiku月次まとめ機能追加、Sonnet評価を比較ページに追加、`--force` オプション追加

---

## 成果物

| ファイル | 内容 | 生成エンジン | 更新頻度 |
|---|---|---|---|
| `articles/weekly/YYYY-MMDD.md` | Ollama 週次記事 | Ollama | 毎週日曜 08:00 |
| `articles/haiku_weekly/YYYY-MMDD.md` | Haiku 週次記事（同じ週を別視点で生成） | Claude Haiku | 毎週日曜 12:00 |
| `articles/compare/YYYY-MMDD.md` | Ollama vs Haiku 比較ページ + Sonnet評価 | generate_compare.py | 毎週日曜 12:00以降 |
| `articles/monthly/YYYY-MM.md` | Ollama 月次まとめ記事 | Ollama | 毎月第1日曜 |
| `articles/haiku_monthly/YYYY-MM.md` | Haiku 月次まとめ記事 | Claude Haiku | 毎月第1日曜 |
| `README.md` | 最新記事一覧（自動更新） | — | 記事生成時 |

GitHub URL: https://github.com/masauehr/weather_digest  
公開サイト: https://masauehr.github.io/weather_digest/

---

## 仕組み（2エンジン並行 + Sonnet評価付き比較ページ自動生成）

### Ollama 実行フロー（08:00）

```
launchd（毎週日曜 08:00）
  ↓
run_weather_ollama.sh が起動
  ↓
実行日分のファイル（articles/weekly/YYYY-MMDD.md）が存在する？
  ├─ Yes → スキップ（Haiku記事があれば比較ページのみ生成して終了）
  └─ No  → local_agent.py を起動（Ollama tool-calling エージェント）
              ↓
            ┌─ search_web()        DuckDuckGo で直近気象ニュースを検索
            ├─ fetch_url()         trafilatura / requests でページ取得
            ├─ write_article()     articles/weekly/ に記事を保存
            ├─ append_to_readme()  README.md にリンクを追加
            ├─ update_index()      index.md（GitHub Pages）を更新
            └─ git_commit_push()   git add / commit / push
              ↓
            Haiku記事が揃っていれば generate_compare.py を呼び出し
              ↓
            第1日曜なら月次記事（articles/monthly/YYYY-MM.md）も生成
```

### Haiku 実行フロー（12:00）

```
launchd（毎週日曜 12:00）
  ↓
run_weather_haiku.sh が起動
  ↓
Haiku記事（articles/haiku_weekly/YYYY-MMDD.md）が存在する？
  ├─ Yes → スキップ（Ollama記事があれば比較ページのみ生成して終了）
  └─ No  → haiku_agent.py を起動（Anthropic API エージェント、mode=weekly）
              ↓
            ┌─ search_web()        DuckDuckGo で直近気象ニュースを検索
            ├─ fetch_url()         trafilatura / requests でページ取得
            ├─ write_article()     articles/haiku_weekly/ に記事を保存
            ├─ append_to_readme()  README.md の Haiku 週次セクションにリンク追加
            ├─ update_index()      index.md の Haiku 週次セクションを更新
            └─ git_commit_push()   git add / commit / push
              ↓
            第1日曜なら haiku_agent.py を再起動（mode=monthly）
              ↓
            articles/haiku_monthly/YYYY-MM.md を生成
              ↓
            Ollama記事が揃っていれば generate_compare.py を呼び出し
```

### 比較ページ生成（generate_compare.py）

```
generate_compare.py
  ↓
articles/weekly/YYYY-MMDD.md（Ollama）と
articles/haiku_weekly/YYYY-MMDD.md（Haiku）の両方が揃っているか確認
  ├─ どちらか欠けている → スキップ
  └─ 両方揃っている    →
        ↓
      Claude Sonnet（claude-sonnet-4-6）が両記事を読んで評価を生成
        ↓
      articles/compare/YYYY-MMDD.md を作成（Sonnet評価セクション付き）
      articles/compare/index.md を更新
      index.md をトップ比較ページとして書き換え（Sonnet評価付き）
      git add / commit / push
```

---

## ファイル構成

```
weather_digest/
├── SPEC.md                                    # 情報収集・記事生成の仕様
├── CLAUDE.md                                  # 自動実行時の動作指示
├── articles/
│   ├── weekly/YYYY-MMDD.md                   # Ollama 週次記事
│   ├── haiku_weekly/YYYY-MMDD.md             # Haiku 週次記事
│   ├── compare/YYYY-MMDD.md                  # モデル比較ページ（Sonnet評価付き）
│   ├── monthly/YYYY-MM.md                    # Ollama 月次まとめ
│   ├── haiku_monthly/YYYY-MM.md              # Haiku 月次まとめ
│   └── topics/YYYY-MM-DD_slug.md             # 深掘りトピックス（手動）
├── _layouts/
│   ├── default.html                           # 記事用レイアウト
│   └── compare.html                           # 比較・評価用レイアウト（Sonnet評価CSS含む）
└── scripts/
    ├── local_agent.py                         # Ollama エージェント
    ├── haiku_agent.py                         # Claude Haiku エージェント（週次・月次対応）
    ├── generate_compare.py                    # 比較ページ生成 + Sonnet評価
    ├── run_weather_ollama.sh                  # Ollama実行スクリプト（launchd）
    ├── run_weather_haiku.sh                   # Haiku実行スクリプト（launchd）
    ├── com.user.weather_digest_ollama.plist   # launchd設定（08:00）
    └── com.user.weather_digest_haiku.plist    # launchd設定（12:00）
```

---

## 収集対象トピック

| カテゴリ | キーワード例 |
|---|---|
| 🌩️ 顕著な気象現象 | 台風・大雨・線状降水帯・特別警報・記録的高温 |
| 🌡️ 気候変動・温暖化 | IPCC・COP・エルニーニョ・ラニーニャ・WMO報告 |
| 🤖 気象AI・技術 | GraphCast・AIFS・Pangu-Weather・数値予報 AI |
| 🛡️ 防災気象情報 | 気象庁新サービス・避難情報・防災DX |
| 🌐 海外気象動向 | WMO・NOAA・ECMWF の最新発表 |

情報源:
- 気象庁プレスリリース: https://www.jma.go.jp/jma/press/
- WMO: https://wmo.int/
- ウェザーニュース: https://weathernews.jp/
- tenki.jp（日本気象協会）: https://tenki.jp/

---

## launchd 設定

### 登録済みジョブ

```
~/Library/LaunchAgents/com.user.weather_digest_ollama.plist  毎週日曜 08:00
~/Library/LaunchAgents/com.user.weather_digest_haiku.plist   毎週日曜 12:00
```

### 登録コマンド

```bash
cp ~/projects/weather_digest/scripts/com.user.weather_digest_ollama.plist ~/Library/LaunchAgents/
cp ~/projects/weather_digest/scripts/com.user.weather_digest_haiku.plist  ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_ollama.plist
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_haiku.plist
```

### 登録確認

```bash
launchctl list | grep weather_digest
# → com.user.weather_digest_ollama   待機中（PID: -）
# → com.user.weather_digest_haiku    待機中（PID: -）
```

---

## 手動実行

```bash
# Ollama版（08:00相当）を今すぐ実行
OLLAMA_MODEL=qwen3.6:35b-mlx bash ~/projects/weather_digest/scripts/run_weather_ollama.sh

# Haiku版（12:00相当）を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_haiku.sh

# 比較ページのみ手動生成（両記事が揃っている場合）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0607 --week-label "5/31〜6/7" --year 2026

# 既存の比較ページをSonnet評価付きで再生成（--force）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0607 --week-label "5/31〜6/7" --year 2026 --force

# ログ確認
tail -f ~/projects/weather_digest/weather_digest.log        # Ollama
tail -f ~/projects/weather_digest/weather_digest_haiku.log  # Haiku
```

---

## 使用モデル

| 役割 | モデル | 種別 |
|---|---|---|
| 週次・月次記事生成（08:00） | `qwen3.6:35b-mlx` | Ollama ローカルLLM |
| 週次・月次記事生成（12:00） | `claude-haiku-4-5-20251001` | Anthropic API（Claude Haiku）|
| 比較ページ評価 | `claude-sonnet-4-6` | Anthropic API（Claude Sonnet）|

Ollama モデルの変更（一時的）:

```bash
OLLAMA_MODEL=qwen3.6:27b-mlx bash ~/projects/weather_digest/scripts/run_weather_ollama.sh
```

---

## GitHub Pages

| ページ | URL |
|---|---|
| トップ（最新比較 + Sonnet評価） | https://masauehr.github.io/weather_digest/ |
| Ollama週次一覧 | https://masauehr.github.io/weather_digest/articles/weekly/ |
| Haiku週次一覧 | https://masauehr.github.io/weather_digest/articles/haiku_weekly/ |
| モデル比較一覧（Sonnet評価付き） | https://masauehr.github.io/weather_digest/articles/compare/ |
| Ollama月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/monthly/ |
| Haiku月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/haiku_monthly/ |

Jekyll テーマ: カスタム（`_layouts/default.html`・`_layouts/compare.html`）

---

## Sonnet評価の仕様

比較ページ生成時（`generate_compare.py`）に `claude-sonnet-4-6` が自動実行される。

### 評価の観点

| 項目 | 内容 |
|---|---|
| 情報の正確性・信頼性 | 公的機関の情報が適切に引用されているか |
| トピックのカバレッジ | 重要な気象イベントを網羅しているか |
| 各モデルの独自性・強み | 一方にしかない情報・視点は何か |
| 読みやすさ・構成 | 見出し・要約・情報の整理がわかりやすいか |
| 総合評価 | 今週はどちらがより有用か、その理由 |

### 評価の再実行（手動・臨時）

比較ページが既に存在する場合は `--force` を付けて再生成する:

```bash
source ~/.anthropic_env
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file MMDD --week-label "M/D〜M/D" --year YYYY --force
```

---

## トラブルシューティング

### Ollamaに接続できない

```bash
ollama serve  # 起動
curl http://localhost:11434/api/tags  # 疎通確認
```

### ANTHROPIC_API_KEY エラー

```bash
# ~/.anthropic_env に以下を記載
ANTHROPIC_API_KEY=sk-ant-...
```

### 記事が生成されない（最大ターン数到達）

`FORCE_WRITE_TURN`（デフォルト14ターン）を超えると記事生成を強制促進する。  
それでも失敗する場合はログを確認:

```bash
tail -100 ~/projects/weather_digest/weather_digest.log
```

### 比較ページが生成されない

両記事が揃っているか確認し、手動生成:

```bash
ls ~/projects/weather_digest/articles/weekly/
ls ~/projects/weather_digest/articles/haiku_weekly/
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file MMDD --week-label "M/D〜M/D" --year YYYY
```

### Sonnet評価だけ再実行したい

```bash
source ~/.anthropic_env
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file MMDD --week-label "M/D〜M/D" --year YYYY --force
```
