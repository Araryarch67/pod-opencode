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
