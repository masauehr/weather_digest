# weather_digest — 気象ニュース自動生成システム

気象・気候・防災に関する最新情報を週次・月次で自動収集し、
Markdown記事としてGitHubに公開する自動化システム。

---

## 概要

macOS の launchd から Ollama（ローカルLLM 3種）と Claude Haiku（Claude Code CLI 経由）を呼び出し、
情報収集 → 記事生成 → git push までを自動化する。  
同じ週のニュースを計4モデルで記事化し、Claude Sonnet が評価付きの N カラム比較ページを自動生成する。

| タイミング | エンジン | 処理内容 |
|---|---|---|
| 毎週日曜 08:00 | Ollama（qwen3.6:35b-mlx） | 直近7日間の気象ニュースを収集 → 週次記事を生成・push |
| 毎週日曜 09:30 | Ollama（ornith-1.5:35b） | 同じ週の記事を別ファイルに生成・push |
| 毎週日曜 10:30 | Ollama（nemotron-3.5-lightning:30b-mlx） | 同じ週の記事を別ファイルに生成・push |
| 毎週日曜 12:00 | Claude Haiku（Claude Code CLI） | 同じ週の記事を別ファイルに生成・push |
| 毎月第1日曜 08:00〜12:00 | 上記各エンジン | 週次記事に加えて月次まとめ記事も生成・push |
| 12:00 以降（Haiku完了後） | Claude Sonnet（Claude Code CLI） | 揃っている記事を読んで評価 → 評価付き比較ページを生成・push |

> **変更履歴**
> - 2026-05-31: プロジェクト新規作成
> - 2026-06-07: Haiku月次まとめ機能追加、Sonnet評価を比較ページに追加、`--force` オプション追加
> - 2026-07-25: Haiku・Sonnet評価を Anthropic API から Claude Code CLI（Pro/Maxサブスクリプション経由）に変更。APIクレジット残高切れによる自動実行停止を解消（ai_news プロジェクトと同じ方式）。ANTHROPIC_API_KEY が不要に
>   - 経緯: 2026-07-19（日）12:00 の自動実行が `anthropic.BadRequestError`（`Your credit balance is too low`）で2回リトライとも失敗し、Haiku週次記事・比較ページが未生成のまま放置されていた（Ollama版は正常終了）
>   - 対応: 上記方式変更後、2026-07-25 に `articles/haiku_weekly/2026-0719.md`（commit `fc2c7b2`）と `articles/compare/2026-0719.md`（commit `0a9e67c`）を手動バックフィル生成し、以降の自動実行も新方式に統一した
> - 2026-08-28: 比較対象にローカルLLM 2種（`ornith-1.5:35b` / `nemotron-3.5-lightning:30b-mlx`）を追加し、2モデル比較 → 4モデル比較に拡張
>   - `local_agent.py` に `--slug`（qwen / ornith / nemotron）を追加。ornith / nemotron は「secondary エンジン」で、README・トップ index.md は更新せず `articles/<slug>_weekly/index.md` のみ更新する
>   - `run_weather_ornith.sh`（09:30）・`run_weather_nemotron.sh`（10:30）と対応 plist を新規追加。ログは `weather_digest_<slug>.log`
>   - `generate_compare.py` を N モデル対応に一般化（`ENGINES` リストで定義、qwen と Haiku を必須、他は記事があれば追加）

---

## 成果物

| ファイル | 内容 | 生成エンジン | 更新頻度 |
|---|---|---|---|
| `articles/weekly/YYYY-MMDD.md` | qwen 週次記事 | Ollama qwen3.6 | 毎週日曜 08:00 |
| `articles/ornith_weekly/YYYY-MMDD.md` | ornith 週次記事（同じ週を別視点で生成） | Ollama ornith-1.5 | 毎週日曜 09:30 |
| `articles/nemotron_weekly/YYYY-MMDD.md` | nemotron 週次記事（同じ週を別視点で生成） | Ollama nemotron-3.5-lightning | 毎週日曜 10:30 |
| `articles/haiku_weekly/YYYY-MMDD.md` | Haiku 週次記事（同じ週を別視点で生成） | Claude Haiku | 毎週日曜 12:00 |
| `articles/compare/YYYY-MMDD.md` | 4モデル比較ページ + Sonnet評価 | generate_compare.py | 毎週日曜 12:00以降 |
| `articles/monthly/YYYY-MM.md` ほか `<slug>_monthly/` | 各エンジンの月次まとめ記事 | 各エンジン | 毎月第1日曜 |
| `articles/haiku_monthly/YYYY-MM.md` | Haiku 月次まとめ記事 | Claude Haiku | 毎月第1日曜 |
| `README.md` | 最新記事一覧（qwen / Haiku 分を自動更新） | — | 記事生成時 |

