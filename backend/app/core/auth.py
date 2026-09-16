"""Validacao do token Supabase no backend.

Regra do projeto: esconder pagina no frontend nao basta. Toda rota que
mexe em dado de organizacao passa por aqui, decodifica o JWT emitido pelo
Supabase Auth (assinado com a chave do PROJETO, nunca inventada por nos)
e so entao cria um client Supabase autenticado como aquele usuario — o
que faz a Row Level Security do Postgres valer tambem no backend, nao so
no navegador.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from supabase import Client, create_client

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_jwks_client: PyJWKClient | None = None


@dataclass
class AuthedUser:
    user_id: str
    email: str | None
    access_token: str


def _get_jwks_client(settings: Settings) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.jwks_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "SUPABASE_URL nao configurado no backend. "
                    "Preencha backend/.env a partir de .env.example."
                ),
            )
        _jwks_client = PyJWKClient(settings.jwks_url)
    return _jwks_client


def _decode_token(token: str, settings: Settings) -> dict:
    # Projetos novos do Supabase assinam com chave assimetrica (JWKS).
    # Projetos antigos ainda podem usar HS256 com segredo compartilhado.
    # Tentamos JWKS primeiro; caimos para HS256 só se um segredo foi
    # explicitamente configurado — nunca inventamos um segredo.
    last_error: Exception | None = None

    if settings.jwks_url:
        try:
            signing_key = _get_jwks_client(settings).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        except Exception as exc:  # noqa: BLE001 — cai para o fallback abaixo
            last_error = exc

    if settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Token invalido ou nao verificavel: {last_error}",
    )


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> AuthedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecalho Authorization: Bearer <token> ausente.",
        )
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Backend sem credenciais Supabase configuradas "
                "(SUPABASE_URL / SUPABASE_ANON_KEY). Configuracao pendente, "
                "nao ha autenticacao simulada."
            ),
        )

    payload = _decode_token(credentials.credentials, settings)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sem 'sub' (id do usuario).")

    return AuthedUser(
        user_id=user_id,
        email=payload.get("email"),
        access_token=credentials.credentials,
    )


def user_scoped_client(
    user: AuthedUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
) -> Client:
    """Client Supabase autenticado como o usuario da requisicao.

    Toda query feita com este client passa pelo PostgREST com o JWT do
    usuario — a Row Level Security do Postgres decide o que ele pode ver
    ou escrever. O backend nao contorna isso usando a service_role aqui.
    """
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(user.access_token)
    return client
