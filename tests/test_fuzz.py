"""Seeded fuzz: random valid operation sequences stay error-free.

Each scenario runs 30 random mutations against a scratch copy (XML and
POD), asserting after every step that the command succeeds, stdout is
valid JSON, and `check` reports zero errors. Deterministic per seed.
"""

import json
import random
import shutil

from typer.testing import CliRunner

from pod_opencode.cli import app

runner = CliRunner()

TYPES = ["FS", "SS", "FF", "SF"]


def _run(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 0, (args, result.stderr)
    return json.loads(result.stdout)


def _check_clean(path):
    result = runner.invoke(app, ["check", path])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["summary"]["errors"] == 0, data["errors"]


def _task_uids(path):
    return [t["unique_id"] for t in _run(["tasks", "list", path])["tasks"]]


def _res_uids(path):
    return [r["unique_id"] for r in _run(["resources", "list", path])["resources"]]


def _pairs(path):
    data = _run(["assignments", "list", path])["assignments"]
    # Skip resourceless actuals rows (no resource UID to address).
    return {
        (a["task_unique_id"], a["resource_unique_id"])
        for a in data
        if a["task_unique_id"] is not None and a["resource_unique_id"] is not None
    }


def _links(path, uid):
    preds = _run(["tasks", "get", path, str(uid)])["predecessors"]
    return {(p["task_unique_id"], p["relation_type"]) for p in preds}


def _scenario(seed, start_file, tmp_path, ext, steps=30):
    rng = random.Random(seed)
    path = str(tmp_path / f"fuzz-{seed}{ext}")
    shutil.copy(start_file, path)
    _check_clean(path)
    counter = 0

    for _ in range(steps):
        uids = _task_uids(path)
        ruids = _res_uids(path)
        op = rng.choice(
            [
                "add",
                "update",
                "delete",
                "assign",
                "unassign",
                "link",
                "unlink",
                "rename",
            ]
        )

        if op == "add":
            args = ["tasks", "add", path, "--name", f"F{seed}-{counter}"]
            if uids and rng.random() < 0.4:
                args += ["--parent-id", str(rng.choice(uids))]
            if rng.random() < 0.6:
                args += [
                    "--start",
                    "2026-10-12",
                    "--duration",
                    rng.choice(["1d", "5d", "2w"]),
                ]
            if rng.random() < 0.15:
                args += ["--milestone"]
            args += ["--output", path]
            _run(args)
            counter += 1
        elif op == "update" and uids:
            uid = str(rng.choice(uids))
            field = rng.choice(["name", "percent", "dates"])
            if field == "name":
                args = ["tasks", "update", path, uid, "--name", f"R{seed}-{counter}"]
            elif field == "percent":
                args = [
                    "tasks",
                    "update",
                    path,
                    uid,
                    "--percent-complete",
                    str(rng.choice([0, 25, 50, 100])),
                ]
            else:
                args = [
                    "tasks",
                    "update",
                    path,
                    uid,
                    "--start",
                    "2026-11-01",
                    "--finish",
                    "2026-11-10",
                    "--duration",
                    "3d",
                ]
            args += ["--output", path]
            _run(args)
            counter += 1
        elif op == "delete" and uids:
            _run(["tasks", "delete", path, str(rng.choice(uids)), "--output", path])
        elif op == "assign" and uids and ruids:
            taken = _pairs(path)
            free = [(t, r) for t in uids for r in ruids if (t, r) not in taken]
            if free:
                t, r = rng.choice(free)
                _run(["tasks", "assign", path, str(t), str(r), "--output", path])
        elif op == "unassign":
            taken = sorted(_pairs(path))
            if taken:
                t, r = rng.choice(taken)
                _run(["tasks", "unassign", path, str(t), str(r), "--output", path])
        elif op == "link" and len(uids) >= 2:
            task = rng.choice(uids)
            cands = [u for u in uids if u != task]
            pred = rng.choice(cands)
            if (pred, "FS") not in _links(path, task):
                _run(["tasks", "link", path, str(task), str(pred), "--output", path])
        elif op == "unlink" and uids:
            task = rng.choice(uids)
            existing = sorted(_links(path, task))
            if existing:
                pred, _ = rng.choice(existing)
                _run(["tasks", "unlink", path, str(task), str(pred), "--output", path])
        elif op == "rename":
            _run(["convert", "--project-name", f"P{seed}-{counter}", path, path])
            counter += 1

        _check_clean(path)

    return path


class TestFuzzXml:
    def test_seed_1(self, tmp_path):
        _scenario(1, "tests/fixtures/sample.xml", tmp_path, ".xml")

    def test_seed_2(self, tmp_path):
        _scenario(2, "tests/fixtures/sample.xml", tmp_path, ".xml")

    def test_seed_3(self, tmp_path):
        _scenario(3, "tests/fixtures/sample.xml", tmp_path, ".xml")


class TestFuzzPod:
    def test_seed_1(self, tmp_path):
        _scenario(1, "tests/fixtures/real.pod", tmp_path, ".pod")

    def test_seed_2(self, tmp_path):
        _scenario(2, "tests/fixtures/real.pod", tmp_path, ".pod")

    def test_seed_3(self, tmp_path):
        _scenario(3, "tests/fixtures/real.pod", tmp_path, ".pod")


class TestCrossFormatFidelity:
    def test_xml_pod_xml_roundtrip(self, tmp_path):
        first = _scenario(7, "tests/fixtures/sample.xml", tmp_path, ".xml", steps=10)
        tasks_xml = _run(["tasks", "list", first])["tasks"]
        res_xml = _run(["resources", "list", first])["resources"]
        pod = str(tmp_path / "mid.pod")
        _run(["convert", first, pod])
        back = str(tmp_path / "back.xml")
        _run(["convert", pod, back])
        assert _run(["tasks", "list", back])["tasks"] == tasks_xml
        assert _run(["resources", "list", back])["resources"] == res_xml
