"""Shared slowapi limiter.

Lives in its own module so routes and ``main`` can import the same limiter
instance without a circular import.

Note: behind a reverse proxy (Tailscale Funnel) ``get_remote_address`` sees the
proxy's address, so the login limit is effectively shared across clients. That
is acceptable as a brute-force backstop for a self-hosted household instance.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
