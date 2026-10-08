# POD → XML round-trip

MPXJ cannot write `.pod`. Every mutation writes a full MSPDI `.xml` snapshot.

1. Read the `.pod`:
   `pod-opencode info project.pod`
2. Write each change to `.xml`:
   `pod-opencode tasks update project.pod 1 --percent-complete 50 --output /tmp/v1.xml`
3. Chain further edits off the latest XML, not the original POD:
   `pod-opencode tasks add /tmp/v1.xml --name "QA" --start 2025-08-01 --duration "3d" --output /tmp/v2.xml`
4. Open `/tmp/v2.xml` in ProjectLibre via File > Open. Optionally Save As `.pod` there.

Rules:

- Never pass `--output something.pod`; the CLI rejects it.
- Each `--output` is a complete project, not a delta.
- UniqueIDs are stable across round-trips; sequential IDs may shift after insert/delete.