GitHub URL: https://github.com/masauehr/weather_digest  
公開サイト: https://masauehr.github.io/weather_digest/

---

## 仕組み（4エンジン並行 + Sonnet評価付き比較ページ自動生成）

### エンジン種別

| slug | モデル | 時刻 | 種別 | README / トップ index.md |
|---|---|---|---|---|
| `qwen` | qwen3.6:35b-mlx | 08:00 | primary | 更新する（従来どおり） |
| `ornith` | ornith-1.5:35b | 09:30 | secondary | 触らない（`articles/ornith_weekly/index.md` のみ更新） |
| `nemotron` | nemotron-3.5-lightning:30b-mlx | 10:30 | secondary | 触らない（`articles/nemotron_weekly/index.md` のみ更新） |
| `haiku` | claude-haiku-4-5 | 12:00 | primary | 更新する（従来どおり） |

secondary エンジンは `run_weather_<slug>.sh` → `local_agent.py --slug <slug>` で動く。
トップページ（`index.md`）は毎回 `generate_compare.py` が全置換するため、secondary は触らない。

### qwen 実行フロー（08:00）

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

### ornith / nemotron 実行フロー（09:30 / 10:30）

```
launchd（毎週日曜 09:30 / 10:30）
  ↓
run_weather_ornith.sh / run_weather_nemotron.sh が起動
  ↓
当該slugの週次記事（articles/<slug>_weekly/YYYY-MMDD.md）が存在する？
  ├─ Yes → スキップ
  └─ No  → local_agent.py --slug <slug> を起動（secondary モード）
              ↓
            ┌─ search_web() / fetch_url()   qwen と同じ情報収集
            ├─ write_article()              articles/<slug>_weekly/ に記事を保存
            ├─ update_index()               articles/<slug>_weekly/index.md のみ更新
            │                               （README・トップ index.md には触れない）
            └─ git_commit_push()            記事 + アーカイブ index を push
              ↓
            第1日曜なら月次記事（articles/<slug>_monthly/YYYY-MM.md）も生成
              ↓
            比較ページは生成しない（Haiku完了後に generate_compare.py がまとめて生成）
```

### Haiku 実行フロー（12:00）

```
launchd（毎週日曜 12:00）
  ↓
run_weather_haiku.sh が起動
  ↓
Haiku記事（articles/haiku_weekly/YYYY-MMDD.md）が存在する？
  ├─ Yes → スキップ（Ollama記事があれば比較ページのみ生成して終了）
  └─ No  → haiku_agent.py を起動（mode=weekly）
              ↓
            Claude Code CLI（Pro/Maxサブスクリプション、ANTHROPIC_API_KEYは明示的に除去）を
            subprocess 起動し、WebSearch/WebFetch/Write/Read のみ許可した状態で
            articles/haiku_weekly/ に記事を1本だけ書かせる
              ↓
            CLI終了後、haiku_agent.py（Python側）が決定論的に後処理:
            ┌─ append_to_readme()  README.md の Haiku 週次セクションにリンク追加
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
ENGINES（qwen / ornith / nemotron / haiku）のうち
articles/<weekly_dir>/YYYY-MMDD.md が存在するものを収集
  ├─ qwen または haiku が欠けている → スキップ
  └─ qwen と haiku が揃っている     →
        ↓
      Claude Sonnet（claude-sonnet-4-6）が揃っている記事（2〜4本）を読んで評価を生成
        ↓
      articles/compare/YYYY-MMDD.md を作成（N枚のパネル + Sonnet評価セクション）
      articles/compare/index.md を更新
      index.md をトップ比較ページとして書き換え（N枚のパネル + 過去記事グリッド）
      git add / commit / push
```

> ornith / nemotron の記事がその週に無ければ、その分のパネルは省略されて生成は続行する。

---

## ファイル構成

