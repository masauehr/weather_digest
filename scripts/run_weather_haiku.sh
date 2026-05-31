#!/bin/bash
# run_weather_haiku.sh — Claude Haiku による気象ニュース週次まとめ 自動実行スクリプト
# launchd から毎週日曜 12:00 に呼び出される（Ollama版の08:00より4時間後）。

set -euo pipefail

PROJECT_DIR="/Users/masahiro/projects/weather_digest"
LOG_FILE="${PROJECT_DIR}/weather_digest_haiku.log"
PYTHON_BIN="/opt/anaconda3/bin/python3"
HAIKU_MODEL="${HAIKU_MODEL:-claude-haiku-4-5-20251001}"
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
DAY_OF_MONTH=$(TZ=Asia/Tokyo date +%d)
YEAR=$(TZ=Asia/Tokyo date +%Y)
WEEK_FILE_MMDD=$(TZ=Asia/Tokyo date +%m%d)
WEEK_END=$(TZ=Asia/Tokyo date +%-m/%-d)
WEEK_START=$(TZ=Asia/Tokyo date -v-7d +%-m/%-d)
WEEK_LABEL="${WEEK_START}〜${WEEK_END}"
HAIKU_WEEKLY_FILE="${PROJECT_DIR}/articles/haiku_weekly/${YEAR}-${WEEK_FILE_MMDD}.md"

log() {
  echo "[$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# ANTHROPIC_API_KEY の読み込み
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  if [ -f "${HOME}/.anthropic_env" ]; then
    # shellcheck disable=SC1090
    source "${HOME}/.anthropic_env"
    log "ANTHROPIC_API_KEY を ~/.anthropic_env から読み込みました"
  fi
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  log "ERROR: ANTHROPIC_API_KEY が設定されていません"
  exit 1
fi
export ANTHROPIC_API_KEY

log "=== weather_digest Haiku 起動チェック ==="
log "今日: ${TODAY} / ファイル: ${YEAR}-${WEEK_FILE_MMDD} / 対象期間: ${WEEK_LABEL}"

cd "${PROJECT_DIR}"

if [ -f "${HAIKU_WEEKLY_FILE}" ]; then
  log "今週分のHaiku記事（${YEAR}-${WEEK_FILE_MMDD}）は生成済み。スキップします。"
  # 比較ページが未生成なら試みる
  COMPARE_FILE="${PROJECT_DIR}/articles/compare/${YEAR}-${WEEK_FILE_MMDD}.md"
  OLLAMA_FILE="${PROJECT_DIR}/articles/weekly/${YEAR}-${WEEK_FILE_MMDD}.md"
  if [ ! -f "${COMPARE_FILE}" ] && [ -f "${OLLAMA_FILE}" ]; then
    log "比較ページが未生成のため生成を試みます..."
    "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/generate_compare.py" \
      --week-file "${WEEK_FILE_MMDD}" \
      --week-label "${WEEK_LABEL}" \
      --year "${YEAR}" \
      2>&1 | tee -a "${LOG_FILE}" || true
  fi
  exit 0
fi

log "=== weather_digest Haiku 自動実行開始 ==="
MODE="weekly"
log "モード: ${MODE}"

MAX_RETRY=2
RETRY=0
SUCCESS=false

while [ ${RETRY} -lt ${MAX_RETRY} ]; do
  RETRY=$((RETRY + 1))
  log "Haikuエージェントを起動します... model=${HAIKU_MODEL} (試行 ${RETRY}/${MAX_RETRY})"

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
    log "Haikuエージェントが終了コード ${EXIT_CODE} で失敗しました。"
    if [ ${RETRY} -lt ${MAX_RETRY} ]; then
      log "30秒後にリトライします..."
      sleep 30
    fi
  fi
done

if [ "${SUCCESS}" = false ]; then
  log "ERROR: ${MAX_RETRY}回試行しましたがすべて失敗しました。"
  exit 1
fi

log "=== Haiku 記事生成完了 ==="

# Ollama版記事が揃っていれば比較ページを生成
OLLAMA_FILE="${PROJECT_DIR}/articles/weekly/${YEAR}-${WEEK_FILE_MMDD}.md"
COMPARE_FILE="${PROJECT_DIR}/articles/compare/${YEAR}-${WEEK_FILE_MMDD}.md"

if [ -f "${OLLAMA_FILE}" ] && [ ! -f "${COMPARE_FILE}" ]; then
  log "=== 比較ページ生成開始 ==="
  "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/generate_compare.py" \
    --week-file "${WEEK_FILE_MMDD}" \
    --week-label "${WEEK_LABEL}" \
    --year "${YEAR}" \
    2>&1 | tee -a "${LOG_FILE}" || log "WARN: 比較ページ生成に失敗しました"
  log "=== 比較ページ生成完了 ==="
elif [ ! -f "${OLLAMA_FILE}" ]; then
  log "INFO: Ollama版記事が未生成のため比較ページはスキップ"
  log "      手動生成コマンド: python3 ${PROJECT_DIR}/scripts/generate_compare.py --week-file ${WEEK_FILE_MMDD} --week-label '${WEEK_LABEL}' --year ${YEAR}"
fi

log "=== weather_digest Haiku 自動実行完了 ==="
