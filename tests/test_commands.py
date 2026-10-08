import pytest
import json
from pathlib import Path
from typer.testing import CliRunner
from pod_opencode.cli import app

runner = CliRunner()


class TestInfoCommand:
    def test_info_outputs_json(self, sample_pod_path):
        result = runner.invoke(app, ["info", sample_pod_path])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "name" in data or "project_id" in data or "task_count" in data

    def test_info_file_not_found(self):
        result = runner.invoke(app, ["info", "/nonexistent/file.pod"])
        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["code"] == "FILE_NOT_FOUND"


class TestConvertCommand:
    def test_convert_creates_pod(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "output.pod"
        result = runner.invoke(app, ["convert", sample_pod_path, str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        raw = output_file.read_bytes()
        assert b"ProjectLibreSeparator_MSXML" in raw
        info = runner.invoke(app, ["info", str(output_file)])
        assert info.exit_code == 0
        before = json.loads(runner.invoke(app, ["info", sample_pod_path]).stdout)
        assert json.loads(info.stdout)["name"] == before["name"]

    def test_convert_creates_xml(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "output.xml"
        result = runner.invoke(app, ["convert", sample_pod_path, str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()


class TestTasksCommand:
    def test_tasks_list_outputs_json(self, sample_pod_path):
        result = runner.invoke(app, ["tasks", "list", sample_pod_path])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "tasks" in data
        assert "count" in data
        assert isinstance(data["tasks"], list)

    def test_tasks_get_existent(self, sample_pod_path):
        result = runner.invoke(app, ["tasks", "get", sample_pod_path, "1"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["unique_id"] == 1

    def test_tasks_get_nonexistent(self, sample_pod_path):
        result = runner.invoke(app, ["tasks", "get", sample_pod_path, "999"])
        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["code"] == "TASK_NOT_FOUND"

    def test_tasks_add_creates_pod(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "out.pod"
        result = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "Test Task",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        tasks = json.loads(
            runner.invoke(app, ["tasks", "list", str(output_file)]).stdout
        )
        assert any(t["name"] == "Test Task" for t in tasks["tasks"])

    def test_tasks_add_child_nesting(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "nested.xml"
        result = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "Anak",
                "--parent-id",
                "1",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        tasks = json.loads(
            runner.invoke(app, ["tasks", "list", str(output_file)]).stdout
        )["tasks"]
        child = next(t for t in tasks if t["name"] == "Anak")
        assert child["parent_id"] == 1
        assert child["outline_level"] == 2


class TestResourcesCommand:
    def test_resources_list_outputs_json(self, sample_pod_path):
        result = runner.invoke(app, ["resources", "list", sample_pod_path])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "resources" in data
        assert "count" in data
        assert isinstance(data["resources"], list)


class TestAssignmentsCommand:
    def test_assignments_list_outputs_json(self, sample_pod_path):
        result = runner.invoke(app, ["assignments", "list", sample_pod_path])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "assignments" in data
        assert "count" in data


class TestProjectNameOption:
    def test_convert_sets_project_name(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "renamed.xml"
        result = runner.invoke(
            app,
            # NOTE: convert is a group callback, its options must precede arguments
            ["convert", "--project-name", "Baru", sample_pod_path, str(output_file)],
        )
        assert result.exit_code == 0
        info = runner.invoke(app, ["info", str(output_file)])
        assert info.exit_code == 0
        assert json.loads(info.stdout)["name"] == "Baru"

    def test_convert_without_project_name_keeps_name(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "same.xml"
        result = runner.invoke(app, ["convert", sample_pod_path, str(output_file)])
        assert result.exit_code == 0
        before = json.loads(runner.invoke(app, ["info", sample_pod_path]).stdout)
        after = json.loads(runner.invoke(app, ["info", str(output_file)]).stdout)
        assert after["name"] == before["name"]

    def test_tasks_update_sets_project_name(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "renamed.xml"
        result = runner.invoke(
            app,
            [
                "tasks",
                "update",
                sample_pod_path,
                "1",
                "--project-name",
                "Baru",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        info = runner.invoke(app, ["info", str(output_file)])
        assert json.loads(info.stdout)["name"] == "Baru"


class TestRealPodFile:
    def test_info_reads_real_pod(self, real_pod_path):
        result = runner.invoke(app, ["info", real_pod_path])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["name"] == "testing-file"

    def test_unsupported_file_gives_clean_error(self, tmp_path):
        bad = tmp_path / "bad.pod"
        bad.write_bytes(b"\x00\x01\x02not a project file")
        result = runner.invoke(app, ["info", str(bad)])
        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["code"] == "READ_ERROR"
        assert "NoneType" not in error["error"]

    def test_tasks_list_real_pod(self, real_pod_path):
        result = runner.invoke(app, ["tasks", "list", real_pod_path])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["count"] == 0

    def test_resources_list_real_pod(self, real_pod_path):
        result = runner.invoke(app, ["resources", "list", real_pod_path])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["count"] == 1

    def test_rename_real_pod_to_pod(self, real_pod_path, tmp_path):
        output_file = tmp_path / "renamed.pod"
        result = runner.invoke(
            app,
            [
                "convert",
                "--project-name",
                "Sistem Perpustakaan",
                real_pod_path,
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        info = runner.invoke(app, ["info", str(output_file)])
        assert info.exit_code == 0
        assert json.loads(info.stdout)["name"] == "Sistem Perpustakaan"


class TestTaskValidation:
    def test_rejects_percent_over_100(self, sample_pod_path, tmp_path):
        result = runner.invoke(
            app,
            [
                "tasks",
                "update",
                sample_pod_path,
                "1",
                "--percent-complete",
                "150",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["code"] == "INVALID_VALUE"
        assert not (tmp_path / "o.xml").exists()

    def test_rejects_bad_duration(self, sample_pod_path, tmp_path):
        result = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "X",
                "--duration",
                "lima hari",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert result.exit_code == 1
        assert json.loads(result.stderr)["code"] == "INVALID_VALUE"

    def test_rejects_finish_before_start(self, sample_pod_path, tmp_path):
        result = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "X",
                "--start",
                "2026-12-01",
                "--finish",
                "2026-01-01",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert result.exit_code == 1
        assert json.loads(result.stderr)["code"] == "INVALID_VALUE"

    def test_rejects_bad_date(self, sample_pod_path, tmp_path):
        result = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "X",
                "--start",
                "bukan-tanggal",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert result.exit_code == 1
        assert json.loads(result.stderr)["code"] == "INVALID_VALUE"


class TestAssignUnassign:
    def test_assign_and_list(self, sample_pod_path, tmp_path):
        out = tmp_path / "a.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "assign",
                sample_pod_path,
                "2",
                "2",
                "--units",
                "0.5",
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        data = json.loads(
            runner.invoke(
                app, ["assignments", "list", str(out), "--task-id", "2"]
            ).stdout
        )
        assert data["count"] == 2
        assert 0.5 in [a["units"] for a in data["assignments"]]

    def test_assign_duplicate_rejected(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "assign",
                sample_pod_path,
                "1",
                "1",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"

    def test_assign_bad_units_rejected(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "assign",
                sample_pod_path,
                "2",
                "2",
                "--units",
                "0",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"

    def test_unassign_removes(self, sample_pod_path, tmp_path):
        out = tmp_path / "u.xml"
        r = runner.invoke(
            app, ["tasks", "unassign", sample_pod_path, "1", "1", "--output", str(out)]
        )
        assert r.exit_code == 0
        data = json.loads(
            runner.invoke(
                app, ["assignments", "list", str(out), "--task-id", "1"]
            ).stdout
        )
        assert data["count"] == 0

    def test_unassign_missing(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "unassign",
                sample_pod_path,
                "2",
                "2",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "ASSIGNMENT_NOT_FOUND"


class TestLinkUnlink:
    def test_link_with_lag_roundtrip(self, sample_pod_path, tmp_path):
        out = tmp_path / "l.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "link",
                sample_pod_path,
                "2",
                "1",
                "--type",
                "FS",
                "--lag",
                "2d",
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        preds = json.loads(runner.invoke(app, ["tasks", "get", str(out), "2"]).stdout)[
            "predecessors"
        ]
        assert len(preds) == 1
        assert preds[0]["task_unique_id"] == 1
        assert preds[0]["relation_type"] == "FS"

    def test_link_duplicate_rejected(self, sample_pod_path, tmp_path):
        out = tmp_path / "l.xml"
        runner.invoke(
            app, ["tasks", "link", sample_pod_path, "2", "1", "--output", str(out)]
        )
        r = runner.invoke(
            app,
            ["tasks", "link", str(out), "2", "1", "--output", str(tmp_path / "o.xml")],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"

    def test_link_bad_type_rejected(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "link",
                sample_pod_path,
                "2",
                "1",
                "--type",
                "XX",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"

    def test_unlink_removes(self, sample_pod_path, tmp_path):
        out = tmp_path / "l.xml"
        runner.invoke(
            app, ["tasks", "link", sample_pod_path, "2", "1", "--output", str(out)]
        )
        r = runner.invoke(
            app, ["tasks", "unlink", str(out), "2", "1", "--output", str(out)]
        )
        assert r.exit_code == 0
        preds = json.loads(runner.invoke(app, ["tasks", "get", str(out), "2"]).stdout)[
            "predecessors"
        ]
        assert preds == []

    def test_unlink_missing(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "unlink",
                sample_pod_path,
                "2",
                "1",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "LINK_NOT_FOUND"


class TestMilestone:
    def test_add_milestone(self, sample_pod_path, tmp_path):
        out = tmp_path / "m.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "M1",
                "--milestone",
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        tasks = json.loads(runner.invoke(app, ["tasks", "list", str(out)]).stdout)[
            "tasks"
        ]
        assert next(t for t in tasks if t["name"] == "M1")["milestone"] is True

    def test_update_milestone_toggle(self, sample_pod_path, tmp_path):
        out = tmp_path / "m.xml"
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "update",
                    sample_pod_path,
                    "1",
                    "--milestone",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        assert (
            json.loads(runner.invoke(app, ["tasks", "get", str(out), "1"]).stdout)[
                "milestone"
            ]
            is True
        )
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "update",
                    str(out),
                    "1",
                    "--no-milestone",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        assert (
            json.loads(runner.invoke(app, ["tasks", "get", str(out), "1"]).stdout)[
                "milestone"
            ]
            is False
        )


class TestDiff:
    def test_diff_detects_changes(self, sample_pod_path, tmp_path):
        new = tmp_path / "new.xml"
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "add",
                    sample_pod_path,
                    "--name",
                    "Baru",
                    "--output",
                    str(new),
                ],
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "update",
                    str(new),
                    "1",
                    "--percent-complete",
                    "75",
                    "--project-name",
                    "Ganti",
                    "--output",
                    str(new),
                ],
            ).exit_code
            == 0
        )
        r = runner.invoke(app, ["diff", sample_pod_path, str(new)])
        assert r.exit_code == 0
        d = json.loads(r.stdout)
        assert d["summary"]["tasks_added"] == 1
        assert d["summary"]["tasks_changed"] == 1
        assert d["project_name"] == {"from": "Sample Project", "to": "Ganti"}
        changed = next(c for c in d["tasks_changed"] if c["unique_id"] == 1)
        assert changed["changes"]["percent_complete"] == {"from": 0.0, "to": 75.0}

    def test_diff_identical_files(self, sample_pod_path):
        d = json.loads(
            runner.invoke(app, ["diff", sample_pod_path, sample_pod_path]).stdout
        )
        assert d["summary"] == {
            "tasks_added": 0,
            "tasks_removed": 0,
            "tasks_changed": 0,
            "resources_added": 0,
            "resources_removed": 0,
            "resources_changed": 0,
        }
        assert d["project_name"] is None

    def test_diff_missing_file(self, sample_pod_path, tmp_path):
        r = runner.invoke(app, ["diff", sample_pod_path, str(tmp_path / "no.xml")])
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "FILE_NOT_FOUND"


class TestInPlace:
    def test_in_place_updates_and_backs_up(self, sample_pod_path, tmp_path):
        target = tmp_path / "work.xml"
        target.write_bytes(Path(sample_pod_path).read_bytes())
        r = runner.invoke(
            app,
            [
                "tasks",
                "update",
                str(target),
                "1",
                "--percent-complete",
                "90",
                "--in-place",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["output"] == str(target)
        bak = tmp_path / "work.xml.bak"
        assert bak.exists()
        assert (
            json.loads(runner.invoke(app, ["tasks", "get", str(bak), "1"]).stdout)[
                "percent_complete"
            ]
            == 0.0
        )
        assert (
            json.loads(runner.invoke(app, ["tasks", "get", str(target), "1"]).stdout)[
                "percent_complete"
            ]
            == 90.0
        )

    def test_in_place_conflicts_with_output(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "update",
                sample_pod_path,
                "1",
                "--percent-complete",
                "10",
                "--output",
                str(tmp_path / "o.xml"),
                "--in-place",
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"


class TestImport:
    BATCH = {
        "project_name": "BatchProj",
        "tasks": [
            {"name": "A", "start": "2026-10-12", "duration": "5d"},
            {"name": "B", "duration": "2d", "parent": "A", "resources": ["Alice"]},
            {"name": "M", "milestone": True, "parent": "A"},
        ],
    }

    def _batch_file(self, tmp_path, data):
        p = tmp_path / "batch.json"
        p.write_text(json.dumps(data))
        return str(p)

    def test_import_creates_hierarchy(self, sample_pod_path, tmp_path):
        out = tmp_path / "imp.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "import",
                sample_pod_path,
                self._batch_file(tmp_path, self.BATCH),
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["count"] == 3
        assert len(data["created_unique_ids"]) == 3
        tasks = {
            t["name"]: t
            for t in json.loads(runner.invoke(app, ["tasks", "list", str(out)]).stdout)[
                "tasks"
            ]
        }
        assert tasks["B"]["parent_id"] == tasks["A"]["unique_id"]
        assert tasks["B"]["outline_level"] == 2
        assert tasks["M"]["milestone"] is True
        assert tasks["B"]["resource_names"] == ["Alice"]
        assert (
            json.loads(runner.invoke(app, ["info", str(out)]).stdout)["name"]
            == "BatchProj"
        )

    def test_import_unknown_parent_no_output(self, sample_pod_path, tmp_path):
        out = tmp_path / "imp.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "import",
                sample_pod_path,
                self._batch_file(
                    tmp_path, {"tasks": [{"name": "X", "parent": "Nope"}]}
                ),
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"
        assert not out.exists()

    def test_import_unknown_resource(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "import",
                sample_pod_path,
                self._batch_file(
                    tmp_path, {"tasks": [{"name": "X", "resources": ["Ghost"]}]}
                ),
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"

    def test_import_invalid_json(self, sample_pod_path, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        r = runner.invoke(
            app,
            [
                "tasks",
                "import",
                sample_pod_path,
                str(p),
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"


class TestRoundTrip:
    def test_update_dates_duration_percent(self, sample_pod_path, tmp_path):
        out = tmp_path / "u.xml"
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "update",
                    sample_pod_path,
                    "1",
                    "--start",
                    "2026-11-01",
                    "--finish",
                    "2026-11-15",
                    "--duration",
                    "10d",
                    "--percent-complete",
                    "50",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        task = json.loads(runner.invoke(app, ["tasks", "get", str(out), "1"]).stdout)
        assert task["start"] == "2026-11-01"
        assert task["finish"] == "2026-11-15"
        assert task["duration"] == "10.0d"
        assert task["percent_complete"] == 50.0

    def test_resources_add_update_delete(self, sample_pod_path, tmp_path):
        out = tmp_path / "r.xml"
        r = runner.invoke(
            app,
            [
                "resources",
                "add",
                sample_pod_path,
                "--name",
                "Zed",
                "--email",
                "z@x.com",
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        uid = json.loads(r.stdout)["affected_unique_id"]
        assert uid is not None
        res = json.loads(
            runner.invoke(app, ["resources", "get", str(out), str(uid)]).stdout
        )
        assert res["name"] == "Zed"
        assert (
            runner.invoke(
                app,
                [
                    "resources",
                    "update",
                    str(out),
                    str(uid),
                    "--email",
                    "n@x.com",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        assert (
            json.loads(
                runner.invoke(app, ["resources", "get", str(out), str(uid)]).stdout
            )["email"]
            == "n@x.com"
        )
        assert (
            runner.invoke(
                app, ["resources", "delete", str(out), str(uid), "--output", str(out)]
            ).exit_code
            == 0
        )
        gone = runner.invoke(app, ["resources", "get", str(out), str(uid)])
        assert gone.exit_code == 1
        assert json.loads(gone.stderr)["code"] == "RESOURCE_NOT_FOUND"

    def test_tasks_delete_removes(self, sample_pod_path, tmp_path):
        out = tmp_path / "d.xml"
        assert (
            runner.invoke(
                app, ["tasks", "delete", sample_pod_path, "3", "--output", str(out)]
            ).exit_code
            == 0
        )
        gone = runner.invoke(app, ["tasks", "get", str(out), "3"])
        assert gone.exit_code == 1
        assert json.loads(gone.stderr)["code"] == "TASK_NOT_FOUND"


class TestCliConsistency:
    WRITE_COMMANDS = [
        ["tasks", "add"],
        ["tasks", "update"],
        ["tasks", "delete"],
        ["tasks", "assign"],
        ["tasks", "unassign"],
        ["tasks", "link"],
        ["tasks", "unlink"],
        ["tasks", "import"],
        ["resources", "add"],
        ["resources", "update"],
        ["resources", "delete"],
        ["convert"],
    ]

    def test_write_commands_share_flags(self):
        for cmd in self.WRITE_COMMANDS:
            text = runner.invoke(app, [*cmd, "--help"]).stdout
            assert "--project-name" in text, cmd
            assert "--in-place" in text, cmd
            if cmd != ["convert"]:
                assert "--output" in text, cmd

    def test_error_output_is_single_json(self):
        cases = [
            ["info", "/nonexistent/x.pod"],
            ["tasks", "get", "tests/fixtures/sample.xml", "999"],
            [
                "tasks",
                "update",
                "tests/fixtures/sample.xml",
                "1",
                "--percent-complete",
                "500",
                "--output",
                "/tmp/opencode/nonexistent-dir/o.xml",
            ],
            [
                "tasks",
                "link",
                "tests/fixtures/sample.xml",
                "2",
                "1",
                "--type",
                "XX",
                "--output",
                "/tmp/opencode/o.xml",
            ],
            [
                "tasks",
                "unlink",
                "tests/fixtures/sample.xml",
                "2",
                "1",
                "--output",
                "/tmp/opencode/o.xml",
            ],
            ["diff", "tests/fixtures/sample.xml", "/nonexistent/y.xml"],
        ]
        for args in cases:
            r = runner.invoke(app, args)
            assert r.exit_code == 1, args
            error = json.loads(r.stderr)
            assert set(error) == {"error", "code"}, args


class TestCheck:
    def _mutated(self, tmp_path, mutate, name="broken.xml"):
        import re

        xml = Path("tests/fixtures/sample.xml").read_text()
        out = tmp_path / name
        out.write_text(mutate(xml))
        return str(out)

    def test_clean_file(self, sample_pod_path):
        r = runner.invoke(app, ["check", sample_pod_path])
        assert r.exit_code == 0
        d = json.loads(r.stdout)
        assert d["summary"]["errors"] == 0
        assert d["summary"]["tasks_checked"] == 3

    def test_finish_before_start(self, tmp_path):
        path = self._mutated(
            tmp_path,
            lambda xml: xml.replace(
                "<Start>2025-01-01T09:00:00</Start>",
                "<Start>2025-02-01T09:00:00</Start>",
                1,
            ),
        )
        r = runner.invoke(app, ["check", path])
        assert r.exit_code == 1
        codes = [e["code"] for e in json.loads(r.stdout)["errors"]]
        assert "FINISH_BEFORE_START" in codes

    def test_dangling_link(self, tmp_path):
        link = "<PredecessorLink><PredecessorUID>999</PredecessorUID><Type>1</Type><LinkLag>0</LinkLag></PredecessorLink>"
        path = self._mutated(
            tmp_path,
            lambda xml: xml.replace("</DurationFormat>", "</DurationFormat>" + link, 1),
        )
        r = runner.invoke(app, ["check", path])
        assert r.exit_code == 1
        found = [
            e for e in json.loads(r.stdout)["errors"] if e["code"] == "DANGLING_LINK"
        ]
        assert len(found) == 1 and found[0]["unique_id"] == 1

    def test_self_link(self, tmp_path):
        link = "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type><LinkLag>0</LinkLag></PredecessorLink>"
        path = self._mutated(
            tmp_path,
            lambda xml: xml.replace("</DurationFormat>", "</DurationFormat>" + link, 1),
        )
        r = runner.invoke(app, ["check", path])
        assert r.exit_code == 1
        assert "SELF_LINK" in [e["code"] for e in json.loads(r.stdout)["errors"]]

    def test_percent_out_of_range(self, tmp_path):
        import re

        path = self._mutated(
            tmp_path,
            lambda xml: re.sub(
                r"<PercentComplete>.*?</PercentComplete>",
                "<PercentComplete>150</PercentComplete>",
                xml,
                count=1,
            ),
        )
        r = runner.invoke(app, ["check", path])
        assert r.exit_code == 1
        assert "PERCENT_OUT_OF_RANGE" in [
            e["code"] for e in json.loads(r.stdout)["errors"]
        ]

    def test_broken_hierarchy(self, tmp_path):
        import re

        def mutate(xml):
            blocks = re.findall(r"<Task>.*?</Task>", xml, re.S)
            for i, block in enumerate(blocks):
                if f"<UID>{i + 1}</UID>" in block[:200] and i == 1:
                    patched = block.replace(
                        "<OutlineLevel>1</OutlineLevel>",
                        "<OutlineLevel>5</OutlineLevel>",
                        1,
                    )
                    return xml.replace(block, patched, 1)
            return xml

        r = runner.invoke(app, ["check", self._mutated(tmp_path, mutate)])
        assert r.exit_code == 1
        assert "BROKEN_HIERARCHY" in [e["code"] for e in json.loads(r.stdout)["errors"]]

    def test_duplicate_name_warning(self, sample_pod_path, tmp_path):
        out = tmp_path / "dup.xml"
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "update",
                    sample_pod_path,
                    "2",
                    "--name",
                    "Planning",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        r = runner.invoke(app, ["check", str(out)])
        assert r.exit_code == 0
        assert "DUPLICATE_TASK_NAME" in [
            w["code"] for w in json.loads(r.stdout)["warnings"]
        ]

    def test_unassigned_warning(self, sample_pod_path, tmp_path):
        out = tmp_path / "u.xml"
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "add",
                    sample_pod_path,
                    "--name",
                    "Solo",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        r = runner.invoke(app, ["check", str(out)])
        assert r.exit_code == 0
        assert "UNASSIGNED_TASK" in [
            w["code"] for w in json.loads(r.stdout)["warnings"]
        ]

    def test_cli_rejects_self_link(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "tasks",
                "link",
                sample_pod_path,
                "1",
                "1",
                "--output",
                str(tmp_path / "o.xml"),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"

    def test_missing_file(self, tmp_path):
        r = runner.invoke(app, ["check", str(tmp_path / "no.xml")])
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "FILE_NOT_FOUND"

    def test_percent_update_leaves_no_errors(self, sample_pod_path, tmp_path):
        out = tmp_path / "p.xml"
        assert (
            runner.invoke(
                app,
                [
                    "tasks",
                    "update",
                    sample_pod_path,
                    "1",
                    "--percent-complete",
                    "50",
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        r = runner.invoke(app, ["check", str(out)])
        assert r.exit_code == 0
        assert json.loads(r.stdout)["summary"]["errors"] == 0

    def test_update_start_beyond_finish_rejected(self, sample_pod_path, tmp_path):
        out = tmp_path / "o.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "update",
                sample_pod_path,
                "1",
                "--start",
                "2026-12-01",
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 1
        assert json.loads(r.stderr)["code"] == "INVALID_VALUE"
        assert not out.exists()

    def test_update_start_with_finish_accepted(self, sample_pod_path, tmp_path):
        out = tmp_path / "o.xml"
        r = runner.invoke(
            app,
            [
                "tasks",
                "update",
                sample_pod_path,
                "1",
                "--start",
                "2026-12-01",
                "--finish",
                "2026-12-05",
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        task = json.loads(runner.invoke(app, ["tasks", "get", str(out), "1"]).stdout)
        assert task["start"] == "2026-12-01"
        assert task["finish"] == "2026-12-05"


class TestRun:
    SCRIPT = {
        "project_name": "RunDemo",
        "operations": [
            {
                "op": "add",
                "name": "Fase 1",
                "start": "2026-10-12",
                "duration": "5d",
                "ref": "p1",
            },
            {
                "op": "add",
                "name": "Kickoff",
                "duration": "1d",
                "parent": "p1",
                "ref": "k1",
            },
            {"op": "add", "name": "M1", "milestone": True, "parent": "Fase 1"},
            {"op": "resource_add", "name": "Budi", "ref": "budi"},
            {"op": "assign", "task": "k1", "resource": "budi", "units": 0.5},
            {"op": "link", "task": "M1", "pred": "k1"},
            {"op": "update", "ref": "p1", "percent_complete": 10},
            {"op": "rename", "project_name": "RunFinal"},
        ],
    }

    def _script(self, tmp_path, data):
        p = tmp_path / "run.json"
        p.write_text(json.dumps(data))
        return str(p)

    def test_full_script(self, real_pod_path, tmp_path):
        out = tmp_path / "run.pod"
        r = runner.invoke(
            app,
            [
                "run",
                real_pod_path,
                self._script(tmp_path, self.SCRIPT),
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert [x["op"] for x in data["results"]] == [
            "add",
            "add",
            "add",
            "resource_add",
            "assign",
            "link",
            "update",
            "rename",
        ]
        assert (
            json.loads(runner.invoke(app, ["info", str(out)]).stdout)["name"]
            == "RunFinal"
        )
        tasks = {
            t["name"]: t
            for t in json.loads(runner.invoke(app, ["tasks", "list", str(out)]).stdout)[
                "tasks"
            ]
        }
        assert tasks["Kickoff"]["parent_id"] == tasks["Fase 1"]["unique_id"]
        assert tasks["Kickoff"]["resource_names"] == ["Budi"]
        assert (
            tasks["M1"]["predecessors"][0]["task_unique_id"]
            == tasks["Kickoff"]["unique_id"]
        )
        assert tasks["Fase 1"]["percent_complete"] == 10.0
        assert runner.invoke(app, ["check", str(out)]).exit_code == 0

    def test_atomic_abort_writes_nothing(self, real_pod_path, tmp_path):
        out = tmp_path / "atomic.pod"
        r = runner.invoke(
            app,
            [
                "run",
                real_pod_path,
                self._script(
                    tmp_path,
                    {
                        "operations": [
                            {"op": "add", "name": "OK1"},
                            {"op": "add"},
                            {"op": "add", "name": "Never"},
                        ]
                    },
                ),
                "--output",
                str(out),
            ],
        )
        assert r.exit_code == 1
        error = json.loads(r.stderr)
        assert error["failed_operation"] == 1
        assert not out.exists()

    def test_did_you_mean(self, sample_pod_path, tmp_path):
        r = runner.invoke(
            app,
            [
                "run",
                sample_pod_path,
                self._script(
                    tmp_path,
                    {
                        "operations": [
                            {"op": "assign", "task": "Planing", "resource": "Alice"}
                        ]
                    },
                ),
                "--output",
                str(tmp_path / "o.pod"),
            ],
        )
        assert r.exit_code == 1
        error = json.loads(r.stderr)
        assert error["code"] == "TASK_NOT_FOUND"
        assert "did you mean" in error["error"] and "Planning" in error["error"]

    def test_delete_and_sweep_in_run(self, sample_pod_path, tmp_path):
        out = tmp_path / "r.xml"
        script = {
            "operations": [
                {"op": "link", "task": 2, "pred": 1},
                {"op": "delete", "unique_id": 1},
            ]
        }
        assert (
            runner.invoke(
                app,
                [
                    "run",
                    sample_pod_path,
                    self._script(tmp_path, script),
                    "--output",
                    str(out),
                ],
            ).exit_code
            == 0
        )
        assert runner.invoke(app, ["check", str(out)]).exit_code == 0

    def test_in_place_run(self, real_pod_path, tmp_path):
        target = tmp_path / "w.pod"
        target.write_bytes(Path(real_pod_path).read_bytes())
        r = runner.invoke(
            app,
            [
                "run",
                str(target),
                self._script(tmp_path, {"operations": [{"op": "add", "name": "Solo"}]}),
                "--in-place",
            ],
        )
        assert r.exit_code == 0
        assert (tmp_path / "w.pod.bak").exists()
        assert (
            json.loads(runner.invoke(app, ["info", str(target)]).stdout)["name"]
            == "testing-file"
        )


class TestCliArgOrder:
    def test_options_after_positionals(self, sample_pod_path, tmp_path):
        out = tmp_path / "o.xml"
        r = runner.invoke(
            app, ["convert", sample_pod_path, str(out), "--project-name", "Bebas"]
        )
        assert r.exit_code == 0
        assert (
            json.loads(runner.invoke(app, ["info", str(out)]).stdout)["name"] == "Bebas"
        )

    def test_run_options_after_positionals(self, real_pod_path, tmp_path):
        out = tmp_path / "o.pod"
        script = tmp_path / "r.json"
        script.write_text(json.dumps({"operations": [{"op": "add", "name": "X"}]}))
        r = runner.invoke(
            app, ["run", real_pod_path, str(script), "--output", str(out)]
        )
        assert r.exit_code == 0