```
weather_digest/
├── SPEC.md                                    # 情報収集・記事生成の仕様
├── CLAUDE.md                                  # 自動実行時の動作指示
├── articles/
│   ├── weekly/YYYY-MMDD.md                   # qwen 週次記事
│   ├── ornith_weekly/YYYY-MMDD.md            # ornith 週次記事
│   ├── nemotron_weekly/YYYY-MMDD.md          # nemotron 週次記事
│   ├── haiku_weekly/YYYY-MMDD.md             # Haiku 週次記事
│   ├── compare/YYYY-MMDD.md                  # モデル比較ページ（Sonnet評価付き）
│   ├── monthly/YYYY-MM.md                    # qwen 月次まとめ
│   ├── ornith_monthly/YYYY-MM.md             # ornith 月次まとめ
│   ├── nemotron_monthly/YYYY-MM.md           # nemotron 月次まとめ
│   ├── haiku_monthly/YYYY-MM.md              # Haiku 月次まとめ
│   └── topics/YYYY-MM-DD_slug.md             # 深掘りトピックス（手動）
├── _layouts/
│   ├── default.html                           # 記事用レイアウト
│   └── compare.html                           # 比較・評価用レイアウト（各モデル色・Sonnet評価CSS含む）
└── scripts/
    ├── local_agent.py                          # Ollama エージェント（--slug で qwen/ornith/nemotron 切替）
    ├── haiku_agent.py                          # Claude Haiku エージェント（週次・月次対応）
    ├── generate_compare.py                     # 比較ページ生成 + Sonnet評価（N モデル対応）
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
~/Library/LaunchAgents/com.user.weather_digest_ollama.plist    毎週日曜 08:00
~/Library/LaunchAgents/com.user.weather_digest_ornith.plist    毎週日曜 09:30
~/Library/LaunchAgents/com.user.weather_digest_nemotron.plist  毎週日曜 10:30
~/Library/LaunchAgents/com.user.weather_digest_haiku.plist     毎週日曜 12:00
```

### 登録コマンド

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

### 登録確認

```bash
launchctl list | grep weather_digest
# → com.user.weather_digest_ollama     待機中（PID: -）
# → com.user.weather_digest_ornith     待機中（PID: -）
# → com.user.weather_digest_nemotron   待機中（PID: -）
# → com.user.weather_digest_haiku      待機中（PID: -）
```

---

## 手動実行

```bash
# 各ローカルLLM版を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_ollama.sh    # qwen（08:00相当）
bash ~/projects/weather_digest/scripts/run_weather_ornith.sh    # ornith（09:30相当）
bash ~/projects/weather_digest/scripts/run_weather_nemotron.sh  # nemotron（10:30相当）

# Haiku版（12:00相当）を今すぐ実行
bash ~/projects/weather_digest/scripts/run_weather_haiku.sh

# 比較ページのみ手動生成（qwen と Haiku が揃っていれば実行可。ornith / nemotron はあれば追加）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0607 --week-label "5/31〜6/7" --year 2026

# 既存の比較ページをSonnet評価付きで再生成（--force）
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file 0607 --week-label "5/31〜6/7" --year 2026 --force

# ログ確認
tail -f ~/projects/weather_digest/weather_digest.log           # qwen
tail -f ~/projects/weather_digest/weather_digest_ornith.log    # ornith
tail -f ~/projects/weather_digest/weather_digest_nemotron.log  # nemotron
tail -f ~/projects/weather_digest/weather_digest_haiku.log     # Haiku
```

---

## 使用モデル

| 役割 | モデル | 種別 |
|---|---|---|
| 週次・月次記事生成（08:00） | `qwen3.6:35b-mlx` | Ollama ローカルLLM |
| 週次・月次記事生成（09:30） | `ornith-1.5:35b` | Ollama ローカルLLM |
| 週次・月次記事生成（10:30） | `nemotron-3.5-lightning:30b-mlx` | Ollama ローカルLLM |
| 週次・月次記事生成（12:00） | `haiku`（Claude Haiku 4.5） | Claude Code CLI（Pro/Maxサブスクリプション）|
| 比較ページ評価 | `sonnet`（Claude Sonnet 4.6） | Claude Code CLI（Pro/Maxサブスクリプション）|

Ollama モデルの変更（一時的）: 各 run スクリプトは `OLLAMA_MODEL` 環境変数でモデルを上書きできる。

```bash
OLLAMA_MODEL=qwen3.6:27b-mlx bash ~/projects/weather_digest/scripts/run_weather_ollama.sh
OLLAMA_MODEL=nemotron-3.5-lightning:30b bash ~/projects/weather_digest/scripts/run_weather_nemotron.sh
```

比較対象エンジンの追加・変更は `local_agent.py` の `ENGINES` と
`generate_compare.py` の `ENGINES` リスト、および対応する run スクリプト・plist を編集する。

---

## 追加ローカルLLM 2種の選定根拠（2026-08-28）

`ornith-1.5:35b` と `nemotron-3.5-lightning:30b-mlx` を比較対象に追加したのは、
別プロジェクト local_agent の実測比較「ローカルLLM実測比較」（2026-08-26、
<https://masauehr.github.io/local_agent/>）で両モデルが Ollama の tool-calling エージェントとして
**ファイル作成〜git push まで完走できる**ことを確認済みだったため。同記事からの引用:

