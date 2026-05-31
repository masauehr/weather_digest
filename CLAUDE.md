# CLAUDE.md — weather_digest プロジェクト専用指示

## このプロジェクトについて

気象・気候・防災に関する最新情報を週次・月次でまとめ、GitHub Pages で公開するプロジェクト。
ローカルLLM（Ollama / qwen）と Claude Haiku の2モデルで同じ週を記事化し、比較ページを自動生成する。

| エンジン | 実行時刻 | スクリプト | 保存先 |
|---|---|---|---|
| Ollama（qwen3.6:35b-mlx） | 毎週日曜 08:00 | `run_weather_ollama.sh` → `local_agent.py` | `articles/weekly/` |
| Claude Haiku（Anthropic API） | 毎週日曜 12:00 | `run_weather_haiku.sh` → `haiku_agent.py` | `articles/haiku_weekly/` |
| 比較ページ生成 | 12:00 以降（Haiku完了後） | `generate_compare.py` | `articles/compare/` |

---

## ファイルパス一覧

| 目的 | パス |
|---|---|
| Ollama 週次記事 | `articles/weekly/YYYY-MMDD.md` |
| Haiku 週次記事 | `articles/haiku_weekly/YYYY-MMDD.md` |
| 比較ページ | `articles/compare/YYYY-MMDD.md` |
| 月次記事 | `articles/monthly/YYYY-MM.md` |
| トピックス | `articles/topics/YYYY-MM-DD_slug.md` |
| Ollama ログ | `weather_digest.log` |
| Haiku ログ | `weather_digest_haiku.log` |
| ANTHROPIC_API_KEY | `~/.anthropic_env` |

---

## 手動実行コマンド

```bash
# Ollama版（08:00相当）
bash ~/projects/weather_digest/scripts/run_weather_ollama.sh

# Haiku版（12:00相当）
bash ~/projects/weather_digest/scripts/run_weather_haiku.sh

# 比較ページのみ手動生成（両記事が揃っている場合）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0602 --week-label "5/26〜6/1" --year 2026
```

## launchd 登録

```bash
cp ~/projects/weather_digest/scripts/com.user.weather_digest_ollama.plist ~/Library/LaunchAgents/
cp ~/projects/weather_digest/scripts/com.user.weather_digest_haiku.plist  ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_ollama.plist
launchctl load ~/Library/LaunchAgents/com.user.weather_digest_haiku.plist
```
