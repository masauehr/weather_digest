# CLAUDE.md — weather_digest プロジェクト専用指示

## このプロジェクトについて

気象・気候・防災に関する最新情報を週次・月次でまとめ、GitHub Pages で公開するプロジェクト。

| エンジン | 実行時刻 | スクリプト |
|---|---|---|
| Claude Haiku（Anthropic API） | 毎週月曜 08:00 | `run_weather.sh` → `haiku_agent.py` |

---

## 自動実行時の動作フロー

### Step 1: 日付判定

今日が「月の第1月曜日」かどうかを判定する。

```bash
DAY=$(TZ=Asia/Tokyo date +%d)
if [ "$DAY" -le 7 ]; then
  # 月次モード（月次まとめ + 週次まとめ）
else
  # 週次モードのみ
fi
```

### Step 2: 情報収集（WebSearch / WebFetch）

以下のサイト・キーワードで最新情報を収集する（直近7日間を対象）:

**収集キーワード（WebSearch）**:
- `気象庁 プレスリリース 今週`
- `異常気象 今週 記録`
- `台風 最新情報`
- `大雨 洪水 今週`
- `気候変動 最新ニュース`
- `AI 気象予報 最新`
- `防災 気象情報 新サービス`
- `WMO 世界気象 最新`
- `エルニーニョ ラニーニャ 最新`
- `気象 研究 論文 今週`

**優先確認サイト（WebFetch で直接確認すること）**:
- 気象庁プレスリリース: https://www.jma.go.jp/jma/press/
- WMO ニュース: https://public.wmo.int/en/media/news

### Step 3: 週次記事の生成

ファイル名: `articles/weekly/YYYY-MMDD.md`（MMDD は実行日の月日）

SPEC.md の週次フォーマットに従い記事を生成する。
- 最低5トピック以上を収録（気象庁情報を必ず1件以上含める）
- 各情報源のURLを必ず記載
- 日本語で記述
- 英語タイトルのリンクには日本語訳を併記

### Step 4: 月次記事の生成（第1月曜のみ）

ファイル名: `articles/monthly/YYYY-MM.md`

前月の週次まとめ記事を参照してサマリーを作成する。

### Step 5: README.md の更新

「最新記事」セクションに生成した記事へのリンクを追記する。

### Step 6: git commit & push

```bash
git add articles/ README.md index.md articles/weekly/index.md
git commit -m "YYYY-MMDD 週次まとめを追加"
git push origin main
```

---

## ファイルパス一覧

| 目的 | パス |
|---|---|
| 週次記事 | `articles/weekly/YYYY-MMDD.md` |
| 月次記事 | `articles/monthly/YYYY-MM.md` |
| トピックス | `articles/topics/YYYY-MM-DD_slug.md` |
| README | `README.md` |
| 実行ログ | `weather_digest.log` |
| エージェント | `scripts/haiku_agent.py` |
| ANTHROPIC_API_KEY | `~/.anthropic_env` |
