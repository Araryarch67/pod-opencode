"""Seeded fuzz: random valid operation sequences stay error-free.

Each scenario runs 30 random mutations against a scratch copy (XML and
POD), asserting after every step that the command succeeds, stdout is
valid JSON, and `check` reports zero errors. Deterministic per seed.
"""

import json
import random
import shutil
from pathlib import Path

from typer.testing import CliRunner

from pod_opencode.cli import app

runner = CliRunner()

FIXTURES = Path(__file__).parent / "fixtures"

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
                result = runner.invoke(
                    app,
                    ["tasks", "link", path, str(task), str(pred), "--output", path],
                )
                if result.exit_code == 1:
                    # A cycle rejection is a valid outcome, not a failure.
                    error = json.loads(result.stderr)
                    assert error["code"] == "INVALID_VALUE", result.stderr
                    assert "cycle" in error["error"], result.stderr
                else:
                    json.loads(result.stdout)
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
        _scenario(1, str(FIXTURES / "sample.xml"), tmp_path, ".xml")

    def test_seed_2(self, tmp_path):
        _scenario(2, str(FIXTURES / "sample.xml"), tmp_path, ".xml")

    def test_seed_3(self, tmp_path):
        _scenario(3, str(FIXTURES / "sample.xml"), tmp_path, ".xml")

    def test_seed_4(self, tmp_path):
        _scenario(4, str(FIXTURES / "sample.xml"), tmp_path, ".xml", steps=50)

    def test_seed_5(self, tmp_path):
        _scenario(5, str(FIXTURES / "sample.xml"), tmp_path, ".xml", steps=50)


class TestFuzzPod:
    def test_seed_1(self, tmp_path):
        _scenario(1, str(FIXTURES / "real.pod"), tmp_path, ".pod")

    def test_seed_2(self, tmp_path):
        _scenario(2, str(FIXTURES / "real.pod"), tmp_path, ".pod")

    def test_seed_3(self, tmp_path):
        _scenario(3, str(FIXTURES / "real.pod"), tmp_path, ".pod")

    def test_seed_4(self, tmp_path):
        _scenario(4, str(FIXTURES / "real.pod"), tmp_path, ".pod", steps=50)

    def test_seed_5(self, tmp_path):
        _scenario(5, str(FIXTURES / "real.pod"), tmp_path, ".pod", steps=50)


class TestCrossFormatFidelity:
    def test_xml_pod_xml_roundtrip(self, tmp_path):
        first = _scenario(7, str(FIXTURES / "sample.xml"), tmp_path, ".xml", steps=10)
        tasks_xml = _run(["tasks", "list", first])["tasks"]
        res_xml = _run(["resources", "list", first])["resources"]
        pod = str(tmp_path / "mid.pod")
        _run(["convert", first, pod])
        back = str(tmp_path / "back.xml")
        _run(["convert", pod, back])
        assert _run(["tasks", "list", back])["tasks"] == tasks_xml
        assert _run(["resources", "list", back])["resources"] == res_xml


