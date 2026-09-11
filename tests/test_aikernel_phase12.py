"""Phase 12 — framework ledger wiring: auditable F-trajectory points."""
import pytest
import torch


@pytest.fixture(scope="module")
def live():
    from eci.framework import ECIFramework
    return ECIFramework()


def test_snapshot_records_without_mutating(live):
    s1 = live.aik_snapshot(note="before")
    assert s1["ok"] is True and s1["note"] == "before"
    assert abs(s1["total_free_energy"] - sum(s1["shares"].values())) < 1e-6
    # drive one real update through a member, snapshot again
    live._aik["contributors"]["agent"].update(torch.tensor([0.3]))
    s2 = live.aik_snapshot(note="after-agent-update")
    assert s2["ok"] is True
    assert abs(s2["total_free_energy"] - sum(s2["shares"].values())) < 1e-6
    # both snapshots retrievable from provenance with distinct ids
    recs = live.provenance.query(kind="aik.snapshot", actor="framework")
    ids = [r["id"] for r in recs if r["inputs"].get("note") in ("before", "after-agent-update")]
    assert len(ids) == 2 and ids[0] != ids[1]
    assert s1["provenance_id"] in ids and s2["provenance_id"] in ids
    # audit chain still verifies (append-only integrity kept)
    assert live.observability.audit.verify()["ok"] is True


def test_snapshot_absent_mesh_reports_error():
    from eci.framework import ECIFramework
    fw = ECIFramework.__new__(ECIFramework)  # no __init__: no mesh at all
    assert fw.aik_snapshot()["ok"] is False
    assert fw.aik_status()["ok"] is False
