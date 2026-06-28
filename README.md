# weather_digest — 気象ニュースダイジェスト

**🌐 公開サイト: https://masauehr.github.io/weather_digest/**

> 詳しくは [weather-digest.md](./weather-digest.md) を参照。仕様の詳細は [SPEC.md](./SPEC.md) を参照。

## クイックリンク

| | リンク |
|---|---|
| 🌐 公開サイト | https://masauehr.github.io/weather_digest/ |
| 🖥️ Ollama週次まとめ | https://masauehr.github.io/weather_digest/articles/weekly/ |
| ⚡ Haiku週次まとめ | https://masauehr.github.io/weather_digest/articles/haiku_weekly/ |
| 🔬 モデル比較 | https://masauehr.github.io/weather_digest/articles/compare/ |
| 📅 Ollama月次まとめ | https://masauehr.github.io/weather_digest/articles/monthly/ |
| 📅 Haiku月次まとめ | https://masauehr.github.io/weather_digest/articles/haiku_monthly/ |
| ⚙️ 収集・生成仕様 | [SPEC.md](./SPEC.md) |

---

## 概要

気象・気候・防災に関する最新情報を週次・月次で自動収集・要約してGitHub Pages で公開するプロジェクト。
ローカルLLM（Ollama / qwen）と Claude Haiku（Anthropic API）の2モデルで同じ週を記事化し、内容を比較する。

## プロジェクト構成

```
weather_digest/
├── README.md
├── SPEC.md                                    # 情報収集・記事生成の仕様
├── CLAUDE.md                                  # 自動実行時の動作指示
├── articles/
│   ├── weekly/YYYY-MMDD.md                   # Ollama 週次記事（日曜 08:00 自動生成）
│   ├── haiku_weekly/YYYY-MMDD.md             # Haiku 週次記事（日曜 12:00 自動生成）
│   ├── compare/YYYY-MMDD.md                  # モデル比較ページ（12:00以降 自動生成）
│   ├── monthly/YYYY-MM.md                    # Ollama 月次まとめ（第1日曜 08:00 自動生成）
│   ├── haiku_monthly/YYYY-MM.md              # Haiku 月次まとめ（第1日曜 12:00 自動生成）
│   └── topics/YYYY-MM-DD_slug.md             # 深掘りトピックス
└── scripts/
    ├── local_agent.py                         # Ollama エージェント
    ├── haiku_agent.py                         # Claude Haiku エージェント
    ├── generate_compare.py                    # 比較ページ生成
    ├── run_weather_ollama.sh                  # Ollama実行スクリプト（launchd 08:00）
    ├── run_weather_haiku.sh                   # Haiku実行スクリプト（launchd 12:00）
    ├── com.user.weather_digest_ollama.plist   # launchd設定（08:00）
    └── com.user.weather_digest_haiku.plist    # launchd設定（12:00）
```

---

## 最新記事

### 週次まとめ（Ollama / qwen）

- [6/21〜6/28](./articles/weekly/2026-0628.md)
- [6/14〜6/21](./articles/weekly/2026-0621.md)
- [6/7〜6/14](./articles/weekly/2026-0614.md)
- [5/31〜6/7](./articles/weekly/2026-0607.md)
- [5/24〜5/31](./articles/weekly/2026-0531.md)
<!-- 週次記事リンクがここに追加されます -->

### Haiku週次まとめ（Claude Haiku）

- [6/14〜6/21](./articles/haiku_weekly/2026-0621.md)
- [6/7〜6/14](./articles/haiku_weekly/2026-0614.md)
- [5/31〜6/7](./articles/haiku_weekly/2026-0607.md)
- [5/24〜5/31](./articles/haiku_weekly/2026-0531.md)

### Haiku月次まとめ（Claude Haiku）

<!-- articles/haiku_monthly/ のファイルへのリンクがここに追加される -->

### モデル比較（Ollama vs Haiku）

<!-- 比較記事リンクがここに追加されます -->

### 月次まとめ

- [2026年6月](./articles/monthly/2026-06.md)
- [2026年6月](./articles/monthly/2026-06.md)
- [2026年6月](./articles/monthly/2026-06.md)
<!-- 月次記事リンクがここに追加されます -->

### トピックス

<!-- トピックス記事リンクがここに追加されます -->

---

## 自動実行システム

### スケジュール

| タイミング | 内容 |
|---|---|
| 毎週日曜 08:00 JST | Ollama（qwen）が週次記事を自動生成・git push |
| 毎週日曜 12:00 JST | Claude Haiku が同じ週の記事を別ファイルに生成 → 比較ページを自動作成 |
| 毎月第1日曜 08:00 JST | 上記に加えて Ollama 月次まとめも生成 |
| 毎月第1日曜 12:00 JST | 上記に加えて Haiku 月次まとめも生成 |

### 使用モデル

| 実行 | モデル | 種別 |
|---|---|---|
| 08:00 | `qwen3.6:35b-mlx` | Ollama ローカルLLM（デフォルト） |
| 12:00 | `claude-haiku-4-5-20251001` | Anthropic API（Claude Haiku） |

### 手動実行

```bash
# Ollama版（08:00相当）を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_ollama.sh

# Haiku版（12:00相当）を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_haiku.sh

# ログ確認
tail -f ~/projects/weather_digest/weather_digest.log
tail -f ~/projects/weather_digest/weather_digest_haiku.log
```

---

## 収集対象トピック

| カテゴリ | 内容 |
|---|---|
| 🌩️ 顕著な気象現象 | 台風・大雨・猛暑・大雪など今週の注目気象 |
| 🌡️ 気候変動 | 温暖化・IPCC・各国気候政策の最新動向 |
| 🤖 気象AI・技術 | AIによる天気予報・数値予報モデルの進化 |
| 🛡️ 防災情報 | 気象庁の新サービス・防災DX・避難情報改善 |
| 🌐 海外気象動向 | WMO・NOAA・ECMWF からの重要情報 |
