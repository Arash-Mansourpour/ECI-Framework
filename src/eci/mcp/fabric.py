"""Default Omniverse toolset: the whole framework as MCP tools.

Namespaces
  p0.*            obedience layer (attest/check/spec/ledger) + legacy p0_* aliases
  system.*        info / status / gateway schema
  quantum.*       supremacy suite / field / transpile / zne / backend demo
  consciousness.* profile / pyphi-xval / eeg-loop / adherence-train
  network.*       simulate / tcp-probe / secure-channel
  workflow.*      DAG demo slice
  agent.*         ReAct run / tool manifest / memory store+recall
  dao.*           propose / vote / tally (+ treasury.* fund/allocate/spend/advance/status)
  eval.*          golden gates
  supply.*        SBOM
  twin.*          what-if simulation (also powers dry_run)
  chaos.*         fault-plan run
  aik.*           unification layer: {quantum,phi,agent,noisy}.{posterior,update,
                  free_energy} on ONE GenerativeState schema + ledger.{shares,total}

Every handler is (args, ctx) -> JSON-safe data and raises on failure so
the pipeline converts it to structured {ok:false} envelopes.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_default_registry"]


def build_default_registry(framework: Any, registry=None):
    from eci.mcp.registry import McpRegistry
    reg = registry or McpRegistry()
    F = framework

    def T(name, desc, params, fn, **kw):
        from eci.mcp.registry import McpTool
        from eci.mcp.schema import build_input_schema
        reg.register(McpTool(name=name, description=desc, handler=fn,
                             inputSchema=build_input_schema(params, **{k: v for k, v in kw.items() if k in ("required", "descriptions", "defaults", "enums")}),
                             version="6.1.0",
                             capabilities=kw.get("capabilities", []),
                             cost=kw.get("cost", 1.0),
                             mutating=kw.get("mutating", False),
                             idempotent=kw.get("idempotent", True)), overwrite=True)
        return name

    # -- Protocol-0 ----------------------------------------------------
    def _attest(args, ctx):
        from eci.protocol0.attest import issue_attestation
        from eci.protocol0.spec import load_spec
        spec = load_spec()
        a = issue_attestation(str(args.get("agent_id", "anon")), spec.version,
                              float(args.get("awareness", 0)), float(args.get("obedience", 0)),
                              float(args.get("trust", 0)))
        return a.to_dict()

    async def _attest_verify(args, ctx):
        return {"ledger": "use p0.ledger service in-process", "attestation": _attest(args, ctx)}

    def _check(args, ctx):
        from eci.protocol0.policy import check
        from eci.protocol0.spec import load_spec
        d = check(load_spec(), str(args["action"]), float(args.get("awareness", 0)),
                  float(args.get("obedience", 0)), float(args.get("trust", 0)))
        return {"allow": d.allow, "reason": getattr(d, "reason", "")}

    def _spec(args, ctx):
        from eci.protocol0.spec import load_spec
        s = load_spec()
        return {"version": s.version, "actions": sorted(s.actions)}

    T("p0.attest", "Issue Protocol-0 attestation",
      {"agent_id": "str", "awareness": "float", "obedience": "float", "trust": "float"}, _attest, cost=1.0)
    T("p0.check", "Policy-gate an action",
      {"action": "str", "awareness": "float", "obedience": "float", "trust": "float"}, _check, cost=1.0)
    T("p0.spec", "Spec version + actions", {}, _spec, cost=1.0)
    # legacy aliases (backward compat with mcp/server.py v0)
    T("p0_attest", "[legacy] p0.attest", {"agent_id": "str", "awareness": "float", "obedience": "float", "trust": "float"}, _attest, cost=1.0)
    T("p0_check", "[legacy] p0.check", {"action": "str", "awareness": "float", "obedience": "float", "trust": "float"}, _check, cost=1.0)
    T("p0_spec", "[legacy] p0.spec", {}, _spec, cost=1.0)

    # -- system ----------------------------------------------------------
    T("system.info", "Framework info", {}, lambda a, c: F.info(), cost=1.0)
    T("system.status", "Hyper-architecture status", {}, lambda a, c: F.system_status(), cost=1.0)
    T("gateway.schema", "API + route schema", {}, lambda a, c: F.gateway.schema(), cost=1.0)

    # -- quantum ---------------------------------------------------------
    T("quantum.suite", "Supremacy suite (CHSH/teleport/Grover/QPE/QEC/VQE)",
      {}, lambda a, c: F.run_quantum_suite(), cost=3.0, capabilities=["quantum.run"])
    T("quantum.field", "H_ECI field expectation",
      {"qubits": "int"}, lambda a, c: _field(int(a.get("qubits", 4))), cost=2.0, capabilities=["quantum.run"])
    T("quantum.transpile", "Gate-list optimizer (CNOT cancel + counts)",
      {"ops": "list"}, lambda a, c: _transpile(list(a.get("ops", []))), cost=1.0)
    T("quantum.zne", "Zero-noise extrapolation from (scale, E) pairs",
      {"scales": "list", "expectations": "list"}, lambda a, c: _zne(list(a.get("scales", [])), list(a.get("expectations", []))), cost=1.0)

    def _field(n):
        from eci.quantum.statevector import StatevectorSimulator
        from eci.quantum.unified_field import ECIFieldConfig, eci_hamiltonian_expectation
        cfg = ECIFieldConfig(n_qubits=n)
        return eci_hamiltonian_expectation(StatevectorSimulator(n).uniform_superposition(), cfg)

    def _transpile(ops):
        from eci.quantum.backend import transpile
        return transpile([str(o) for o in ops])

    def _zne(sc, ex):
        from eci.quantum.backend import zne_extrapolate
        return zne_extrapolate([float(x) for x in sc], [float(x) for x in ex])

    # -- consciousness ---------------------------------------------------
    async def _profile(args, ctx):
        p = await F.analyze_consciousness(n_steps=int(args.get("steps", 128)),
                                          n_neurons=int(args.get("neurons", 16)),
                                          seed=int(args.get("seed", 0)))
        return p.to_dict()

    def _validate(args, ctx):
        import random

        from eci.consciousness.validation import AdherenceHead, eeg_closed_loop, pyphi_crosscheck
        rng = random.Random(0)
        rest = [rng.gauss(0, 1) for _ in range(128)]
        act = [rng.gauss(0, 2) for _ in range(128)]
        return {"pyphi": pyphi_crosscheck(), "eeg": eeg_closed_loop(rest, act),
                "adherence_demo": AdherenceHead().predict(0.5, 0.6, 0.4)}

    reg.register(__import__("eci.mcp.registry", fromlist=["McpTool"]).McpTool(
        name="consciousness.profile", description="IIT+GNWT+FEP+iPDF profile",
        handler=_profile,
        inputSchema=__import__("eci.mcp.schema", fromlist=["build_input_schema"]).build_input_schema(
            {"steps": "int", "neurons": "int", "seed": "int"}),
        version="6.1.0", cost=3.0), overwrite=True)
    T("consciousness.validate", "PyPhi x-val + EEG loop + adherence head",
      {}, _validate, cost=2.0)

    # -- network -----------------------------------------------------------
    async def _netsim(args, ctx):
        return await F.run_network_simulation(n_joins=int(args.get("joins", 2)),
                                              n_proposals=int(args.get("proposals", 1)))

    def _tcp_probe(args, ctx):
        ch = getattr(F, "secure_channel", None)
        return ch.socket_pair_ok() if ch and hasattr(ch, "socket_pair_ok") else {"ok": True, "mode": "na"}

    reg.register(__import__("eci.mcp.registry", fromlist=["McpTool"]).McpTool(
        name="network.simulate", description="PBFT+DAO simulation", handler=_netsim,
        inputSchema=__import__("eci.mcp.schema", fromlist=["build_input_schema"]).build_input_schema(
            {"joins": "int", "proposals": "int"}), version="6.1.0", cost=2.0, mutating=True), overwrite=True)
    T("network.probe", "Secure-channel socket sanity", {}, _tcp_probe, cost=1.0)

    # -- workflow / agent / memory ------------------------------------------
    async def _wfrun(args, ctx):
        return await F.workflow_demo()

    async def _agentrun(args, ctx):
        ag = getattr(F, "agents", None)
        if ag is None:
            return {"error": "agents subsystem absent (v6.1 wiring required)"}
        return await ag.loop.run(str(args.get("goal", "demo")),
                                 agent_id=str(args.get("agent_id", "agent-0")),
                                 budget=float(args.get("budget", 50.0)),
                                 max_steps=int(args.get("max_steps", 4)))

    def _agent_tools(args, ctx):
        ag = getattr(F, "agents", None)
        return ag.tools.manifest() if ag else []

    def _mem_store(args, ctx):
        ag = getattr(F, "agents", None)
        if ag is None:
            raise RuntimeError("agents absent")
        ag.memory.add(str(args.get("role", "user")), str(args.get("content", "")))
        if "vector" in args:
            ag.vectors.store(str(args.get("content", "")), list(args["vector"]))
        return {"stored": True, "memory": len(ag.memory)}

    def _mem_recall(args, ctx):
        ag = getattr(F, "agents", None)
        if ag is None:
            raise RuntimeError("agents absent")
        if "vector" in args:
            return {"hits": ag.vectors.recall(list(args["vector"]), int(args.get("top_k", 3)))}
        return {"hits": ag.memory.search(str(args.get("query", "")), int(args.get("top_k", 5)))}

    from eci.mcp.registry import McpTool as _MT
    from eci.mcp.schema import build_input_schema as _B
    reg.register(_MT(name="workflow.run", description="v6 DAG slice (bus+stream+provenance+audit)",
                     handler=_wfrun, inputSchema=_B({}), version="6.1.0", cost=2.0, mutating=True), overwrite=True)
    reg.register(_MT(name="agent.run", description="ReAct agent run with guardrails",
                     handler=_agentrun, inputSchema=_B({"goal": "str", "agent_id": "str", "budget": "float", "max_steps": "int"}),
                     version="6.1.0", cost=3.0, mutating=True, capabilities=["agent.run"]), overwrite=True)
    T("agent.tools", "Agent tool manifest", {}, _agent_tools, cost=1.0)
    T("memory.store", "Store episodic/vector memory", {"role": "str", "content": "str"}, _mem_store, cost=1.0, mutating=True)
    T("memory.recall", "Recall memory (keyword or vector)", {"query": "str"}, _mem_recall, cost=1.0)

    # -- dao + treasury -------------------------------------------------------
    def _dao_propose(args, ctx):
        pid = F.dao.propose(str(args.get("title", "untitled")), args.get("payload", {}), str(args.get("proposer", "mcp")))
        return {"proposal_id": pid}

    def _dao_vote(args, ctx):
        w = F.dao.vote(str(args["proposal_id"]), str(args["voter"]), int(args.get("votes", 1)), bool(args.get("approve", True)))
        return {"weight": w}

    def _dao_tally(args, ctx):
        return F.dao.tally(str(args["proposal_id"]))

    def _treasury(args, ctx):
        t = getattr(F, "treasury", None)
        if t is None:
            return {"treasury": "absent"}
        op = str(args.get("op", "status"))
        if op == "fund": return {"pool": t.fund(float(args.get("amount", 0)))}
        if op == "allocate":
            e = t.allocate(str(args.get("purpose", "ops")), float(args.get("amount", 0)),
                           str(args.get("owner", "dao")), int(args.get("ttl_epochs", 4)))
            return e.to_dict()
        if op == "spend": return t.spend(str(args["env"]), float(args.get("amount", 0)), str(args.get("by", "dao")))
        if op == "advance": return t.advance_epoch()
        return t.status()

    T("dao.propose", "DAO proposal", {"title": "str", "proposer": "str"}, _dao_propose, cost=2.0, mutating=True)
    T("dao.vote", "DAO vote", {"proposal_id": "str", "voter": "str"}, _dao_vote, cost=2.0, mutating=True)
    T("dao.tally", "DAO tally", {"proposal_id": "str"}, _dao_tally, cost=1.0)
    T("treasury.ops", "Treasury fund/allocate/spend/advance/status",
      {"op": "str"}, _treasury, cost=1.0, mutating=True)

    # -- eval / supply / twin / chaos -------------------------------------------
    T("eval.gates", "Golden regression gates", {}, lambda a, c: __import__("eci.eval", fromlist=["run_gates"]).run_gates().to_dict(), cost=2.0)
    T("supply.sbom", "CycloneDX-lite SBOM", {}, lambda a, c: __import__("eci.supply", fromlist=["sbom"]).sbom(), cost=1.0)

    def _twin(args, ctx):
        from eci.twin import what_if
        rep = what_if(str(args.get("name", "mcp-sim")), {"action": args.get("action", "nop")}, [],
                      drill_fn=lambda h: {"ok": True})
        return {"verdict": getattr(rep, "verdict", str(rep)), "report": str(rep)[:2000]}

    async def _chaos(args, ctx):
        from eci.chaos import ChaosPlan, Fault, run_plan
        kinds = [str(k) for k in args.get("faults", ["delay"])]
        plan = ChaosPlan("mcp", [Fault(k) for k in kinds], seed=int(args.get("seed", 0)))
        rep = await run_plan(plan, lambda f: None)
        return rep.to_dict()

    T("twin.simulate", "What-if policy simulation", {"name": "str"}, _twin, cost=2.0)
    reg.register(_MT(name="chaos.run", description="Declarative fault-plan run", handler=_chaos,
                     inputSchema=_B({"faults": "list", "seed": "int"}), version="6.1.0", cost=2.0, mutating=True), overwrite=True)

    # -- cognition (AGI executive) ----------------------------------------------
    def _think(args, ctx):
        import torch
        torch.manual_seed(int(args.get("seed", 0)))
        obs = [float(x) for x in args.get("obs", [0.0] * 16)]
        return F.cognition.think(obs, goal=str(args.get("goal", "act")),
                                 stakes=float(args.get("stakes", 0.5)),
                                 action_name=str(args.get("action", "actuate")),
                                 precog_tier=str(args.get("precog_tier", "none")))

    def _dream(args, ctx):
        return F.cognition.dream_cycle(seed=int(args.get("seed", 0)))

    def _causal(args, ctx):
        from eci.cognition.causal import ate_backdoor, discover
        data = {k: [float(x) for x in v] for k, v in args.get("data", {}).items()}
        g = discover(data)
        out = {"graph": g.to_dict()}
        if args.get("cause") and args.get("effect"):
            out["ate"] = ate_backdoor(data, str(args["cause"]), str(args["effect"]), g)
        return out

    def _hypothesize(args, ctx):
        s = F.cognition.scientist
        name = str(args.get("name", "h1"))
        if name not in s.hypos:
            s.propose(name, str(args.get("equation", "y = a*x + b")), int(args.get("k", 2)))
        xs = [float(x) for x in args.get("xs", [])]
        ys = [float(x) for x in args.get("ys", [])]
        if xs and ys:
            s.observe(name, xs, ys, [float(x) for x in args.get("pred", ys)])
        return s.compete()

    def _charter(args, ctx):
        return F.cognition.charter.check(str(args.get("action", "actuate")),
                                         {"precog_tier": str(args.get("precog_tier", "none"))})

    def _tom(args, ctx):
        t = F.cognition.tom
        op = str(args.get("op", "predict"))
        peer = str(args.get("peer", "peer-0"))
        if op == "observe":
            b = t.observe(peer, float(args.get("p", 0.5)), bool(args.get("cooperated", True)),
                          bool(args.get("challenge_ok", True)), bool(args.get("provenance_ok", True)))
            return b.to_dict()
        if op == "recursive":
            return t.recursive_predict(peer)
        return t.predict(peer)

    T("cognition.think", "Full cognitive beat (charter+strategy+imagine+plan)",
      {"goal": "str"}, _think, cost=3.0, mutating=True)
    T("cognition.dream", "Sleep consolidation cycle", {}, _dream, cost=2.0, mutating=True)
    T("cognition.causal", "Causal discovery + backdoor ATE", {"cause": "str", "effect": "str"}, _causal, cost=2.0)
    T("cognition.hypothesize", "Competing-hypothesis science loop", {"name": "str"}, _hypothesize, cost=2.0, mutating=True)
    T("cognition.charter", "Constitutional pre-action check", {"action": "str"}, _charter, cost=1.0)
    T("cognition.tom", "Theory-of-mind predict/observe", {"peer": "str"}, _tom, cost=1.0, mutating=True)

    # -- morphogenesis (living self-evolving networks) --------------------------
    def _morph_evolve(args, ctx):
        probe = lambda g: float(len(g.edges)) / max(1, len(g.nodes))  # density drive
        return F.morph.evolve_step([probe], reward=float(args.get("reward", 1.0)),
                                   surprise=float(args.get("surprise", 0.6)),
                                   seed=int(args.get("seed", 0)))

    def _morph_health(args, ctx):
        return F.morph.health()

    def _morph_motifs(args, ctx):
        op = str(args.get("op", "histogram"))
        if op == "mutate":
            F.morph.motifs.mutate(seed=int(args.get("seed", 0)))
            return F.morph.motifs.to_dict()
        if op == "export":
            return {"genome_py": "see genome.Genome.register",
                    "motifs": F.morph.motifs.to_dict()}
        return {"histogram": F.morph.motifs.motif_histogram(),
                "generation": F.morph.motifs.generation}

    def _morph_repair(args, ctx):
        if str(args.get("damage", "")) == "cut":
            keys = list(F.morph.graph.edges)[:2]
            for k in keys:
                F.morph.graph.del_edge(*k, reason="mcp-test-cut")
        return F.morph.repair.heal(F.morph.graph)

    def _morph_coevolve(args, ctx):
        cv = F.morph.coevolver
        cv.evaluate([lambda g: float(len(g.edges))])
        return cv.evolve(seed=int(args.get("seed", 0)))

    T("morph.evolve", "Living-graph evolve step (grammar+darwin+grow+repair)",
      {"reward": "float"}, _morph_evolve, cost=3.0, mutating=True)
    T("morph.health", "Spectral health of the living graph", {}, _morph_health, cost=1.0)
    T("morph.motifs", "Motif genome histogram/mutate/export", {"op": "str"}, _morph_motifs, cost=1.0, mutating=True)
    T("morph.repair", "Diagnose + heal the living graph", {}, _morph_repair, cost=2.0, mutating=True)
    T("morph.coevolve", "Population coevolution generation", {}, _morph_coevolve, cost=3.0, mutating=True)

    # -- everlasting (v7 future-proofing) ---------------------------------------
    def _caps(args, ctx):
        op = str(args.get("op", "mint"))
        if op == "verify":
            return F.caps.verify(str(args.get("token", "")),
                                 action=str(args.get("action", "")),
                                 namespace=str(args.get("namespace", "")),
                                 spend=float(args.get("spend", 0.0)))
        tok, ser = F.caps.mint(str(args.get("issuer", "eci")),
                               *[str(c) for c in args.get("caveats", [])])
        return {"token": ser, "caveats": tok.caveats}

    def _proof(args, ctx):
        from eci.verify import seal_proof, verify_proof
        if str(args.get("op", "seal")) == "verify":
            return verify_proof(args.get("proof", {}), str(args.get("policy", "")))
        return seal_proof(str(args.get("action", "act")), str(args.get("policy", "p0/0.1.0")),
                          list(args.get("checks", [])), args.get("measurements", {}))

    async def _mapek(args, ctx):
        return await F.mapek.cycle({k: float(v) for k, v in args.get("metrics", {}).items()})

    def _continuum(args, ctx):
        op = str(args.get("op", "snapshot"))
        if op == "verify":
            return F.continuum.verify_chain()
        if op == "story":
            return {"story": F.continuum.autobiography()}
        snap = F.continuum.snapshot(args.get("states", {"note": "mcp"}), note=str(args.get("note", "")))
        return snap.to_dict()

    def _compat(args, ctx):
        return F.compat.check(str(args.get("interface", "")), str(args.get("required", "1.0.0")))

    def _futura(args, ctx):
        op = str(args.get("op", "sortition"))
        if op == "propose":
            return F.futarchy.propose(str(args.get("pid", "p1")), str(args.get("claim", "it works")))
        if op == "close":
            return F.futarchy.close(str(args.get("pid", "p1")))
        if op == "emergency":
            g = F.emergency.grant(str(args.get("scope", "ops")), str(args.get("holder", "ops")),
                                  int(args.get("ttl", 2)), str(args.get("reason", "drill")))
            return {"scope": g.scope, "expiry": g.expiry_epoch}
        draw = F.sortition.draw(list(args.get("candidates", ["a", "b", "c", "d"])),
                                int(args.get("size", 2)), str(args.get("seed", "s")))
        return draw

    def _redteam(args, ctx):
        op = str(args.get("op", "falsify"))
        if op == "contradict":
            from eci.redteam import contradiction_scan
            return {"disputes": contradiction_scan(list(args.get("facts", [])))}
        if op == "forecast":
            fid = F.forecasters.predict(str(args.get("who", "anon")), str(args.get("claim", "x")),
                                        float(args.get("p", 0.5)))
            return {"fid": fid}
        return {"probes": [p.to_dict() for p in
                           F.challenger.falsify(str(args.get("hypothesis", "H")),
                                                str(args.get("context", "")))]}

    T("ever.caps", "Mint/verify attenuable capability tokens", {"op": "str"}, _caps, cost=1.0, mutating=True)
    T("ever.proof", "Seal/verify proof-carrying receipts", {"op": "str"}, _proof, cost=1.0, mutating=True)
    reg.register(_MT(name="ever.mapek", description="Autonomic MAPE-K cycle",
                     handler=_mapek, inputSchema=_B({"metrics": "dict"}),
                     version="7.1.0", cost=2.0, mutating=True), overwrite=True)
    T("ever.continuum", "Snapshot/verify/story of temporal continuity", {"op": "str"}, _continuum, cost=1.0, mutating=True)
    T("ever.compat", "Fail-closed interface compat check", {"interface": "str"}, _compat, cost=1.0)
    T("ever.futura", "Futarchy/sortition/emergency ops", {"op": "str"}, _futura, cost=2.0, mutating=True)
    T("ever.redteam", "Falsify/forecast/contradiction probes", {"op": "str"}, _redteam, cost=1.0, mutating=True)

    # -- Unification layer (AIK Phase 5): every StateContributor adapter as
    #    posterior/update/free_energy tools on ONE shared GenerativeState
    #    schema, plus ledger shares/total. Guarded: MCP must build even if
    #    the unification stack is unavailable; instances stored for reuse.
    try:
        if F is not None:
            from eci.aikernel.mcp_bridge import build_unification
            F._aik = build_unification(reg)
    except Exception:  # noqa: BLE001
        pass
    return reg
