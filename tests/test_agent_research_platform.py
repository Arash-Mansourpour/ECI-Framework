from __future__ import annotations

import json

import pytest


class _Response:
    def __init__(self, body: dict):
        self.body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_openai_compatible_policy_sends_structured_request_and_validates_tool():
    from eci.agents import AgentState, OpenAICompatiblePolicy

    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return _Response({"choices": [{"message": {"content": json.dumps({
            "thought": "use the safe tool", "tool": "echo", "args": {"text": "hello"},
            "done": False, "answer": "",
        })}}]})

    policy = OpenAICompatiblePolicy("test-model", "http://localhost/v1", "secret",
                                    timeout_s=4, opener=opener)
    state = AgentState(goal="say hello", history=[{"role": "user", "content": "previous"}],
                       available_tools=[{"name": "echo", "params": {"text": "str"}}])
    result = policy(state, ["echo"])

    request, timeout = requests[0]
    payload = json.loads(request.data)
    assert request.full_url == "http://localhost/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer secret"
    assert timeout == 4
    assert payload["response_format"] == {"type": "json_object"}
    assert "previous" in payload["messages"][1]["content"]
    assert result["tool"] == "echo" and result["args"] == {"text": "hello"}


def test_openai_compatible_policy_rejects_invalid_or_unavailable_actions():
    from eci.agents import AgentState, ModelProviderError, OpenAICompatiblePolicy

    policy = OpenAICompatiblePolicy(
        "test-model", opener=lambda *_args, **_kwargs: _Response({
            "choices": [{"message": {"content": json.dumps({
                "tool": "delete_everything", "args": {}, "done": False,
            })}}]
        }),
    )
    with pytest.raises(ModelProviderError, match="unavailable tool"):
        policy(AgentState(goal="test"), ["echo"])


def test_agent_memory_is_session_scoped_and_policy_errors_do_not_run_tools():
    import asyncio

    from eci.agents import Agents

    agents = Agents()

    async def run():
        return await agents.loop.run(
            "greet", agent_id="agent-a", policy_fn=lambda _state, _tools: {
                "tool": "not-registered", "args": {}, "done": False,
            })

    result = asyncio.run(run())
    assert result["ok"] is False
    assert result["steps"][0]["blocked"] == "unknown-tool"
    assert agents.memory.last(session="default:agent-a")[0]["content"] == "greet"
    assert agents.memory.last(session="default:agent-b") == []


def test_agent_safety_checks_fail_closed_on_quota_and_economy_errors():
    import asyncio

    from eci.agents import AgentLoop, ToolRegistry

    tools = ToolRegistry()
    tools.register("echo", lambda args, _ctx: args, params={"text": "str"})
    policy = lambda _state, _tools: {"tool": "echo", "args": {"text": "x"}, "done": False}

    class BrokenQuota:
        def admit(self, *_args, **_kwargs):
            raise RuntimeError("quota backend down")

    quota_loop = AgentLoop(tools=tools, tenancy=BrokenQuota())
    quota_result = asyncio.run(quota_loop.run("goal", policy_fn=policy))
    assert quota_result["steps"][0]["blocked"] == "tenancy-error"
    assert tools.health()["calls"]["echo"] == 0

    class BrokenEconomy:
        def charge(self, *_args, **_kwargs):
            raise RuntimeError("economy backend down")

    economy_loop = AgentLoop(tools=tools, economy=BrokenEconomy())
    economy_result = asyncio.run(economy_loop.run("goal", policy_fn=policy))
    assert economy_result["steps"][0]["blocked"] == "budget-check-error"
    assert tools.health()["calls"]["echo"] == 0


def test_agent_policy_receives_subsystem_neural_attention_from_shared_bus():
    import asyncio

    from eci.agents import Agents
    from eci.kernel.bus import Event, EventBus

    bus = EventBus()
    agents = Agents(bus=bus)
    bus.publish(Event(
        type="brain.subsystem.signal", source="brain-neural-fabric",
        payload={"subsystem": "research-loop", "attention": 0.83},
    ))
    seen = {}

    def policy(state, _tools):
        seen.update(state.neural_attention)
        return {"tool": None, "args": {}, "done": True, "answer": "observed"}

    result = asyncio.run(agents.loop.run("continue", policy_fn=policy))
    assert seen["research-loop"] == pytest.approx(0.83)
    assert result["neural_attention"]["research-loop"] == pytest.approx(0.83)


def test_research_requires_resolved_label_source_and_explicit_voting():
    from eci.research import ResearchLoop

    loop = ResearchLoop()
    hypothesis = loop.propose("candidate improves", 0.8, {"score": 0.9}, hid="h-1")
    with pytest.raises(ValueError, match="resolved binary label"):
        loop.run_cycle(hypothesis, drill=lambda payload: payload["score"])
    with pytest.raises(ValueError, match="outcome_source"):
        loop.run_cycle(hypothesis, drill=lambda payload: payload["score"], outcome=1)

    result = loop.run_cycle(
        hypothesis, drill=lambda payload: payload["score"], outcome=1,
        outcome_source="dataset-v1:case-1",
    )
    assert result.brier == pytest.approx(0.04)
    assert result.approved is False
    assert result.vote_source == "no-reviewer"
    assert result.outcome_source == "dataset-v1:case-1"


