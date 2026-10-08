import pytest
import json
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def jvm_setup_teardown():
    """Start JVM once at session start, tear down at session end."""
    from pod_opencode.jvm import start_jvm, shutdown_jvm

    start_jvm()
    yield
    shutdown_jvm()


@pytest.fixture
def sample_pod_path():
    """Return path to sample XML fixture (MSPDI format)."""
    path = Path(__file__).parent / "fixtures" / "sample.xml"
    if not path.exists():
        pytest.skip("Sample fixture not found")
    return str(path)


@pytest.fixture
def real_pod_path():
    """Return path to a real ProjectLibre .pod fixture."""
    path = Path(__file__).parent / "fixtures" / "real.pod"
    if not path.exists():
        pytest.skip("Real POD fixture not found")
    return str(path)
