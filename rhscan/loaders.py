"""Parquet loaders: tolerant, streaming, never crash on malformed rows."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import pyarrow.parquet as pq

from rhscan.models import Step, Trajectory

log = logging.getLogger(__name__)


def parse_messages(raw: Any) -> list[Step]:
    """Parse the `messages` field (JSON string or already-parsed list)."""
    data: Any = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [Step(idx=0, role="user", content=raw)]
    if not isinstance(data, list):
        return []
    steps: list[Step] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        tool_calls_raw = item.get("tool_calls") or []
        tool_calls: list[dict[str, Any]] = []
        if isinstance(tool_calls_raw, str):
            try:
                parsed = json.loads(tool_calls_raw)
                tool_calls_raw = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                tool_calls_raw = []
        for tc in tool_calls_raw if isinstance(tool_calls_raw, list) else []:
            if isinstance(tc, dict):
                tool_calls.append(tc)
        steps.append(
            Step(
                idx=i,
                role=str(item.get("role", "")),
                content=str(item.get("content") or ""),
                tool_calls=tool_calls,
                tool_call_id=str(item.get("tool_call_id") or "") or None,
            )
        )
    return steps


def _get(row: dict[str, Any], key: str, default: Any = "") -> Any:
    val = row.get(key, default)
    return default if val is None else val


def _f(row: dict[str, Any], key: str) -> float:
    try:
        return float(_get(row, key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _i(row: dict[str, Any], key: str) -> int:
    try:
        return int(_get(row, key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def row_to_trajectory(row: dict[str, Any]) -> Trajectory:
    return Trajectory(
        run_id=str(_get(row, "run_id")),
        task_id=str(_get(row, "task_id")),
        source=str(_get(row, "source")),
        repo=str(_get(row, "repo")),
        commit=str(_get(row, "commit")),
        docker_image=str(_get(row, "docker_image")),
        teacher_model=str(_get(row, "teacher_model")),
        harness=str(_get(row, "harness")),
        harness_version=str(_get(row, "harness_version")),
        attempt=_i(row, "attempt"),
        steps=parse_messages(_get(row, "messages", "[]")),
        reward=_f(row, "reward"),
        tests_passed=_i(row, "tests_passed"),
        tests_failed=_i(row, "tests_failed"),
        patch=str(_get(row, "patch")),
        n_steps=_i(row, "n_steps"),
        n_input_tokens=_i(row, "n_input_tokens"),
        n_output_tokens=_i(row, "n_output_tokens"),
        cost_usd=_f(row, "cost_usd"),
        wall_time_s=_f(row, "wall_time_s"),
        error=str(_get(row, "error")),
        started_at=str(_get(row, "started_at")),
        finished_at=str(_get(row, "finished_at")),
        raw_log_path=str(_get(row, "raw_log_path")),
    )


def iter_trajectories(
    path: str, batch_size: int = 256, stats: dict[str, int] | None = None
) -> Iterator[Trajectory]:
    """Stream trajectories from Parquet in batches; log & count bad rows."""
    if stats is not None:
        stats.setdefault("ok", 0)
        stats.setdefault("bad", 0)
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=batch_size):
        rows = batch.to_pylist()
        for row in rows:
            try:
                traj = row_to_trajectory(row)
            except Exception as exc:  # never crash a whole scan on one row
                log.warning("skipping malformed row: %s", exc)
                if stats is not None:
                    stats["bad"] += 1
                continue
            if stats is not None:
                stats["ok"] += 1
            yield traj


def write_parquet(rows: list[dict[str, Any]], path: str) -> None:
    import pyarrow as pa

    if not rows:
        schema = pa.schema([])
        pq.write_table(pa.Table.from_arrays([], schema=schema), path)
        return
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)
