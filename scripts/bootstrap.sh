#!/usr/bin/env bash
# pod-opencode bootstrap: install the CLI and auto-apply the skill.
#
# One-liner (fresh machine, needs git + python3):
#   curl -sSL https://raw.githubusercontent.com/Araryarch67/pod-opencode/main/scripts/bootstrap.sh | bash -s --
# From a repo checkout:
#   ./scripts/bootstrap.sh [--cli-only] [--skill-only] [--from-repo] [--dry-run]
#
# Default: pip install pod-opencode from PyPI, then copy the skill into
# every known agent skills dir (only ones for detected agents are
# reported as active, but all four are installed so future agents work).
set -euo pipefail

REPO_URL="https://github.com/Araryarch67/pod-opencode.git"
PYPI_NAME="pod-opencode"
SKILL_NAME="pod-opencode"

CLI_ONLY=0
SKILL_ONLY=0
FROM_REPO=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --cli-only) CLI_ONLY=1 ;;
    --skill-only) SKILL_ONLY=1 ;;
    --from-repo) FROM_REPO=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "unknown flag: $arg (see header)" >&2; exit 1 ;;
  esac
done

run() {
  if [ "$DRY_RUN" = 1 ]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

# --- locate skill source (repo checkout or temp clone) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || echo "")"
SRC="$SCRIPT_DIR/../skills/$SKILL_NAME"
if [ ! -f "$SRC/SKILL.md" ]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "need git to fetch the skill (or run from a repo checkout)" >&2
    exit 1
  fi
  TMP_CLONE="$(mktemp -d)/pod-opencode"
  echo "cloning $REPO_URL ..."
  run git clone --depth 1 "$REPO_URL" "$TMP_CLONE"
  SRC="$TMP_CLONE/skills/$SKILL_NAME"
fi

fail=0

# --- prerequisites ---
if command -v python3 >/dev/null 2>&1; then
  PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  echo "python3: $PYVER"
else
  echo "MISSING: python3 (>= 3.10 required)" >&2
  fail=1
fi
if command -v java >/dev/null 2>&1; then
  echo "java: $(java -version 2>&1 | head -n 1)"
else
  echo "MISSING: java (JRE 8+ required on PATH)" >&2
  fail=1
fi

# --- CLI ---
if [ "$SKILL_ONLY" = 0 ]; then
  if [ "$FROM_REPO" = 1 ]; then
    REPO_ROOT="$(cd "$SRC/../.." && pwd)"
    echo "installing CLI from repo: $REPO_ROOT"
    run python3 -m pip install -e "$REPO_ROOT"
  else
    echo "installing CLI from PyPI: $PYPI_NAME"
    run python3 -m pip install -U "$PYPI_NAME"
  fi
  if [ "$DRY_RUN" = 0 ]; then
    if pod-opencode --version >/dev/null 2>&1; then
      echo "CLI ok: $(pod-opencode --version)"
    else
      echo "CLI installed but not on PATH (check pip --user bin dir)" >&2
    fi
  fi
fi

# --- skill ---
if [ "$CLI_ONLY" = 0 ]; then
  detect() { # detect <label> <command> <dir>
    if command -v "$2" >/dev/null 2>&1 || [ -d "$3" ]; then
      echo "  detected: $1"
    else
      echo "  (not detected, still installing): $1"
    fi
  }
  echo "agent detection:"
  detect "opencode" "opencode" "$HOME/.config/opencode"
  detect "claude" "claude" "$HOME/.claude"
  detect "codex" "codex" "$HOME/.codex"
  detect "generic-agents" "cursor-agent" "$HOME/.agents"

  for target in \
    "$HOME/.config/opencode/skills/$SKILL_NAME" \
    "$HOME/.claude/skills/$SKILL_NAME" \
    "$HOME/.agents/skills/$SKILL_NAME" \
    "$HOME/.codex/skills/$SKILL_NAME"; do
    run mkdir -p "$target"
    run cp -r "$SRC"/. "$target"/
    echo "skill -> $target"
  done
  echo "restart your agent (or run /skills) to verify '$SKILL_NAME' appears."
fi

if [ "$fail" = 1 ]; then
  echo "bootstrap incomplete: install the missing prerequisites above, then re-run." >&2
  exit 1
fi
echo "bootstrap done."