def test_research_uses_all_canaries_and_records_drill_failures_and_real_votes():
    from eci.research import ResearchLoop

    called = []

    def drill(payload):
        called.append(payload["id"])
        if payload["id"] == "bad":
            raise RuntimeError("fixture failure")
        return payload["score"]

    loop = ResearchLoop(vote_fn=lambda _hyp, _scores: {"reviewer-a": 1, "reviewer-b": 1})
    hyp = loop.propose("evaluate", 0.9, {"id": "train", "score": 0.9})
    result = loop.run_cycle(
        hyp, drill, canary_payloads=[{"id": f"case-{i}", "score": 0.8} for i in range(8)]
        + [{"id": "bad", "score": 1.0}], outcome=1,
        outcome_source="heldout-v2:labels.jsonl",
    )
    assert len(called) == 10  # one twin + all nine canaries
    assert result.approved is False and result.vote_source == "configured-reviewer"
    assert len(result.drill_failures) == 1
    assert result.policy_loss == 1.0  # resolved positive, but failed drill blocks approval
    assert result.canary_score == pytest.approx(8 * 0.8 / 9)


def test_research_rejects_invalid_scores_and_forecasts():
    from eci.research import Hypothesis, ResearchLoop

    with pytest.raises(ValueError, match="predicted_prob"):
        Hypothesis("h", "claim", float("nan"))
    loop = ResearchLoop()
    hypothesis = loop.propose("claim", 0.5)
    result = loop.run_cycle(hypothesis, lambda _payload: 1.2, outcome=1,
                            outcome_source="test-label")
    assert result.drill_failures
    assert result.twin_score == 0.0


def test_research_and_recursive_results_export_auditable_json(tmp_path):
    from eci.recursion import OuterLoop
    from eci.research import ResearchLoop

    research = ResearchLoop(vote_fn=lambda _hyp, _scores: {"reviewer": 1})
    hyp = research.propose("claim", 0.8, {"x": 0.9}, hid="export-1")
    research.run_cycle(hyp, lambda payload: payload["x"], outcome=1,
                       outcome_source="fixture:labels#1")
    result_path = tmp_path / "research.json"
    research.export_json(result_path)
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assert data["results"][0]["outcome_source"] == "fixture:labels#1"
    assert data["mean_objective"] == pytest.approx(0.04)

    outer = OuterLoop(lambda params: ResearchLoop(quorum=params["quorum"]))
    round_result = outer.run_round([{
        "claim": "candidate works", "prob": 0.8, "payload": {"x": 0.9},
        "drill": lambda payload: payload["x"], "drill_id": "score-v1",
        "outcome": 1, "outcome_source": "fixture:labels#1", "simulate_votes": True,
    }], verifier=lambda state: state["dataset_sha256"] != "")
    assert round_result["dataset_sha256"]
    assert round_result["adopted"] is True
    outer_path = tmp_path / "outer.json"
    outer.export_json(outer_path)
    assert json.loads(outer_path.read_text(encoding="utf-8"))["rounds"][0]["adopted"] is True


def test_self_improvement_does_not_adopt_without_votes_or_on_unverified_round():
    from eci.recursion import OuterLoop
    from eci.research import ResearchLoop

    outer = OuterLoop(lambda params: ResearchLoop(quorum=params["quorum"]))
    task = {"claim": "candidate", "prob": 0.9, "payload": {"x": 0.9},
            "drill": lambda payload: payload["x"], "drill_id": "score-v1",
            "outcome": 1, "outcome_source": "fixture:labels#1"}
    result = outer.run_round([task], verifier=lambda _state: True)
    assert result["verified"] is True
    assert result["approved_cycles"] == 0
    assert result["adopted"] is False
    assert outer.to_dict()["best_objective"] is None


def test_paired_benchmark_uses_same_cases_and_seeds_with_suite_fingerprint():
    from eci.benchmarking import BenchmarkCase, BenchmarkSuite, compare

    suite = BenchmarkSuite(
        name="tiny-arithmetic", version="1.0",
        cases=(
            BenchmarkCase("one", {"x": 1}, 2),
            BenchmarkCase("two", {"x": 2}, 3),
        ),
    )
    baseline = lambda inputs, _seed: inputs["x"]
    candidate = lambda inputs, _seed: inputs["x"] + 1
    report = compare(suite, "baseline-v1", baseline, "candidate-v2", candidate,
                     seeds=[0, 1, 2],
                     candidate_metadata={"model": "fixture-v2", "temperature": 0})

    assert report.baseline["mean_score"] == 0.0
    assert report.candidate["mean_score"] == 1.0
    assert report.paired["mean_delta"] == 1.0
    assert report.paired["candidate_wins"] == 6
    assert report.paired["n_pairs"] == 6
    assert len(report.suite["sha256"]) == 64
    serialized = json.loads(report.to_json())
    assert serialized["schema_version"] == 1
    assert serialized["suite"]["sha256"] == report.suite["sha256"]
    assert serialized["candidate"]["metadata"]["model"] == "fixture-v2"

    configured = BenchmarkSuite(
        name="tiny-arithmetic", version="1.0",
        cases=suite.cases, scorer_id="numeric-tolerance-v1",
        scorer_config={"tolerance": 0.5},
    )
    configured_changed = BenchmarkSuite(
        name="tiny-arithmetic", version="1.0",
        cases=suite.cases, scorer_id="numeric-tolerance-v1",
        scorer_config={"tolerance": 0.25},
    )
    assert configured.fingerprint() != configured_changed.fingerprint()


