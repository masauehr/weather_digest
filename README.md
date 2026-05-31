# weather_digest — 気象ニュースダイジェスト

**🌐 公開サイト: https://masauehr.github.io/weather_digest/**

> 詳しい仕様は [SPEC.md](./SPEC.md) を参照。

## クイックリンク

| | リンク |
|---|---|
| 🌐 公開サイト | https://masauehr.github.io/weather_digest/ |
| 📰 週次まとめ | https://masauehr.github.io/weather_digest/articles/weekly/ |
| 📅 月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/monthly/ |
| 🔬 トピックス | https://masauehr.github.io/weather_digest/articles/topics/ |
| ⚙️ 収集・生成仕様 | [SPEC.md](./SPEC.md) |

---

## 概要

気象・気候・防災に関する最新情報を週次・月次で自動収集・要約してGitHub Pages で公開するプロジェクト。

## プロジェクト構成

```
weather_digest/
├── README.md                          # このファイル（最新記事一覧）
├── SPEC.md                            # 情報収集・記事生成の仕様
├── CLAUDE.md                          # 自動実行時の動作指示
├── articles/
│   ├── weekly/YYYY-MMDD.md           # 週次記事（月曜 08:00 自動生成）
│   ├── monthly/YYYY-MM.md            # 月次まとめ（第1月曜 自動生成）
│   └── topics/YYYY-MM-DD_slug.md     # 深掘りトピックス（手動 or 指示で生成）
└── scripts/
    ├── haiku_agent.py                # Claude Haiku エージェント
    ├── run_weather.sh                # 実行スクリプト（launchd）
    └── com.user.weather_digest.plist # launchd 設定
```

---

## 最新記事

### 週次まとめ

- [5/24〜5/31](./articles/weekly/2026-0531.md)
<!-- 週次記事リンクがここに追加されます -->

### 月次まとめ

<!-- 月次記事リンクがここに追加されます -->

### トピックス

<!-- トピックス記事リンクがここに追加されます -->

---

## 自動実行システム

macOS の launchd が `scripts/run_weather.sh` を呼び出し、
**Claude Haiku（Anthropic API）** が情報収集から記事生成・git push までを自動実行する。

### スケジュール

| タイミング | 内容 |
|---|---|
| 毎週日曜 08:00 JST | Claude Haiku が週次記事を自動生成・git push |
| 毎月第1日曜 08:00 JST | 上記に加えて月次まとめも生成 |

### 手動実行

```bash
# 今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather.sh

# ログ確認
tail -f ~/projects/weather_digest/weather_digest.log
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
