"""Security subsystem: crypto-agile post-quantum primitives."""

from eci.security.pqc import HashBasedSigner, PQCSuite, SecureChannel, derive_key
from eci.security.secrets import SecretLease, SecretManager
from eci.security.secure_channel import HybridSecureChannel, SecureChannelConfig

__all__ = ["HashBasedSigner", "PQCSuite", "SecureChannel", "derive_key",
           "SecretLease", "SecretManager", "HybridSecureChannel", "SecureChannelConfig"]
