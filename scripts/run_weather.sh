#!/bin/bash
# run_weather.sh — Claude Haiku による気象ニュース週次まとめ 自動実行スクリプト
# launchd から毎週月曜 08:00 に呼び出される。

set -euo pipefail

# --- 設定 ---
PROJECT_DIR="/Users/masahiro/projects/weather_digest"
LOG_FILE="${PROJECT_DIR}/weather_digest.log"
PYTHON_BIN="/opt/anaconda3/bin/python3"
HAIKU_MODEL="${HAIKU_MODEL:-claude-haiku-4-5-20251001}"
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
DAY_OF_MONTH=$(TZ=Asia/Tokyo date +%d)
YEAR=$(TZ=Asia/Tokyo date +%Y)
WEEK_FILE_MMDD=$(TZ=Asia/Tokyo date +%m%d)
WEEK_END=$(TZ=Asia/Tokyo date +%-m/%-d)
WEEK_START=$(TZ=Asia/Tokyo date -v-7d +%-m/%-d)
WEEK_LABEL="${WEEK_START}〜${WEEK_END}"
WEEKLY_FILE="${PROJECT_DIR}/articles/weekly/${YEAR}-${WEEK_FILE_MMDD}.md"

# --- ログ関数 ---
log() {
  echo "[$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# --- ANTHROPIC_API_KEY の読み込み ---
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  if [ -f "${HOME}/.anthropic_env" ]; then
    # shellcheck disable=SC1090
    source "${HOME}/.anthropic_env"
    log "ANTHROPIC_API_KEY を ~/.anthropic_env から読み込みました"
  fi
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  log "ERROR: ANTHROPIC_API_KEY が設定されていません"
  log "  ~/.anthropic_env に ANTHROPIC_API_KEY=sk-ant-... を記載してください"
  exit 1
fi
export ANTHROPIC_API_KEY

# --- 開始 ---
log "=== weather_digest 起動チェック ==="
log "今日: ${TODAY} / ファイル: ${YEAR}-${WEEK_FILE_MMDD} / 対象期間: ${WEEK_LABEL}"

cd "${PROJECT_DIR}"

# --- 実行済みチェック（今週分のファイルが既にあればスキップ）---
if [ -f "${WEEKLY_FILE}" ]; then
  log "今週分の記事（${YEAR}-${WEEK_FILE_MMDD}）は生成済み。スキップします。"
  exit 0
fi

log "=== weather_digest 自動実行開始 ==="

# --- モード判定（第1月曜か否か）---
if [ "${DAY_OF_MONTH}" -le 7 ]; then
  MODE="monthly"
  log "モード: monthly（第1月曜 → 月次まとめも生成）"
else
  MODE="weekly"
  log "モード: weekly"
fi

# --- エージェント実行（タイムアウト時リトライ最大2回）---
MAX_RETRY=2
RETRY=0
SUCCESS=false

while [ ${RETRY} -lt ${MAX_RETRY} ]; do
  RETRY=$((RETRY + 1))
  log "エージェントを起動します... model=${HAIKU_MODEL} (試行 ${RETRY}/${MAX_RETRY})"

  if "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/haiku_agent.py" \
      --mode "${MODE}" \
      --week-file "${WEEK_FILE_MMDD}" \
      --week-label "${WEEK_LABEL}" \
      --year "${YEAR}" \
      --month "$(TZ=Asia/Tokyo date +%m)" \
      --model "${HAIKU_MODEL}" \
      2>&1 | tee -a "${LOG_FILE}"; then
    SUCCESS=true
    break
  else
    EXIT_CODE=$?
    log "エージェントが終了コード ${EXIT_CODE} で失敗しました。"
    if [ ${RETRY} -lt ${MAX_RETRY} ]; then
      log "30秒後にリトライします..."
      sleep 30
    fi
  fi
done

if [ "${SUCCESS}" = false ]; then
  log "ERROR: ${MAX_RETRY}回試行しましたがすべて失敗しました。手動確認が必要です。"
  exit 1
fi

log "=== weather_digest 自動実行完了 ==="
