#!/usr/bin/env bash
# Sync canonical skill (skills/pod-opencode) to project-local agent dirs.
# Edit ONLY skills/pod-opencode/*, then run this.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/skills/pod-opencode"

for t in .opencode/skills/pod-opencode .claude/skills/pod-opencode .agents/skills/pod-opencode .codex/skills/pod-opencode; do
  mkdir -p "$REPO_ROOT/$t"
  cp -r "$SRC"/. "$REPO_ROOT/$t"/
  echo "synced -> $t"
done
