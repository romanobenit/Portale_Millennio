"""
Autenticazione JWT con Keycloak via PyJWT (sostituisce python-jose).

PyJWT >= 2.8.0 con PyJWKClient gestisce internamente il caching delle chiavi JWKS
e previene algorithm confusion attacks (CVE presenti in python-jose <= 3.3.0).

Tutte le chiamate a PyJWKClient sono eseguite in asyncio.to_thread perché
PyJWKClient usa urllib (sync) internamente.
"""
import asyncio
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import get_settings
from core.logger import logger

settings = get_settings()

KEYCLOAK_JWKS_URL = (
    f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
    "/protocol/openid-connect/certs"
)

bearer_scheme = HTTPBearer()

# PyJWKClient con caching delle chiavi (TTL default 300s, max 16 chiavi)
_jwks_client = jwt.PyJWKClient(KEYCLOAK_JWKS_URL, cache_keys=True, max_cached_keys=16)


async def decode_token(token: str) -> dict:
    """
    Valida un JWT Keycloak (RS256) e restituisce il payload.
    Usa PyJWKClient per il fetching sicuro della chiave pubblica da JWKS.
    """
    try:
        # PyJWKClient è sincrono — eseguire in thread per non bloccare l'event loop
        signing_key = await asyncio.to_thread(
            _jwks_client.get_signing_key_from_jwt, token
        )
        # Accetta token emessi sia da millennio-backend che da millennio-frontend
        payload: dict = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=[settings.keycloak_client_id, "millennio-frontend", "account"],
            options={"verify_exp": True, "require": ["sub", "exp", "iat"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token scaduto",
        ) from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Audience JWT non valida",
        ) from exc
    except jwt.PyJWTError as exc:
        logger.debug("JWT validation failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido",
        ) from exc


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    return await decode_token(credentials.credentials)


def require_roles(*roles: str):
    async def _check(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        realm_roles: list[str] = user.get("realm_access", {}).get("roles", [])
        if not any(r in realm_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permessi insufficienti",
            )
        return user

    return _check


def require_any_role(*roles: str):
    return require_roles(*roles)


RequireSocio = Depends(require_roles("socio", "staff", "dirigenza", "allenatore"))
RequireStaff = Depends(require_roles("staff", "dirigenza"))
RequireDirigenza = Depends(require_roles("dirigenza"))
RequireAllenatore = Depends(require_roles("allenatore", "staff", "dirigenza"))
