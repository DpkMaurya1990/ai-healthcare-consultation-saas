#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGET_GLOB='backend/**/*.py'
EXCLUDE_GLOB='backend/cons_app_venv/**'

# Suspicious: sensitive identifiers appearing on/near logging or print calls.
SENSITIVE_PATTERN='patient_name|notes|email|phone|authorization|token|openai_api_key|clerk_secret_key|groq_api_key'
LOG_CALL_PATTERN='logger\.(debug|info|warning|error|exception|critical)|audit_logger\.(debug|info|warning|error|exception|critical)|access_logger\.(debug|info|warning|error|exception|critical)|logging\.(debug|info|warning|error|exception|critical)|\bprint\('

# Suspicious: logging full payload objects or request bodies.
PAYLOAD_PATTERN='request\.body\(|request\.json\(|json\.dumps\(.*(notes|patient_name|email|phone)|dict\(.*(notes|patient_name|email|phone)'

search_matches() {
  local pattern="$1"

  if command -v rg >/dev/null 2>&1; then
    rg -n --no-heading -i "$pattern" "$TARGET_GLOB" -g "!$EXCLUDE_GLOB" || true
    return
  fi

  if command -v grep >/dev/null 2>&1; then
    grep -RInE --include='*.py' --exclude-dir='cons_app_venv' "$pattern" backend || true
    return
  fi

  echo "[audit] ERROR: neither 'rg' nor 'grep' is available on this machine." >&2
  exit 2
}

echo "[audit] scanning backend logging statements for potential PII leakage..."

log_findings="$(search_matches "(${LOG_CALL_PATTERN}).*(${SENSITIVE_PATTERN})|(${SENSITIVE_PATTERN}).*(${LOG_CALL_PATTERN})")"
payload_findings="$(search_matches "${PAYLOAD_PATTERN}")"

if [[ -n "$log_findings" || -n "$payload_findings" ]]; then
  echo "[audit] POTENTIAL LEAK RISK FOUND"

  if [[ -n "$log_findings" ]]; then
    echo
    echo "[audit] suspicious logging lines:"
    echo "$log_findings"
  fi

  if [[ -n "$payload_findings" ]]; then
    echo
    echo "[audit] suspicious payload logging lines:"
    echo "$payload_findings"
  fi

  echo
  echo "[audit] review required: avoid logging raw patient_name/notes/email/phone and auth secrets."
  exit 1
fi

echo "[audit] OK: no obvious PII logging patterns detected in backend source."
