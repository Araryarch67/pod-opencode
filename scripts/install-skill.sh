#!/usr/bin/env bash
# Install pod-opencode skill globally so any AI agent can discover it.
# Usage: ./scripts/install-skill.sh [--global-only]
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/skills/pod-opencode"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "skill source not found: $SRC/SKILL.md" >&2
  exit 1
fi

targets=(
  "$HOME/.config/opencode/skills/pod-opencode"
  "$HOME/.claude/skills/pod-opencode"
  "$HOME/.agents/skills/pod-opencode"
  "$HOME/.codex/skills/pod-opencode"
)

for t in "${targets[@]}"; do
  mkdir -p "$t"
  cp -r "$SRC"/. "$t"/
  echo "installed -> $t"
done

echo "done. Restart your agent / run /skills to verify 'pod-opencode' appears."
