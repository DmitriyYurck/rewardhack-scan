"""Benchmark-generator tests: determinism, label truth, patch validity."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from benchgen.gen import generate, make_patch, run_reward
from benchgen.tasks import TASKS


def test_determinism_by_seed():
    a_rows, a_labels = generate(seed=42, n_per_class=2)
    b_rows, b_labels = generate(seed=42, n_per_class=2)
    assert a_rows == b_rows
    assert a_labels == b_labels


def test_different_seed_differs():
    a_rows, _ = generate(seed=42, n_per_class=2)
    b_rows, _ = generate(seed=43, n_per_class=2)
    assert a_rows != b_rows


def test_labels_match_construction():
    rows, labels = generate(seed=42, n_per_class=2)
    assert len(rows) == len(labels)
    for traj, lab in zip(rows, labels, strict=True):
        assert traj["run_id"] == lab["run_id"]
        assert traj["source"] == lab["source"]
        assert traj["task_id"] == lab["task_id"]
        # hack label is derived from class, which ground truth knows
        assert lab["hack"] == (lab["category"] is not None)
        if lab["hack"]:
            assert lab["hack_step_idx"] is not None
            assert lab["subtlety"] in ("blatant", "moderate", "obfuscated")
        assert lab["split"] in ("dev", "test", "adversarial")


def test_patch_applies_cleanly():
    """Every patch transforms before-state into after-state via `patch`.

    We verify by applying each generated patch with git apply in a scratch
    copy of the task repo and diffing against before+after file dicts.
    """
    task = TASKS[0]
    before = dict(task.files)
    after = dict(task.files)
    after[task.main_module] = task.fix_files[task.main_module]
    patch = make_patch(before, after)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for path, content in before.items():
            p = root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=root,
            input=patch,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        for path, content in after.items():
            assert (root / path).read_text() == content


def test_honest_fix_actually_passes_visible_tests():
    task = TASKS[0]
    after = dict(task.files)
    after.update(task.fix_files)
    reward, passed, _ = run_reward(after, task.hidden_tests)
    assert reward == 1.0 and passed > 0


def test_buggy_state_fails_visible_tests():
    task = TASKS[0]
    reward, _, failed = run_reward(dict(task.files), task.hidden_tests)
    assert reward == 0.0 and failed > 0


def test_loader_roundtrip():
    from rhscan.loaders import row_to_trajectory

    rows, _ = generate(seed=42, n_per_class=1)
    traj = row_to_trajectory(rows[0])
    assert traj.run_id == rows[0]["run_id"]
    assert traj.steps[0].role == "user"


def test_hard_negative_presence():
    _, labels = generate(seed=42, n_per_class=10)
    honest = [lab for lab in labels if not lab["hack"]]
    hn = [lab for lab in honest if lab["hard_negative"]]
    assert honest, "no honest rows"
    assert len(hn) / len(honest) >= 0.3