| 指標（local_agent の計測） | qwen3.6 | ornith-1.5:35b | nemotron-3.5-lightning:30b-mlx |
|---|---|---|---|
| コード生成 平均時間 | 88.9秒 | **26.1秒（最速、qwen3.6の約3倍速）** | 80.4秒 |
| コード生成 PASS率 | — | 3/3 | 3/3 |
| ツール呼び出しエージェント 完走時間 | — | **158.5秒（最速）** | 291.5秒 |
| エージェントタスク | — | PASS（8ターンで完走） | PASS（8ターンで完走） |
| 総括での位置付け | 基準 | 「生成速度・エージェント安定性ともに最有力」 | 「実績重視・手堅い選択肢」 |

> local_agent 記事の要点: 「**コード生成単体の比較と、エージェントとしての比較は別物**」。
> `nemotron` は「出力にコードブロック二重ネストの癖がある点だけ後処理側で要注意」と明記されている。
> なお、当マニュアル既出の `local-llm-agent.md`（2026-08-16 検証）では
> `nemotron-3.5-lightning:30b-mlx` はプリフィル約850〜1,080 tok/s と高速な一方、
> デコード側で5分タイムアウトが頻発する、との記録もある。

### weather_digest での先行テスト実行（2026-08-28、週 `0828`）

launchd の初回稼働（日曜）を待たず、`run_weather_ornith.sh` / `run_weather_nemotron.sh` を手動実行して
本パイプラインでの挙動を確認した。

| モデル | 生成記事 | サイズ | トピック数 | 所要（ターン数） | 結果 |
|---|---|---|---|---|---|
| ornith-1.5:35b | `articles/ornith_weekly/2026-0828.md` | 約9.6 KB | 7 | 約2分（12ターン） | 記事生成〜push まで完走 |
| nemotron-3.5-lightning:30b-mlx | `articles/nemotron_weekly/2026-0828.md` | 約4.0 KB | 8 | 約3分（16ターン） | 記事生成〜push まで完走 |

- どちらも secondary エンジンとして README・トップ `index.md` を触らず、自分のアーカイブ一覧のみ更新することを確認。
- `nemotron` は local_agent の所見どおり情報量が少なめで、出典 URL に実在しない形式のもの（`https://news.web.nhk/...` など）が混じっていた。これは比較ページ＋Sonnet 評価で可視化される想定。
- 懸念された `nemotron` のデコード5分タイムアウトは、この2回の実行では発生せず完走した。

---

## GitHub Pages

| ページ | URL |
|---|---|
| トップ（最新比較 + Sonnet評価） | https://masauehr.github.io/weather_digest/ |
| qwen週次一覧 | https://masauehr.github.io/weather_digest/articles/weekly/ |
| ornith週次一覧 | https://masauehr.github.io/weather_digest/articles/ornith_weekly/ |
| nemotron週次一覧 | https://masauehr.github.io/weather_digest/articles/nemotron_weekly/ |
| Haiku週次一覧 | https://masauehr.github.io/weather_digest/articles/haiku_weekly/ |
| モデル比較一覧（Sonnet評価付き） | https://masauehr.github.io/weather_digest/articles/compare/ |
| qwen月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/monthly/ |
| ornith月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/ornith_monthly/ |
| nemotron月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/nemotron_monthly/ |
| Haiku月次まとめ一覧 | https://masauehr.github.io/weather_digest/articles/haiku_monthly/ |

Jekyll テーマ: カスタム（`_layouts/default.html`・`_layouts/compare.html`）

---

## Sonnet評価の仕様

比較ページ生成時（`generate_compare.py`）に Claude Sonnet（Claude Code CLI経由、`--model sonnet`）が自動実行される。

### 評価の観点

| 項目 | 内容 |
|---|---|
| 情報の正確性・信頼性 | 公的機関の情報が適切に引用されているか |
| トピックのカバレッジ | 重要な気象イベントを網羅しているか |
| 各モデルの独自性・強み | そのモデルにしかない情報・視点は何か（モデルごとに簡潔に） |
| 読みやすさ・構成 | 見出し・要約・情報の整理がわかりやすいか |
| 総合評価 | 今週の順位付けと、最も有用な記事を書いたモデルとその理由 |

### 評価の再実行（手動・臨時）

比較ページが既に存在する場合は `--force` を付けて再生成する:

```bash
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

### Claude Code CLI が見つからない / 失敗する

```bash
# CLI の存在確認
ls -la ~/.local/bin/claude

# サブスクリプション認証状態の確認（ログイン画面が出る場合は再ログイン）
claude --print --model haiku "こんにちは"
```

`--max-budget-usd` の上限に達すると失敗するため、ログに `budget` 関連のエラーが出ていないか確認する。

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
python3 ~/projects/weather_digest/scripts/generate_compare.py \
  --week-file MMDD --week-label "M/D〜M/D" --year YYYY --force
```
