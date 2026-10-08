# Round-trips: chaining edits across files

Every write produces a **complete new snapshot**, never a delta. Always
feed the latest output into the next command:

```bash
pod-opencode tasks update project.pod 1 --percent-complete 50 --output /tmp/v1.pod
pod-opencode tasks add /tmp/v1.pod --name "QA" --start 2025-08-01 --duration "3d" --output /tmp/v2.pod
```

Rules:

- Read `.pod` or `.xml`; write `.xml` or `.pod`. Both open in ProjectLibre.
- To edit the same file in place, use `--in-place` (writes `<file>.bak` first). `--output` and `--in-place` never combine.
- UniqueIDs stay stable across round-trips; sequential IDs may shift after insert/delete.
- Open the final file in ProjectLibre directly. No Save As step needed.
