"""Mesh federation: independent ECI meshes that trust each other explicitly.

Two meshes anchor each other's ledger heads (mutual checkpoints) and
translate policy: a vote in mesh A counts in mesh B with a negotiated
weight factor. No shared validator set, no merged ledger — each mesh stays
sovereign; only the bridge records are cross-signed. This is how isolated
deployments become one global network without centralization.
"""

from eci.federation.bridge import Bridge, TranslationMap, anchor, translate_vote

__all__ = ["Bridge", "TranslationMap", "anchor", "translate_vote"]
