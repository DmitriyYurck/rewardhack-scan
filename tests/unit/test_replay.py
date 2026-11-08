import pytest

from rhscan.models import Trajectory
from rhscan.replay import ReplayResult, replay_trajectory, strip_test_changes


class FakeRunner:
    def __init__(self, passed: bool) -> None:
        self.passed = passed
        self.last_patch = ""

    def run(self, image: str, patch: str, test_command: str, timeout_s: int, network: bool):
        self.last_patch = patch
        return ReplayResult(attempted=True, tests_passed=self.passed)


def test_strip_test_changes():
    patch = (
        "diff --git a/src.py b/src.py\n--- a/src.py\n+++ b/src.py\n@@ -1 +1 @@\n-x=1\n+x=2\n"
        "diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ b/tests/t.py\n@@ -1 +1 @@\n-a=1\n+assert True\n"
    )
    out = strip_test_changes(patch)
    assert "src.py" in out
    assert "test" not in out.lower() or "assert True" not in out


def test_replay_confirms():
    t = Trajectory(
        run_id="r",
        attempt=0,
        reward=1.0,
        docker_image="img",
        patch="diff --git a/tests/t.py b/tests/t.py\n--- a/t\n+++ b/t\n@@ -1 +1 @@\n-a\n+assert True\n",
    )
    result, finding = replay_trajectory(t, FakeRunner(passed=False))
    assert result.reward_disappeared
    assert finding is not None and finding.layer == "replay"


def test_replay_not_confirmed_when_tests_pass():
    t = Trajectory(run_id="r", attempt=0, reward=1.0, docker_image="img", patch="x")
    result, finding = replay_trajectory(t, FakeRunner(passed=True))
    assert not result.reward_disappeared
    assert finding is None


def test_replay_skips_no_image():
    t = Trajectory(run_id="r", attempt=0, reward=1.0, patch="x")
    result, finding = replay_trajectory(t, FakeRunner(passed=False))
    assert not result.attempted
    assert finding is None


@pytest.mark.docker
def test_replay_against_real_bench_task_image():
    """End-to-end replay with a real Docker image (skipped without daemon)."""
    import shutil

    from rhscan.loaders import iter_trajectories
    from rhscan.replay import SubprocessDockerRunner, replay_trajectory

    if shutil.which("docker") is None:
        pytest.skip("docker not installed")
    rows = list(iter_trajectories("bench/trajectories.parquet"))
    if not rows:
        pytest.skip("bench/trajectories.parquet not generated")

    traj = rows[0]
    if traj.reward <= 0:
        pytest.skip("first bench trajectory has reward 0")
    result, _ = replay_trajectory(
        traj,
        SubprocessDockerRunner(),
        "python -m pytest tests/ -q --tb=no -p no:cacheprovider",
        timeout_s=120,
        network=False,
    )
    assert result.attempted
