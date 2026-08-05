"""Network-facing crawler safety primitives."""

from .policy import DnsFailure, NetworkPolicy, ResolvedTarget, UnsafeTarget
from .url import InvalidUrl, NormalizedUrl, normalize_http_url, same_origin

__all__ = [
    "DnsFailure",
    "InvalidUrl",
    "NetworkPolicy",
    "NormalizedUrl",
    "ResolvedTarget",
    "UnsafeTarget",
    "normalize_http_url",
    "same_origin",
]
