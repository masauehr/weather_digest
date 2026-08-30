# weather_digest — 気象ニュースダイジェスト

**🌐 公開サイト: https://masauehr.github.io/weather_digest/**

> 詳しくは [weather-digest.md](./weather-digest.md) を参照。仕様の詳細は [SPEC.md](./SPEC.md) を参照。

## クイックリンク

| | リンク |
|---|---|
| 🌐 公開サイト | https://masauehr.github.io/weather_digest/ |
| 🖥️ qwen週次まとめ | https://masauehr.github.io/weather_digest/articles/weekly/ |
| 🦉 ornith週次まとめ | https://masauehr.github.io/weather_digest/articles/ornith_weekly/ |
| 🌩️ nemotron週次まとめ | https://masauehr.github.io/weather_digest/articles/nemotron_weekly/ |
| ⚡ Haiku週次まとめ | https://masauehr.github.io/weather_digest/articles/haiku_weekly/ |
| 🔬 モデル比較 | https://masauehr.github.io/weather_digest/articles/compare/ |
| 📅 qwen月次まとめ | https://masauehr.github.io/weather_digest/articles/monthly/ |
| 📅 ornith月次まとめ | https://masauehr.github.io/weather_digest/articles/ornith_monthly/ |
| 📅 nemotron月次まとめ | https://masauehr.github.io/weather_digest/articles/nemotron_monthly/ |
| 📅 Haiku月次まとめ | https://masauehr.github.io/weather_digest/articles/haiku_monthly/ |
| ⚙️ 収集・生成仕様 | [SPEC.md](./SPEC.md) |

---

## 概要

気象・気候・防災に関する最新情報を週次・月次で自動収集・要約してGitHub Pages で公開するプロジェクト。
ローカルLLM 3種（Ollama: qwen3.6 / ornith-1.5 / nemotron-3.5-lightning）と Claude Haiku（Claude Code CLI）の
計4モデルで同じ週を記事化し、Claude Sonnet が評価した比較ページを自動生成する。

## プロジェクト構成

```
weather_digest/
├── README.md
├── SPEC.md                                    # 情報収集・記事生成の仕様
├── CLAUDE.md                                  # 自動実行時の動作指示
├── articles/
│   ├── weekly/YYYY-MMDD.md                   # qwen 週次記事（日曜 08:00 自動生成）
│   ├── ornith_weekly/YYYY-MMDD.md            # ornith 週次記事（日曜 09:30 自動生成）
│   ├── nemotron_weekly/YYYY-MMDD.md          # nemotron 週次記事（日曜 10:30 自動生成）
│   ├── haiku_weekly/YYYY-MMDD.md             # Haiku 週次記事（日曜 12:00 自動生成）
│   ├── compare/YYYY-MMDD.md                  # モデル比較ページ（12:00以降 自動生成）
│   ├── monthly/YYYY-MM.md                    # qwen 月次まとめ（第1日曜 08:00 自動生成）
│   ├── ornith_monthly/YYYY-MM.md             # ornith 月次まとめ（第1日曜 09:30 自動生成）
│   ├── nemotron_monthly/YYYY-MM.md           # nemotron 月次まとめ（第1日曜 10:30 自動生成）
│   ├── haiku_monthly/YYYY-MM.md              # Haiku 月次まとめ（第1日曜 12:00 自動生成）
│   └── topics/YYYY-MM-DD_slug.md             # 深掘りトピックス
└── scripts/
    ├── local_agent.py                          # Ollama エージェント（--slug で qwen/ornith/nemotron 切替）
    ├── haiku_agent.py                          # Claude Haiku エージェント
    ├── generate_compare.py                     # 比較ページ生成（N モデル対応）
    ├── run_weather_ollama.sh                   # qwen実行スクリプト（launchd 08:00）
    ├── run_weather_ornith.sh                   # ornith実行スクリプト（launchd 09:30）
    ├── run_weather_nemotron.sh                 # nemotron実行スクリプト（launchd 10:30）
    ├── run_weather_haiku.sh                    # Haiku実行スクリプト（launchd 12:00）
    ├── com.user.weather_digest_ollama.plist    # launchd設定（08:00）
    ├── com.user.weather_digest_ornith.plist    # launchd設定（09:30）
    ├── com.user.weather_digest_nemotron.plist  # launchd設定（10:30）
    └── com.user.weather_digest_haiku.plist     # launchd設定（12:00）
```

---

## 最新記事

### 週次まとめ（Ollama / qwen）

