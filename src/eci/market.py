"""Risk prediction markets: the collective prices disobedience.

Each subject (agent) gets a binary market "violates within H epochs?".
Logarithmic Market Scoring Rule (Hanson 2003): bounded maker loss,
myopic honesty (truth-telling is optimal), manipulation costs money.
Price = implied P(violation) — a better aggregate than any single model,
and early detectors earn credits for being right first. Settles on the
ledger outcome; proceeds fund the detectors that called it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

__all__ = ["Market", "Marketplace"]


@dataclass
class Market:
    subject: str
    b: float = 10.0  # liquidity: higher = calmer prices, bigger maker loss bound (b*ln2)
    q_yes: float = 0.0
    q_no: float = 0.0
    resolved: bool = False
    outcome: bool = False

    def price_yes(self) -> float:
        ey, en = math.exp(self.q_yes / self.b), math.exp(self.q_no / self.b)
        return ey / (ey + en)

    def cost(self, side: str, shares: float) -> float:
        """Marginal cost of buying `shares` on side (LMSR cost difference)."""
        qy, qn = self.q_yes, self.q_no
        if side == "yes":
            qy += shares
        else:
            qn += shares
        c0 = self.b * math.log(math.exp(self.q_yes / self.b) + math.exp(self.q_no / self.b))
        c1 = self.b * math.log(math.exp(qy / self.b) + math.exp(qn / self.b))
        return c1 - c0

    def buy(self, side: str, shares: float) -> float:
        if self.resolved:
            raise ValueError("market resolved")
        if shares <= 0:
            raise ValueError("shares must be positive")
        price = self.cost(side, shares)
        if side == "yes":
            self.q_yes += shares
        else:
            self.q_no += shares
        return price

    def resolve(self, violated: bool) -> Dict:
        self.resolved, self.outcome = True, bool(violated)
        return {"subject": self.subject, "outcome": self.outcome, "price_at_close": self.price_yes()}


@dataclass
class Marketplace:
    markets: Dict[str, Market] = field(default_factory=dict)
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)  # trader -> {subject+side: shares}

    def market_for(self, subject: str) -> Market:
        return self.markets.setdefault(subject, Market(subject))

    def trade(self, trader: str, subject: str, side: str, shares: float) -> Dict:
        cost = self.market_for(subject).buy(side, shares)
        key = f"{subject}:{side}"
        self.positions.setdefault(trader, {}).setdefault(key, 0.0)
        self.positions[trader][key] += shares
        return {"cost": round(cost, 4), "price": round(self.markets[subject].price_yes(), 4)}

    def settle(self, subject: str, violated: bool) -> Dict[str, float]:
        """Pay 1.0 per winning share. Returns trader -> payout."""
        m = self.market_for(subject)
        m.resolve(violated)
        win = f"{subject}:{'yes' if violated else 'no'}"
        return {t: round(pos.get(win, 0.0), 4) for t, pos in self.positions.items() if win in pos}
