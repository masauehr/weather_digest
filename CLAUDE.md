# CLAUDE.md — weather_digest プロジェクト専用指示

## このプロジェクトについて

気象・気候・防災に関する最新情報を週次・月次でまとめ、GitHub Pages で公開するプロジェクト。
ローカルLLM 3種（Ollama: qwen3.6 / ornith-1.5 / nemotron-3.5-lightning）と Claude Haiku の
計4モデルで同じ週を記事化し、Claude Sonnet が評価した比較ページを自動生成する。

【2026-07-25 変更】Haiku・Sonnet評価とも Anthropic API（従量課金）ではなく、
Claude Code CLI（Pro/Maxサブスクリプション経由）で実行する方式に変更した（ai_news プロジェクトと同じ方式）。
ANTHROPIC_API_KEY は不要になった。

【2026-08-28 変更】比較対象にローカルLLM 2種（ornith-1.5:35b / nemotron-3.5-lightning:30b-mlx）を追加。
`local_agent.py` は `--slug`（qwen / ornith / nemotron）でエンジンを切り替える。
ornith / nemotron は「secondary エンジン」で、README・トップ index.md は更新せず
自分のアーカイブ一覧（`articles/<slug>_weekly/index.md`）だけを更新する。
`generate_compare.py` は qwen と Haiku を必須とし、存在する記事だけを N 枚のパネルに並べる。

| エンジン | 実行時刻 | スクリプト | 保存先 |
|---|---|---|---|
| Ollama（qwen3.6:35b-mlx） | 毎週日曜 08:00 | `run_weather_ollama.sh` → `local_agent.py --slug qwen` | `articles/weekly/` |
| Ollama（ornith-1.5:35b） | 毎週日曜 09:30 | `run_weather_ornith.sh` → `local_agent.py --slug ornith` | `articles/ornith_weekly/` |
| Ollama（nemotron-3.5-lightning:30b-mlx） | 毎週日曜 10:30 | `run_weather_nemotron.sh` → `local_agent.py --slug nemotron` | `articles/nemotron_weekly/` |
| Claude Haiku（Claude Code CLI） | 毎週日曜 12:00 | `run_weather_haiku.sh` → `haiku_agent.py` | `articles/haiku_weekly/` |
| 各ローカルLLM 月次 | 毎月第1日曜 08:00〜10:30 | 上記各 run スクリプト（monthly モード） | `articles/<slug>_monthly/` |
| Haiku 月次 | 毎月第1日曜 12:00 | `run_weather_haiku.sh` → `haiku_agent.py` | `articles/haiku_monthly/` |
| 比較ページ生成＋Sonnet評価（Claude Code CLI） | 12:00 以降（Haiku完了後） | `generate_compare.py` | `articles/compare/` |

---

## ファイルパス一覧

| 目的 | パス |
|---|---|
| qwen 週次記事 | `articles/weekly/YYYY-MMDD.md` |
| ornith 週次記事 | `articles/ornith_weekly/YYYY-MMDD.md` |
| nemotron 週次記事 | `articles/nemotron_weekly/YYYY-MMDD.md` |
| Haiku 週次記事 | `articles/haiku_weekly/YYYY-MMDD.md` |
| 比較ページ（Sonnet評価付き） | `articles/compare/YYYY-MMDD.md` |
| qwen 月次記事 | `articles/monthly/YYYY-MM.md` |
| ornith 月次記事 | `articles/ornith_monthly/YYYY-MM.md` |
| nemotron 月次記事 | `articles/nemotron_monthly/YYYY-MM.md` |
| Haiku 月次記事 | `articles/haiku_monthly/YYYY-MM.md` |
| トピックス | `articles/topics/YYYY-MM-DD_slug.md` |
| qwen ログ | `weather_digest.log` |
| ornith ログ | `weather_digest_ornith.log` |
| nemotron ログ | `weather_digest_nemotron.log` |
| Haiku ログ | `weather_digest_haiku.log` |
| Claude Code CLI | `~/.local/bin/claude`（Haiku・Sonnet評価とも Pro/Max サブスクリプション経由） |

---

## 手動実行コマンド

```bash
# 各ローカルLLM版
bash ~/projects/weather_digest/scripts/run_weather_ollama.sh    # qwen（08:00相当）
bash ~/projects/weather_digest/scripts/run_weather_ornith.sh    # ornith（09:30相当）
bash ~/projects/weather_digest/scripts/run_weather_nemotron.sh  # nemotron（10:30相当）

# Haiku版（12:00相当）
bash ~/projects/weather_digest/scripts/run_weather_haiku.sh

# 比較ページのみ手動生成（qwen と Haiku の記事が揃っている場合。ornith / nemotron はあれば追加される）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0607 --week-label "6/1〜6/7" --year 2026

# 既存の比較ページをSonnet評価付きで再生成（--force）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0607 --week-label "6/1〜6/7" --year 2026 --force
```

## launchd 登録

```bash
cp ~/projects/weather_digest/scripts/com.user.weather_digest_ollama.plist   ~/Library/LaunchAgents/
cp ~/projects/weather_digest/scripts/com.user.weather_digest_ornith.plist   ~/Library/LaunchAgents/
cp ~/projects/weather_digest/scripts/com.user.weather_digest_nemotron.plist ~/Library/LaunchAgents/
cp ~/projects/weather_digest/scripts/com.user.weather_digest_haiku.plist    ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_ollama.plist
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_ornith.plist
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_nemotron.plist
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_haiku.plist
```
