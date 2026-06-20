"""
Rate limiting centralizzato via slowapi + Redis.

Limiti applicati (per IP remoto, salvo diversa indicazione):
  - Endpoint pubblici calendario/tessere: 60 req/min
  - Endpoint PDF tessera (heavy): 10 req/min
  - Webhook Stripe: 200 req/min  (Stripe può ritentare fino a 72h)
  - Acquisto NFT: 10 req/min per utente
  - Verifica QR Palasirion: 30 req/min

Lo storage Redis è condiviso con il broker Celery (DB 0).
In caso di Redis non raggiungibile, slowapi degrada silenziosamente
(fail_open=True) per non bloccare il servizio.

NOTA: dietro il Hetzner Load Balancer, request.client.host è l'IP del LB,
non del client reale. Leggiamo X-Forwarded-For solo se la request arriva
da un IP nella rete privata Hetzner (10.0.0.0/8).
"""
from slowapi import Limiter
from starlette.requests import Request

from core.config import get_settings

settings = get_settings()

_PRIVATE_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                     "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                     "172.30.", "172.31.", "192.168.", "127.")


def _get_real_ip(request: Request) -> str:
    """
    Restituisce l'IP reale del client.
    Se la richiesta arriva da un IP privato (load balancer interno Hetzner),
    legge X-Forwarded-For. Altrimenti usa l'IP diretto per prevenire IP spoofing.
    """
    client_ip = request.client.host if request.client else "unknown"
    is_from_proxy = any(client_ip.startswith(p) for p in _PRIVATE_PREFIXES)
    if is_from_proxy:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return client_ip


limiter = Limiter(
    key_func=_get_real_ip,
    storage_uri=settings.redis_url,
    strategy="fixed-window",
    default_limits=["200/minute"],
)
