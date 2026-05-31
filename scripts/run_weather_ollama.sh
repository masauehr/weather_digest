#!/bin/bash
# run_weather_ollama.sh — Ollama（qwen）による気象ニュース週次まとめ 自動実行スクリプト
# launchd から毎週日曜 08:00 に呼び出される。

set -euo pipefail

PROJECT_DIR="/Users/masahiro/projects/weather_digest"
LOG_FILE="${PROJECT_DIR}/weather_digest.log"
PYTHON_BIN="/opt/anaconda3/bin/python3"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.6:35b-mlx}"
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
DAY_OF_MONTH=$(TZ=Asia/Tokyo date +%d)
YEAR=$(TZ=Asia/Tokyo date +%Y)
WEEK_FILE_MMDD=$(TZ=Asia/Tokyo date +%m%d)
WEEK_END=$(TZ=Asia/Tokyo date +%-m/%-d)
WEEK_START=$(TZ=Asia/Tokyo date -v-7d +%-m/%-d)
WEEK_LABEL="${WEEK_START}〜${WEEK_END}"
WEEKLY_FILE="${PROJECT_DIR}/articles/weekly/${YEAR}-${WEEK_FILE_MMDD}.md"

log() {
  echo "[$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=== weather_digest Ollama 起動チェック ==="
log "今日: ${TODAY} / ファイル: ${YEAR}-${WEEK_FILE_MMDD} / 対象期間: ${WEEK_LABEL}"

cd "${PROJECT_DIR}"

if [ -f "${WEEKLY_FILE}" ]; then
  log "今週分のOllama記事（${YEAR}-${WEEK_FILE_MMDD}）は生成済み。スキップします。"
  # 比較ページが未生成なら試みる
  COMPARE_FILE="${PROJECT_DIR}/articles/compare/${YEAR}-${WEEK_FILE_MMDD}.md"
  if [ ! -f "${COMPARE_FILE}" ]; then
    HAIKU_FILE="${PROJECT_DIR}/articles/haiku_weekly/${YEAR}-${WEEK_FILE_MMDD}.md"
    if [ -f "${HAIKU_FILE}" ]; then
      log "比較ページが未生成のため生成を試みます..."
      "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/generate_compare.py" \
        --week-file "${WEEK_FILE_MMDD}" \
        --week-label "${WEEK_LABEL}" \
        --year "${YEAR}" \
        2>&1 | tee -a "${LOG_FILE}" || true
    fi
  fi
  exit 0
fi

log "=== weather_digest Ollama 自動実行開始 ==="

if [ "${DAY_OF_MONTH}" -le 7 ]; then
  MODE="monthly"
  log "モード: monthly（第1日曜 → 月次まとめも生成）"
else
  MODE="weekly"
  log "モード: weekly"
fi

# Ollama 疎通確認
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
  log "ERROR: Ollama が起動していません。ollama serve を実行してください。"
  exit 1
fi

MAX_RETRY=2
RETRY=0
SUCCESS=false

while [ ${RETRY} -lt ${MAX_RETRY} ]; do
  RETRY=$((RETRY + 1))
  log "Ollamaエージェントを起動します... model=${OLLAMA_MODEL} (試行 ${RETRY}/${MAX_RETRY})"

  if "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/local_agent.py" \
      --mode "${MODE}" \
      --week-file "${WEEK_FILE_MMDD}" \
      --week-label "${WEEK_LABEL}" \
      --year "${YEAR}" \
      --month "$(TZ=Asia/Tokyo date +%m)" \
      --model "${OLLAMA_MODEL}" \
      2>&1 | tee -a "${LOG_FILE}"; then
    SUCCESS=true
    break
  else
    EXIT_CODE=$?
    log "Ollamaエージェントが終了コード ${EXIT_CODE} で失敗しました。"
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

log "=== Ollama 記事生成完了 ==="

# Haiku版記事が揃っていれば比較ページを生成
HAIKU_FILE="${PROJECT_DIR}/articles/haiku_weekly/${YEAR}-${WEEK_FILE_MMDD}.md"
COMPARE_FILE="${PROJECT_DIR}/articles/compare/${YEAR}-${WEEK_FILE_MMDD}.md"

if [ -f "${HAIKU_FILE}" ] && [ ! -f "${COMPARE_FILE}" ]; then
  log "=== 比較ページ生成開始 ==="
  "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/generate_compare.py" \
    --week-file "${WEEK_FILE_MMDD}" \
    --week-label "${WEEK_LABEL}" \
    --year "${YEAR}" \
    2>&1 | tee -a "${LOG_FILE}" || log "WARN: 比較ページ生成に失敗しました（手動で実行してください）"
  log "=== 比較ページ生成完了 ==="
elif [ ! -f "${HAIKU_FILE}" ]; then
  log "INFO: Haiku版記事はまだ未生成（12:00以降に自動生成されます）"
fi

log "=== weather_digest Ollama 自動実行完了 ==="