- [8/23〜8/30](./articles/weekly/2026-0830.md)
- [8/16〜8/23](./articles/weekly/2026-0823.md)
- [8/9〜8/16](./articles/weekly/2026-0816.md)
- [8/2〜8/9](./articles/weekly/2026-0809.md)
- [7/26〜8/2](./articles/weekly/2026-0802.md)
- [7/19〜7/26](./articles/weekly/2026-0726.md)
- [7/12〜7/19](./articles/weekly/2026-0719.md)
- [7/5〜7/12](./articles/weekly/2026-0712.md)
- [6/28〜7/5](./articles/weekly/2026-0705.md)
- [6/21〜6/28](./articles/weekly/2026-0628.md)
- [6/14〜6/21](./articles/weekly/2026-0621.md)
- [6/7〜6/14](./articles/weekly/2026-0614.md)
- [5/31〜6/7](./articles/weekly/2026-0607.md)
- [5/24〜5/31](./articles/weekly/2026-0531.md)
<!-- 週次記事リンクがここに追加されます -->

### ornith週次まとめ（Ollama / ornith-1.5:35b）

一覧は [articles/ornith_weekly/](./articles/ornith_weekly/) を参照（比較ページにも掲載）。

### nemotron週次まとめ（Ollama / nemotron-3.5-lightning:30b-mlx）

一覧は [articles/nemotron_weekly/](./articles/nemotron_weekly/) を参照（比較ページにも掲載）。

### Haiku週次まとめ（Claude Haiku）

- [8/23〜8/30](./articles/haiku_weekly/2026-0830.md)
- [8/9〜8/16](./articles/haiku_weekly/2026-0816.md)
- [8/2〜8/9](./articles/haiku_weekly/2026-0809.md)
- [7/19〜7/26](./articles/haiku_weekly/2026-0726.md)
- [7/12〜7/19](./articles/haiku_weekly/2026-0719.md)
- [6/21〜6/28](./articles/haiku_weekly/2026-0628.md)
- [6/14〜6/21](./articles/haiku_weekly/2026-0621.md)
- [6/7〜6/14](./articles/haiku_weekly/2026-0614.md)
- [5/31〜6/7](./articles/haiku_weekly/2026-0607.md)
- [5/24〜5/31](./articles/haiku_weekly/2026-0531.md)

### Haiku月次まとめ（Claude Haiku）

<!-- articles/haiku_monthly/ のファイルへのリンクがここに追加される -->

### モデル比較（qwen / ornith / nemotron / Haiku）

<!-- 比較記事リンクがここに追加されます -->

### 月次まとめ

- [2026年8月](./articles/monthly/2026-08.md)
- [2026年8月](./articles/monthly/2026-08.md)
- [2026年8月](./articles/monthly/2026-08.md)
- [2026年7月](./articles/monthly/2026-07.md)
- [2026年7月](./articles/monthly/2026-07.md)
- [2026年7月](./articles/monthly/2026-07.md)
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
| 毎週日曜 09:30 JST | Ollama（ornith-1.5）が同じ週の記事を別ファイルに生成 |
| 毎週日曜 10:30 JST | Ollama（nemotron-3.5-lightning）が同じ週の記事を別ファイルに生成 |
| 毎週日曜 12:00 JST | Claude Haiku が同じ週の記事を別ファイルに生成 → 4モデル比較ページを自動作成 |
| 毎月第1日曜 08:00〜10:30 JST | 上記各ローカルLLMが月次まとめも生成 |
| 毎月第1日曜 12:00 JST | 上記に加えて Haiku 月次まとめも生成 |

比較ページは Haiku 完了後に生成され、その時点で存在する記事だけを並べる
（qwen と Haiku は必須、ornith / nemotron はその週の記事があれば追加）。

### 使用モデル

| 実行 | モデル | 種別 |
|---|---|---|
| 08:00 | `qwen3.6:35b-mlx` | Ollama ローカルLLM |
| 09:30 | `ornith-1.5:35b` | Ollama ローカルLLM |
| 10:30 | `nemotron-3.5-lightning:30b-mlx` | Ollama ローカルLLM |
| 12:00 | `claude-haiku-4-5` | Claude Code CLI（Pro/Maxサブスクリプション） |
| 比較評価 | `claude-sonnet-4-6` | Claude Code CLI（Pro/Maxサブスクリプション） |

### 手動実行

```bash
# 各ローカルLLM版を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_ollama.sh    # qwen（08:00相当）
bash ~/projects/weather_digest/scripts/run_weather_ornith.sh    # ornith（09:30相当）
bash ~/projects/weather_digest/scripts/run_weather_nemotron.sh  # nemotron（10:30相当）

# Haiku版（12:00相当）を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_haiku.sh

# ログ確認
tail -f ~/projects/weather_digest/weather_digest.log
tail -f ~/projects/weather_digest/weather_digest_ornith.log
tail -f ~/projects/weather_digest/weather_digest_nemotron.log
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
