#!/usr/bin/env bash
# scripts/check_forbidden_colors.sh
#
# Enforces `docs/plan/mvp-implementation-plan.md` §17 hard-constraint #11.
# Run from any CWD; uses project root via git.
set -euo pipefail

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  root="$(git rev-parse --show-toplevel)"
else
  root="$(cd "$(dirname "$0")/../.." && pwd)"
fi

pattern='#FF4D4F|#D32F2F|#007BFF'

# Allow-list: this script is the only file that *defines* the forbidden
# tokens (otherwise the check would always self-flag).
allowlist_regex='(^|/)(scripts/check_forbidden_colors.sh|packages/lint-rules/)'

hits=$(
  grep -rEn --exclude-dir=build --exclude-dir=.dart_tool \
    --exclude-dir=scripts --exclude-dir=lint-rules \
    --exclude-dir=api-types \
    -- "$pattern" "$root" 2>/dev/null \
    | grep -Ev "$allowlist_regex" || true
)

if [ -n "$hits" ]; then
  echo "[forbidden-colors] FAIL — §17 #11 hit:"
  echo "$hits"
  exit 1
fi

echo "[forbidden-colors] OK — §17 #11 0 hits"