#!/bin/bash
# run_weather_nemotron.sh — Ollama（nemotron-3.5-lightning:30b-mlx）による気象ニュース週次まとめ 自動実行スクリプト
# launchd から毎週日曜 10:30 に呼び出される（qwen版 08:00・ornith版 09:30 の後、Haiku版 12:00 の前）。
# モデル比較用の追加ローカルLLM。README・トップ index.md は更新せず、
# 自分のアーカイブ一覧（articles/nemotron_weekly/index.md）だけを更新する。
# 比較ページは Haiku 完了後に generate_compare.py が自動生成する。

set -euo pipefail

SLUG="nemotron"
PROJECT_DIR="/Users/masahiro/projects/weather_digest"
LOG_FILE="${PROJECT_DIR}/weather_digest_${SLUG}.log"
PYTHON_BIN="/opt/anaconda3/bin/python3"
OLLAMA_MODEL="${OLLAMA_MODEL:-nemotron-3.5-lightning:30b-mlx}"
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
DAY_OF_MONTH=$(TZ=Asia/Tokyo date +%d)
YEAR=$(TZ=Asia/Tokyo date +%Y)
WEEK_FILE_MMDD=$(TZ=Asia/Tokyo date +%m%d)
WEEK_END=$(TZ=Asia/Tokyo date +%-m/%-d)
WEEK_START=$(TZ=Asia/Tokyo date -v-7d +%-m/%-d)
WEEK_LABEL="${WEEK_START}〜${WEEK_END}"
WEEKLY_FILE="${PROJECT_DIR}/articles/${SLUG}_weekly/${YEAR}-${WEEK_FILE_MMDD}.md"

log() {
  echo "[$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=== weather_digest ${SLUG} 起動チェック ==="
log "今日: ${TODAY} / ファイル: ${YEAR}-${WEEK_FILE_MMDD} / 対象期間: ${WEEK_LABEL} / モデル: ${OLLAMA_MODEL}"

cd "${PROJECT_DIR}"

if [ -f "${WEEKLY_FILE}" ]; then
  log "今週分の${SLUG}記事（${YEAR}-${WEEK_FILE_MMDD}）は生成済み。スキップします。"
  exit 0
fi

log "=== weather_digest ${SLUG} 自動実行開始 ==="

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
  log "Ollamaエージェントを起動します... model=${OLLAMA_MODEL} slug=${SLUG} (試行 ${RETRY}/${MAX_RETRY})"

  if "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/local_agent.py" \
      --mode "${MODE}" \
      --week-file "${WEEK_FILE_MMDD}" \
      --week-label "${WEEK_LABEL}" \
      --year "${YEAR}" \
      --month "$(TZ=Asia/Tokyo date +%m)" \
      --model "${OLLAMA_MODEL}" \
      --slug "${SLUG}" \
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

log "=== weather_digest ${SLUG} 自動実行完了 ==="
