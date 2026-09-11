"""Phase 15 — coverage closure: every contributor registered, ledger snapshotted.

1. Package walk finds exactly the 8 known StateContributor subclasses and
   asserts each is a member of a fresh default mesh (no silent orphans).
2. Ledger snapshot survives a JSON round-trip with shares intact, and every
   snapshotted posterior reloads via GenerativeState.from_dict.
"""
import json


def test_all_contributors_registered_in_default_mesh():
    """Anti-rot gate: a new adapter that isn't wired into build_unification
    fails here loudly instead of drifting invisible."""
    import inspect
    import pkgutil
    import eci
    from eci.aikernel.mcp_bridge import build_unification
    from eci.aikernel.state_contract import StateContributor
    found = {}
    for mod in pkgutil.walk_packages(eci.__path__, prefix="eci."):
        if "test" in mod.name or "pycache" in mod.name:
            continue
        try:
            m = __import__(mod.name, fromlist=["*"])
        except Exception:
            continue
        for attr, obj in vars(m).items():
            if (inspect.isclass(obj) and obj.__module__ == m.__name__
                    and issubclass(obj, StateContributor) and obj is not StateContributor):
                found.setdefault(obj.__name__, mod.name)
    assert found, "no contributors discovered at all?"
    mesh = build_unification()["ledger"].members()
    registered_classes = {type(m).__name__ for m in mesh.values()}
    orphans = {k: v for k, v in found.items() if k not in registered_classes}
    assert orphans == {}, f"contributors not in default mesh: {orphans}"
    assert len(found) == 8, found


def test_ledger_snapshot_roundtrip():
    """Snapshot -> JSON -> reload: shares intact, posteriors reload."""
    from eci.aikernel.generative_model import GenerativeState
    from eci.aikernel.mcp_bridge import build_unification
    built = build_unification()
    led = built["ledger"]
    snap = led.snapshot()
    assert set(snap["members"]) == set(led.members())
    wire = json.loads(json.dumps(snap))  # the actual wire
    for name, rec in wire["members"].items():
        assert abs(rec["share"] - led.shares()[name]) < 1e-9, name
        back = GenerativeState.from_dict(rec["posterior"])
        assert back.dim == led.members()[name].posterior().dim, name
    assert abs(sum(r["share"] for r in wire["members"].values())
               - float(led.total_free_energy().detach().item())) < 1e-6