class TestNegativeFuzz:
    """Invalid inputs must always fail cleanly: exit 1, exactly one JSON
    error on stderr, and no output file created."""

    BAD_CASES = [
        ["tasks", "get", "{f}", "999"],
        ["tasks", "update", "{f}", "1", "--percent-complete", "101", "--output", "{o}"],
        ["tasks", "update", "{f}", "1", "--percent-complete", "-1", "--output", "{o}"],
        ["tasks", "update", "{f}", "1", "--duration", "zero", "--output", "{o}"],
        ["tasks", "update", "{f}", "1", "--start", "not-a-date", "--output", "{o}"],
        ["tasks", "update", "{f}", "1", "--start", "2026-12-01", "--output", "{o}"],
        ["tasks", "add", "{f}", "--name", "X", "--duration", "1x", "--output", "{o}"],
        [
            "tasks",
            "add",
            "{f}",
            "--name",
            "X",
            "--start",
            "2026-12-01",
            "--finish",
            "2026-01-01",
            "--output",
            "{o}",
        ],
        ["tasks", "add", "{f}", "--name", "X", "--parent-id", "999", "--output", "{o}"],
        ["tasks", "delete", "{f}", "999", "--output", "{o}"],
        ["tasks", "assign", "{f}", "1", "999", "--output", "{o}"],
        ["tasks", "assign", "{f}", "999", "1", "--output", "{o}"],
        ["tasks", "assign", "{f}", "1", "1", "--units", "0", "--output", "{o}"],
        ["tasks", "assign", "{f}", "1", "1", "--units", "-2", "--output", "{o}"],
        ["tasks", "unassign", "{f}", "2", "2", "--output", "{o}"],
        ["tasks", "link", "{f}", "2", "1", "--type", "XX", "--output", "{o}"],
        ["tasks", "link", "{f}", "1", "1", "--output", "{o}"],
        ["tasks", "link", "{f}", "2", "999", "--output", "{o}"],
        ["tasks", "link", "{f}", "2", "1", "--lag", "soon", "--output", "{o}"],
        ["tasks", "unlink", "{f}", "2", "1", "--output", "{o}"],
        ["resources", "get", "{f}", "999"],
        ["resources", "update", "{f}", "999", "--email", "a@b.c", "--output", "{o}"],
        ["resources", "delete", "{f}", "999", "--output", "{o}"],
        [
            "tasks",
            "update",
            "{f}",
            "1",
            "--percent-complete",
            "10",
            "--output",
            "{o}",
            "--in-place",
        ],
        ["diff", "{f}", "{m}"],
        ["check", "{m}"],
        ["info", "{m}"],
    ]

    def test_bad_cases_xml(self, tmp_path):
        self._run_bad(str(FIXTURES / "sample.xml"), tmp_path, ".xml")

    def test_bad_cases_pod(self, tmp_path):
        self._run_bad(str(FIXTURES / "real.pod"), tmp_path, ".pod")

    def _run_bad(self, fixture, tmp_path, ext):
        import shutil

        src = str(tmp_path / f"neg{ext}")
        shutil.copy(fixture, src)
        missing = str(tmp_path / "missing.xml")
        for case in self.BAD_CASES:
            out = str(tmp_path / "should-not-exist.xml")
            args = [c.format(f=src, o=out, m=missing) for c in case]
            result = runner.invoke(app, args)
            assert result.exit_code == 1, args
            error = json.loads(result.stderr)
            assert set(error) == {"error", "code"}, (args, result.stderr)
            assert not Path(out).exists(), args

    def test_run_bad_script(self, tmp_path):
        import shutil

        src = str(tmp_path / "neg.xml")
        shutil.copy(str(FIXTURES / "sample.xml"), src)
        bad_scripts = [
            {"operations": []},
            {"operations": [{"op": "nope"}]},
            {"operations": [{"op": "add"}]},
            {"operations": [{"op": "update", "unique_id": 999}]},
            {"operations": [{"op": "link", "task": 1, "pred": 1}]},
            {"nope": True},
        ]
        for i, script in enumerate(bad_scripts):
            p = tmp_path / f"bad{i}.json"
            p.write_text(json.dumps(script))
            out = tmp_path / f"nope{i}.xml"
            result = runner.invoke(app, ["run", src, str(p), "--output", str(out)])
            assert result.exit_code == 1, script
            error = json.loads(result.stderr)
            assert "code" in error, (script, result.stderr)
            assert not out.exists(), script


class TestHelpSmoke:
    COMMANDS = [
        ["info", "--help"],
        ["convert", "--help"],
        ["tasks", "--help"],
        ["tasks", "list", "--help"],
        ["tasks", "get", "--help"],
        ["tasks", "add", "--help"],
        ["tasks", "update", "--help"],
        ["tasks", "delete", "--help"],
        ["tasks", "assign", "--help"],
        ["tasks", "unassign", "--help"],
        ["tasks", "link", "--help"],
        ["tasks", "unlink", "--help"],
        ["tasks", "import", "--help"],
        ["resources", "--help"],
        ["resources", "list", "--help"],
        ["resources", "get", "--help"],
        ["resources", "add", "--help"],
        ["resources", "update", "--help"],
        ["resources", "delete", "--help"],
        ["assignments", "list", "--help"],
        ["diff", "--help"],
        ["check", "--help"],
        ["run", "--help"],
    ]

    def test_all_helps(self):
        for args in self.COMMANDS:
            result = runner.invoke(app, args)
            assert result.exit_code == 0, args
            assert "Usage" in result.stdout, args
