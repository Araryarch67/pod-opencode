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
    def test_convert_rejects_pod_output(self, sample_pod_path, tmp_path):
        output_file = tmp_path / "output.pod"
        result = runner.invoke(app, ["convert", sample_pod_path, str(output_file)])
        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["code"] == "INVALID_OUTPUT_FORMAT"

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

    def test_tasks_get_nonexistent(self, sample_pod_path):
        result = runner.invoke(app, ["tasks", "get", sample_pod_path, "999"])
        assert result.exit_code == 1

    def test_tasks_add_rejects_pod_output(self, sample_pod_path, tmp_path):
        result = runner.invoke(
            app,
            [
                "tasks",
                "add",
                sample_pod_path,
                "--name",
                "Test Task",
                "--output",
                str(tmp_path / "out.pod"),
            ],
        )
        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["code"] == "INVALID_OUTPUT_FORMAT"


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
        assert isinstance(data["assignments"], list)
