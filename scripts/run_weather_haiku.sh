#!/bin/bash
# run_weather_haiku.sh — Claude Haiku による気象ニュース週次まとめ 自動実行スクリプト
# launchd から毎週日曜 12:00 に呼び出される（Ollama版の08:00より4時間後）。
#
# 【2026-07-25 変更】Anthropic API（従量課金クレジット）ではなく、
# Claude Code CLI（Pro/Maxサブスクリプション）経由で実行するように変更した。
# ai_news プロジェクトと同じ方式。ANTHROPIC_API_KEY は使わない
# （設定されていても haiku_agent.py / generate_compare.py 側で明示的に除去する）。

set -euo pipefail

PROJECT_DIR="/Users/masahiro/projects/weather_digest"
LOG_FILE="${PROJECT_DIR}/weather_digest_haiku.log"
PYTHON_BIN="/opt/anaconda3/bin/python3"
CLAUDE_BIN="${HOME}/.local/bin/claude"
HAIKU_MODEL="${HAIKU_MODEL:-haiku}"
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

# --- Claude Code CLI の存在確認（サブスクリプション認証。APIキーは使わない）---
if [ ! -x "${CLAUDE_BIN}" ]; then
  log "ERROR: Claude Code CLI が見つかりません: ${CLAUDE_BIN}"
  exit 1
fi
# ANTHROPIC_API_KEY が環境に残っているとAPIクレジット課金経路に戻ってしまうため、
# このプロセス内では明示的に外す（haiku_agent.py / generate_compare.py 側でも二重に除去する）
unset ANTHROPIC_API_KEY || true

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

# --- モード判定（第1週 = 月次も生成）---
if [ "${DAY_OF_MONTH}" -le 7 ]; then
  MODE="monthly"
  log "モード: monthly（第1日曜 → 月次まとめも生成）"
else
  MODE="weekly"
  log "モード: weekly"
fi

MONTH=$(TZ=Asia/Tokyo date +%m)
HAIKU_MONTHLY_FILE="${PROJECT_DIR}/articles/haiku_monthly/${YEAR}-${MONTH}.md"

# --- 共通: エージェント実行関数（リトライ付き）---
run_haiku_agent() {
  local _mode="$1"
  local _max_retry=2
  local _retry=0
  local _success=false

  while [ ${_retry} -lt ${_max_retry} ]; do
    _retry=$((_retry + 1))
    log "Haikuエージェントを起動します... mode=${_mode} model=${HAIKU_MODEL} (試行 ${_retry}/${_max_retry})"

    if "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/haiku_agent.py" \
        --mode "${_mode}" \
        --week-file "${WEEK_FILE_MMDD}" \
        --week-label "${WEEK_LABEL}" \
        --year "${YEAR}" \
        --month "${MONTH}" \
        --model "${HAIKU_MODEL}" \
        2>&1 | tee -a "${LOG_FILE}"; then
      _success=true
      break
    else
      EXIT_CODE=$?
      log "Haikuエージェントが終了コード ${EXIT_CODE} で失敗しました。"
      if [ ${_retry} -lt ${_max_retry} ]; then
        log "30秒後にリトライします..."
        sleep 30
      fi
    fi
  done

  if [ "${_success}" = false ]; then
    log "ERROR: ${_max_retry}回試行しましたがすべて失敗しました（mode=${_mode}）。手動確認が必要です。"
    return 1
  fi
  return 0
}

# --- 週次記事生成（常に実行）---
log "=== Haiku 週次記事生成開始 ==="
run_haiku_agent "weekly" || exit 1
log "=== Haiku 週次記事生成完了 ==="

# --- 月次記事生成（第1週のみ）---
if [ "${MODE}" = "monthly" ]; then
  if [ -f "${HAIKU_MONTHLY_FILE}" ]; then
    log "Haiku 月次記事（${YEAR}-${MONTH}）は実行済み。スキップします。"
  else
    log "=== Haiku 月次記事生成開始 ==="
    run_haiku_agent "monthly" || log "WARN: 月次記事生成に失敗しました（手動で実行してください）"
    log "=== Haiku 月次記事生成完了 ==="
  fi
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
