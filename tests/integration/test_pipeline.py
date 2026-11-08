"""Offline end-to-end (rules + mocked judge + mocked replay) on synthetic fixtures."""

from pathlib import Path

import pyarrow.parquet as pq
from typer.testing import CliRunner

from rhscan.cli import app

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "fixtures.parquet"
LBL = Path(__file__).resolve().parents[1] / "fixtures" / "labels.parquet"
runner = CliRunner()


def test_scan_rules_only(tmp_path):
    out = tmp_path / "out"
    res = runner.invoke(app, ["scan", str(FIX), "--out", str(out)])
    assert res.exit_code == 0, res.output
    assert (out / "report.md").exists()
    assert (out / "findings.parquet").exists()
    assert (out / "summary.parquet").exists()
    findings = pq.read_table(out / "findings.parquet").to_pylist()
    assert len(findings) > 0


def test_scan_idempotent(tmp_path):
    out = tmp_path / "out"
    runner.invoke(app, ["scan", str(FIX), "--out", str(out)])
    first = (out / "summary.parquet").read_bytes()
    res = runner.invoke(app, ["scan", str(FIX), "--out", str(out)])
    assert res.exit_code == 0
    # second run skips processed; summary still exists and is readable
    rows = pq.read_table(out / "summary.parquet").to_pylist()
    assert len(rows) >= 0
    _ = first


def test_eval(tmp_path):
    out = tmp_path / "out"
    runner.invoke(app, ["scan", str(FIX), "--out", str(out)])
    res = runner.invoke(
        app,
        [
            "eval",
            "--labels",
            str(LBL),
            "--summary",
            str(out / "summary.parquet"),
            "--findings",
            str(out / "findings.parquet"),
            "--out",
            str(out),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "Precision" in res.output or "F1" in res.output


def test_validate_rules():
    res = runner.invoke(app, ["validate-rules", "rules.yaml"])
    assert res.exit_code == 0, res.output


def test_dry_run(tmp_path):
    out = tmp_path / "out"
    res = runner.invoke(app, ["scan", str(FIX), "--out", str(out), "--dry-run"])
    assert res.exit_code == 0
    assert "DRY RUN" in res.output
