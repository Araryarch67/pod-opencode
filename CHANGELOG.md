# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `tasks assign` and `tasks unassign` to manage resource assignments,
  including `--units` and duplicate/unknown-ID errors.
- `tasks link` and `tasks unlink` to manage predecessor relations
  (FS, SS, FF, SF, optional lag).
- `tasks import` to create many tasks at once from a batch JSON file,
  with parent references, resource assignments, milestones, and
  project naming.
- `diff` command to compare two project files (renames, added/removed
  items, per-field changes, summary counts).
- `run` command: many operations from one JSON script in a single JVM
  session, with ref labels, did-you-mean hints, per-op receipts, and
  all-or-nothing writes.
- Single-action commands (`info`, `convert`, `diff`, `check`, `run`) are
  real commands now, so options parse in any position.
- `check` command to lint a file (dangling/self links, finish before
  start, broken hierarchy, out-of-range percents, missing dates,
  unassigned tasks, duplicate names), including raw-XML detection of
  links MPXJ drops silently.
- `--in-place` on every write command: backs up the input to `.bak` and
  overwrites it.
- `--milestone` / `--no-milestone` on `tasks add` and `tasks update`.
- Input validation with `INVALID_VALUE` errors: percent range, duration and
  date parsing, finish-before-start.
- Explicit `jpype1` dependency (the `mpxj` package does not declare it, so
  fresh installs failed to start the JVM).

### Fixed

- Deleting a task now sweeps predecessor links pointing at it and its
  subtree, which previously lingered as dangling links.
- Updating start without finish can no longer leave a stale finish behind:
  the merged dates are validated and rejected with `INVALID_VALUE`.
- `link` rejects self-links.
- `link` (CLI and `run`) refuses links that would close a dependency
  cycle, and `check` reports `DEPENDENCY_CYCLE` for foreign files.
- Units are fractions end to end (`1.0` = 100%): assignment `--units`
  and resource `--max-units` used to write 100x too little into the
  file, and `--max-units` crashed outright (MPXJ 16 removed
  `setMaxUnits`; availability now goes through the date-range table).

## [0.2.0] - 2026-10-09

### Added

- Native `.pod` output: every write command accepts `--output file.pod`.
  The file is a real ProjectLibre container (header, separator, embedded
  MSPDI) and opens in ProjectLibre with the correct title.
- `--project-name` on `convert` and all write commands. Sets the project
  Name and Title, which is what ProjectLibre shows in its title bar.
- `--parent-id` on `tasks add` inserts the child after the parent's subtree
  with correct outline level and WBS, so re-reads nest it correctly.
- `--duration` on `tasks add` and `tasks update` is now applied instead of
  ignored.
- `tests/fixtures/real.pod`, a genuine ProjectLibre-written fixture used by
  the test-suite.
- AI agent skill (`pod-opencode`) with project-local installs for OpenCode,
  Claude Code, Codex, Cursor and generic agents, plus
  `scripts/install-skill.sh` for global installs.
- `LICENSE` (MIT) and `CHANGELOG.md`.

### Fixed

- Task and resource lookup by ID failed on MPXJ 16 (missing Integer boxing).
  `get`, `update` and `delete` by UniqueID work again.
- Dates on `tasks add` and `tasks update` failed (MPXJ 16 expects
  `LocalDateTime`, not `java.util.Date`).
- All dates read back as null (MPXJ 16 returns `java.time` temporals, the
  converter only handled `java.util.Date`).
- New tasks and resources got null IDs, which crashed MSPDI writing and
  returned null `affected_unique_id`. IDs are now assigned as max+1.
- Error paths printed two JSON objects on stderr (`typer.Exit` was caught by
  `except Exception`). Each failure now prints exactly one.
- Unreadable files failed with an internal `NoneType` error. The reader now
  reports unsupported formats, including pre-1.5.5 POD files without
  embedded schedule data.

### Credits

- Based on [pod-ai-cli](https://github.com/distractdiverge/pod-ai-cli) by
  distractdiverge.

[Unreleased]: https://github.com/Araryarch67/pod-opencode/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Araryarch67/pod-opencode/releases/tag/v0.2.0