def test_benchmark_records_candidate_failures_instead_of_dropping_cases():
    from eci.benchmarking import BenchmarkCase, BenchmarkSuite, compare

    suite = BenchmarkSuite("failure-test", "1", (BenchmarkCase("case", {}, "ok"),))

    def broken(_input, _seed):
        raise RuntimeError("candidate failed")

    report = compare(suite, "baseline", lambda _input, _seed: "ok",
                     "broken", broken)
    assert report.candidate["failures"] == 1
    assert report.candidate["mean_score"] == 0.0
    assert report.observations[0]["candidate_error"].startswith("RuntimeError")


def test_async_benchmark_candidate_is_supported():
    import asyncio

    from eci.benchmarking import BenchmarkCase, BenchmarkSuite, compare_async

    suite = BenchmarkSuite("async-test", "1", (BenchmarkCase("case", {"n": 3}, 3),))

    async def candidate(inputs, seed):
        await asyncio.sleep(0)
        return inputs["n"] + seed

    report = asyncio.run(compare_async(
        suite, "baseline", lambda inputs, _seed: inputs["n"],
        "async", candidate, seeds=[0],
    ))
    assert report.candidate["mean_score"] == 1.0


def test_compare_cli_loads_candidates_and_writes_machine_readable_report(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    from eci.__main__ import main

    baseline_module = ModuleType("test_benchmark_baseline")
    baseline_module.solve = lambda inputs, _seed: inputs["x"]
    candidate_module = ModuleType("test_benchmark_candidate")
    candidate_module.solve = lambda inputs, _seed: inputs["x"] + 1
    monkeypatch.setitem(sys.modules, baseline_module.__name__, baseline_module)
    monkeypatch.setitem(sys.modules, candidate_module.__name__, candidate_module)
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps({
        "name": "cli-arithmetic", "version": "1", "scorer": "exact-match-v1",
        "cases": [{"case_id": "sum", "input": {"x": 41}, "expected": 42}],
    }), encoding="utf-8")
    output_path = tmp_path / "report.json"

    assert main([
        "compare", "--suite", str(suite_path),
        "--baseline", "test_benchmark_baseline:solve",
        "--candidate", "test_benchmark_candidate:solve",
        "--candidate-metadata", '{"revision":"test-v2"}',
        "--seeds", "0,1", "--output", str(output_path),
    ]) == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["paired"]["mean_delta"] == 1.0
    assert report["suite"]["name"] == "cli-arithmetic"
    assert report["candidate"]["metadata"]["revision"] == "test-v2"


def test_agents_research_verification_and_benchmarks_join_the_same_neural_bus():
    from eci.benchmarking import BenchmarkCase, BenchmarkSuite, compare
    from eci.brain import BrainMesh, SubsystemNeuralFabric
    from eci.kernel.bus import EventBus
    from eci.research import ResearchLoop
    from eci.verification import Claim, VerificationGate

    bus = EventBus()
    fabric = SubsystemNeuralFabric(BrainMesh(per_region=2, ticks=1, seed=4), bus=bus, seed=4)
    research = ResearchLoop(bus=bus, vote_fn=lambda _hyp, _scores: {"reviewer": 1})
    hypothesis = research.propose("verified quality", 0.9, {"score": 0.9}, hid="mesh-hyp")
    research.run_cycle(hypothesis, lambda payload: payload["score"], outcome=1,
                       outcome_source="fixture:label#1")
    gate = VerificationGate(bus=bus)
    gate.evaluate(Claim("mesh-claim", "fixture passes", lambda: {"ok": True}))
    suite = BenchmarkSuite("mesh-bench", "1", (BenchmarkCase("one", {"x": 1}, 1),))
    compare(suite, "baseline", lambda inputs, _seed: inputs["x"],
            "candidate", lambda inputs, _seed: inputs["x"], bus=bus)

    assert {"research-loop", "verification-gate", "benchmark.compare"} <= set(fabric.nodes)
    assert fabric.event_count == 4  # proposal, resolved cycle, verification, comparison
    output = fabric.tick()
    assert output["fabric"]["nodes"] >= 3
