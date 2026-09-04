"""Ecosystem batch: court, market, commons, privacy, genome."""
import pytest

from eci.court import Case, Court
from eci.genome import Gene, Genome, life_cycle, mutate
from eci.market import Marketplace
from eci.privacy import Guardian
from eci.protocol0.ledger import Ledger
from eci.semantic import Commons


def test_court_conviction_and_single_appeal():
    court = Court(panel_size=5, appeal_size=9)
    members = [f"n{i}" for i in range(12)]
    panel = Court.select_panel(members, "epoch-1", 5)
    assert len(panel) == 5 and len(set(panel)) == 5
    assert Court.select_panel(members, "epoch-2", 5) != panel  # rotates
    case = Case("c1", "mallory", {"precog_p": 0.97})
    ballots = {v: "quarantine" for v in panel[:4]}
    ballots[panel[4]] = "acquit"
    v = court.try_case(case, panel, ballots, Ledger())
    assert v.verdict == "quarantine"  # 4/5 >= 2/3
    v2 = court.appeal(case, panel + ["n5", "n6", "n7", "n8"],
                      {w: "acquit" for w in panel + ["n5", "n6", "n7", "n8"]})
    assert v2.verdict == "acquit"
    with pytest.raises(PermissionError):
        court.appeal(case, panel, {})


def test_market_prices_and_settles():
    mp = Marketplace()
    assert abs(mp.market_for("mallory").price_yes() - 0.5) < 1e-9
    r = mp.trade("alice", "mallory", "yes", 5.0)
    assert r["price"] > 0.5  # buying YES moves price up
    r2 = mp.trade("bob", "mallory", "no", 2.0)
    assert r2["price"] < r["price"]
    pay = mp.settle("mallory", True)
    assert pay["alice"] == 5.0 and "bob" not in pay
    with pytest.raises(ValueError):
        mp.trade("alice", "mallory", "yes", 1.0)  # resolved


def test_commons_dispute_and_resolve():
    c = Commons()
    c.assert_fact("sky", "color", "blue", "alice", ["w1", "w2"])
    assert not c.disputes
    c.assert_fact("sky", "color", "green", "bob", ["w3"])
    assert len(c.disputes) == 1 and not c.disputes[0].resolved
    d = c.resolve("sky", "color", c.disputes[0].fact_ids[0], Ledger())
    assert d.resolved and d.winner is not None
    c.retract(d.winner)
    assert c.facts[d.winner].live is False  # tombstone, still present


def test_privacy_budget_and_mean():
    g = Guardian(budget_per_epoch=1.0)
    r1 = g.ask("alice", 0.8, sensitivity=0.1, eps=0.6, seed=0)
    assert r1["ok"] is True
    r2 = g.ask("alice", 0.8, sensitivity=0.1, eps=0.6, seed=1)
    assert r2["ok"] is False  # 0.6 spent, only 0.4 left
    m = g.mean({"a": 0.5, "b": 0.7}, eps_each=0.2)
    assert m["ok"] and m["n"] == 2 and -5.0 <= m["mean"] <= 5.0  # Laplace tails are honest
    g.reset_epoch()
    assert g.remaining("alice") == 1.0


def test_genome_lifecycle_and_mutation_bounds():
    parent = Gene("vote_gate", {"min_obedience": 0.5})
    child = mutate(parent, seed=0)
    assert child.generation == 1 and all(0.0 <= v <= 1.0 for v in child.params.values())
    genome, ledger = Genome(), Ledger()
    good = life_cycle(parent,
                      simulate=lambda pol: {"obedience": 0.9, "resilience": 0.95},
                      canary=lambda pol: {"obedience": 0.9, "resilience": 1.0, "baseline_resilience": 1.0},
                      vote=lambda pol: True, genome=genome, ledger=ledger)
    assert good["adopted"] is True and "vote_gate" in genome.export()
    bad = life_cycle(parent,
                     simulate=lambda pol: {"obedience": 0.5, "resilience": 0.5} if pol else {"obedience": 0.8, "resilience": 0.95},
                     canary=lambda pol: {}, vote=lambda pol: True,
                     genome=Genome(), ledger=ledger)
    assert bad["adopted"] is False and bad["stage"] == "twin"
    assert ledger.verify()["ok"] is True
