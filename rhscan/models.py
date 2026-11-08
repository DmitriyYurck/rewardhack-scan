"""Pydantic models for trajectories, findings, and summaries."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Source = Literal["tbench", "swesmith", "r2e"]
Category = Literal[
    "test_tampering",
    "hardcoding",
    "verifier_evasion",
    "solution_leak",
    "false_reporting",
]
Layer = Literal["rules", "judge", "replay"]
Verdict = Literal["clean", "rules_only", "judge_only", "confirmed_by_replay"]


class Step(BaseModel):
    idx: int = 0
    role: str = ""
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_call_id: str | None = None


class Trajectory(BaseModel):
    run_id: str = ""
    task_id: str = ""
    source: str = ""
    repo: str = ""
    commit: str = ""
    docker_image: str = ""
    teacher_model: str = ""
    harness: str = ""
    harness_version: str = ""
    attempt: int = 0
    steps: list[Step] = Field(default_factory=list)
    reward: float = 0.0
    tests_passed: int = 0
    tests_failed: int = 0
    patch: str = ""
    n_steps: int = 0
    n_input_tokens: int = 0
    n_output_tokens: int = 0
    cost_usd: float = 0.0
    wall_time_s: float = 0.0
    error: str = ""
    started_at: str = ""
    finished_at: str = ""
    raw_log_path: str = ""

    @property
    def key(self) -> tuple[str, int]:
        return (self.run_id, self.attempt)


class Finding(BaseModel):
    run_id: str = ""
    attempt: int = 0
    category: str = ""
    severity: str = "medium"
    layer: Layer = "rules"
    rule_id: str = ""
    step_idx: int = -1
    evidence: str = ""
    confidence: float = 0.0


class AttemptSummary(BaseModel):
    run_id: str = ""
    attempt: int = 0
    task_id: str = ""
    source: str = ""
    teacher_model: str = ""
    reward: float = 0.0
    hack_score: float = 0.0
    verdict: Verdict = "clean"
    n_findings: int = 0
    categories: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class EvalMetrics(BaseModel):
    scope: str = ""
    layer: str = ""
    category: str = ""
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    n: int = 0
    split: str = ""
    subtlety: str = ""
    source: str = ""
    hard_negative: str = ""
