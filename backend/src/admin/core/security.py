import base64
import json
import time
import uuid
from typing import Any, Protocol

import httpx
import jwt
from jwt import PyJWKSet
from pydantic import EmailStr, TypeAdapter
from pydantic import ValidationError as PydanticError

from admin.core.config import EntraConfig
from admin.core.errors import AuthenticationError
from admin.core.logging import get_logger
from admin.schemas.session import Identity

logger = get_logger(__name__)

JWKS_CACHE_SECONDS = 3600
EMAIL_CLAIMS = ("email", "preferred_username", "upn")


EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _extract_email(claims: dict[str, Any]) -> str:
    for claim in EMAIL_CLAIMS:
        try:
            return EMAIL_ADAPTER.validate_python(claims.get(claim)).lower()
        except PydanticError:
            continue
    raise AuthenticationError("token does not carry a usable email claim")


def _to_identity(claims: dict[str, Any]) -> Identity:
    object_id = claims.get("oid")
    if not object_id:
        raise AuthenticationError("token does not carry an oid claim")

    return Identity(
        entra_object_id=uuid.UUID(object_id),
        email=_extract_email(claims),
        name=claims.get("name") or _extract_email(claims),
    )


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> Identity: ...


class EntraTokenVerifier:
    def __init__(self, config: EntraConfig, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client
        self._jwks: PyJWKSet | None = None
        self._fetched_at = 0.0

    async def _load_jwks(self, *, force: bool = False) -> PyJWKSet:
        is_stale = time.monotonic() - self._fetched_at > JWKS_CACHE_SECONDS
        if self._jwks is None or is_stale or force:
            response = await self._client.get(self._config.jwks_uri)
            response.raise_for_status()
            self._jwks = PyJWKSet.from_dict(response.json())
            self._fetched_at = time.monotonic()
        return self._jwks

    async def _signing_key(self, kid: str) -> Any:
        for attempt_force in (False, True):
            jwks = await self._load_jwks(force=attempt_force)
            for key in jwks.keys:
                if key.key_id == kid:
                    return key.key
        raise AuthenticationError("token signing key is not published by the tenant")

    async def verify(self, token: str) -> Identity:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as error:
            raise AuthenticationError("malformed token") from error

        kid = header.get("kid")
        if not kid:
            raise AuthenticationError("token header is missing kid")

        key = await self._signing_key(kid)

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self._config.allowed_audiences,
                issuer=self._config.issuer,
                options={"require": ["exp", "iat", "aud", "iss", "oid"]},
            )
        except jwt.ExpiredSignatureError as error:
            raise AuthenticationError("token has expired") from error
        except jwt.PyJWTError as error:
            raise AuthenticationError("token failed verification") from error

        if claims.get("tid") != self._config.tenant_id:
            raise AuthenticationError("token was issued by a different tenant")

        return _to_identity(claims)


class LocalTokenVerifier:
    def __init__(self) -> None:
        logger.warning(
            "entra_not_configured",
            detail="accepting unsigned local identity tokens; never enable outside local",
        )

    async def verify(self, token: str) -> Identity:
        try:
            padded = token + "=" * (-len(token) % 4)
            claims = json.loads(base64.urlsafe_b64decode(padded))
        except (ValueError, json.JSONDecodeError) as error:
            raise AuthenticationError("local token must be base64url-encoded JSON") from error

        return _to_identity(claims)


def build_token_verifier(config: EntraConfig, client: httpx.AsyncClient) -> TokenVerifier:
    if config.is_configured:
        return EntraTokenVerifier(config, client)
    return LocalTokenVerifier()
