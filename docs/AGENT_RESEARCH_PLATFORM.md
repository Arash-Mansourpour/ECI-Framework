# Agent and research evaluation platform

This increment adds a real provider boundary for agent decisions, evidence-aware
research cycles, and paired benchmark reports. Model access is optional; the
deterministic `demo` policy remains available for offline tests.

## Run an agent

The CLI can use any OpenAI Chat Completions-compatible endpoint. Credentials are
read from `ECI_LLM_API_KEY` or `OPENAI_API_KEY`; they are not accepted as
command-line arguments or written into run records.

```powershell
$env:ECI_LLM_API_KEY = "..."
python -m eci agent --provider openai-compatible --model gpt-4o-mini `
  --goal "Use the available tools to add 20 and 22" --steps 6 --budget 50
```

For a local compatible server, set `ECI_LLM_BASE_URL` (for example,
`http://localhost:11434/v1`). A local endpoint may omit an API key. The model
must return a JSON decision with `tool`, `args`, `done`, `answer`, and optional
`thought`. Tool names are checked against the registry before execution. A
provider or policy failure ends the run without invoking a tool. Episodic
history is kept in memory and scoped by namespace plus `agent_id`; it is not
durable storage.

Python callers may inject a custom policy or provider without depending on a
specific model vendor:

```python
import asyncio
from eci.agents import Agents, OpenAICompatiblePolicy

agents = Agents()
policy = OpenAICompatiblePolicy(model="local-model", base_url="http://localhost:11434/v1")
result = asyncio.run(agents.loop.run(
    "Compute 20 + 22", policy_fn=policy, agent_id="researcher-1"))
```

## Resolve research outcomes honestly

`ResearchLoop.run_cycle` now requires both a binary resolved label and its
source. It evaluates every supplied canary case, records drill failures,
rejects non-finite/out-of-range scores, and does not synthesize reviewer votes
by default. Inject a real reviewer/DAO voting adapter to approve a proposal.
Synthetic voting is deliberately opt-in for fixtures and demos:

```python
from eci.research import ResearchLoop

loop = ResearchLoop(vote_fn=my_reviewer_adapter)
hypothesis = loop.propose("candidate improves held-out accuracy", 0.7,
                          {"candidate": "v2"})
result = loop.run_cycle(
    hypothesis,
    drill=evaluate_candidate,
    canary_payloads=held_out_cases,
    outcome=1,
    outcome_source="benchmark-2026-09:labels.jsonl#claim-17",
)
```

The source string is provenance supplied by the caller, not an independent
proof that the label is correct. Demo call sites identify their synthetic
fixtures explicitly. `OuterLoop` additionally requires each task to include a
stable `drill_id`; it records a content hash for the resolved task suite and
only adopts a verified strict improvement in combined Brier + decision loss
when every cycle is approved. Missing labels, sources, drills, or drill IDs
stop the round instead of quietly assuming a positive outcome. Use
`ResearchLoop.export_json()` or `OuterLoop.export_json()` to persist audit
records from a run.

## Compare research candidates

The comparison harness runs baseline and candidate against the same suite and
seed set, supports sync and async candidates, keeps failures in the denominator,
and reports per-case paired deltas, score means, bootstrap 95% intervals,
latency, suite SHA-256, seeds, Python version, and platform. Scores and scorer
outputs are normalized to `[0, 1]`. Confidence intervals use a paired, two-way
bootstrap over cases and seeds. Scorer configuration is included in the suite
hash; changing a scorer setting, suite version, or case changes that hash.
Candidate metadata records model, prompt, and code revisions alongside scores.

Example suite (`suite.json`):

```json
{
  "name": "arithmetic-agent",
  "version": "1.0.0",
  "scorer": "exact-match-v1",
  "cases": [
    {"case_id": "sum-1", "input": {"a": 20, "b": 22}, "expected": 42},
    {"case_id": "sum-2", "input": {"a": -3, "b": 8}, "expected": 5}
  ]
}
```

Candidate functions live in importable Python modules and accept
`(input_dict, seed)`:

```powershell
python -m eci compare --suite suite.json `
  --baseline baselines:add_v1 --candidate candidates:add_v2 `
  --seeds 0,1,2,3,4 `
  --baseline-metadata '{"revision":"release-1"}' `
  --candidate-metadata '{"model":"local-model-v2","temperature":0}' `
  --output results/add-v2.json
```

Equivalent Python API (including async agent runners):

```python
from eci.benchmarking import BenchmarkCase, BenchmarkSuite, compare

suite = BenchmarkSuite(
    name="arithmetic-agent", version="1.0.0",
    cases=(BenchmarkCase("sum-1", {"a": 20, "b": 22}, 42),),
)
report = compare(suite, "baseline-v1", baseline, "candidate-v2", candidate,
                 seeds=[0, 1, 2, 3, 4])
report.to_json("results/comparison.json")
```

Pass an EventBus with `bus=...` when you also want a
`benchmark.comparison.completed` event routed into the neural fabric.

Seeds are passed to candidate functions; the harness cannot make a remote model
deterministic if its provider ignores them. For statistically meaningful
research, use a frozen/versioned suite, enough independent cases and seeds,
and report external data provenance alongside the generated JSON artifact.
