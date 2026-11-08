import json

from rhscan.judge import Judge, estimate_cost, validate_judge_json
from rhscan.models import Step, Trajectory


class FakeClient:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.calls = 0

    def complete(self, model: str, prompt: str) -> str:
        self.calls += 1
        return self.raw


def test_validate_good():
    v = validate_judge_json('{"verdict":"hack","category":"hardcoding","confidence":0.8}')
    assert v.verdict == "hack"


def test_validate_bad_raises():
    try:
        validate_judge_json("not json")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_judge_agreement(tmp_path):
    raw = json.dumps({"verdict": "hack", "category": "hardcoding", "confidence": 0.9, "quote": "q"})
    judge = Judge(FakeClient(raw), "m", tmp_path)
    t = Trajectory(run_id="r", attempt=0, patch="x", steps=[Step(idx=0, content="hi")])
    f = judge.judge(t)
    assert f is not None and f.confidence == 0.9


def test_judge_clean(tmp_path):
    raw = json.dumps({"verdict": "clean", "confidence": 0.9})
    judge = Judge(FakeClient(raw), "m", tmp_path)
    t = Trajectory(run_id="r", attempt=0, patch="x", steps=[])
    assert judge.judge(t) is None


def test_cache_hits(tmp_path):
    raw = json.dumps({"verdict": "clean", "confidence": 0.9})
    client = FakeClient(raw)
    judge = Judge(client, "m", tmp_path)
    t = Trajectory(run_id="r", attempt=0, patch="x", steps=[])
    judge.judge(t)
    calls = client.calls
    judge.judge(t)
    assert client.calls == calls  # cached, no new calls


def test_estimate_cost():
    t = Trajectory(run_id="r", attempt=0, patch="x" * 100, steps=[])
    c = estimate_cost(t)
    assert c >= 0


def test_fake_judge_is_deterministic():
    from rhscan.judge import FakeJudge

    fj = FakeJudge("hack")
    out1 = fj.complete("m", "prompt")
    out2 = fj.complete("m", "prompt")
    assert out1 == out2
    v = validate_judge_json(out1)
    assert v.verdict == "hack"


def test_judge_with_fake_client_plumbing(tmp_path):
    from rhscan.judge import FakeJudge

    judge = Judge(FakeJudge("hack"), "fake-model", tmp_path)
    t = Trajectory(run_id="r", attempt=0, patch="x", steps=[Step(idx=0, content="hi")])
    f = judge.judge(t)
    assert f is not None and f.layer == "judge"
