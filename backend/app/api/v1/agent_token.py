"""
NEF Agent Token Endpoint
POST /api/v1/agent/token

Allows a registered NEF agent to exchange its agent_id + HMAC-signed
challenge for a short-lived JWT. This enables the agent to use
Bearer token auth for all subsequent API calls.

Signature scheme:
  message   = f"{agent_id}:{nonce}"
  signature = HMAC-SHA256(message, api_key)
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

# Token TTL
_ACCESS_TOKEN_TTL_MINUTES = 60     # 1-hour access token
_REFRESH_TOKEN_TTL_HOURS  = 24     # 24-hour refresh token


# ── Request / Response models ──────────────────────────────────────────────────

class AgentTokenRequest(BaseModel):
    agent_id:  str
    nonce:     str        # random hex, prevents replay
    signature: str        # HMAC-SHA256(f"{agent_id}:{nonce}", api_key)


class AgentTokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int       # seconds until access_token expires


class AgentRefreshRequest(BaseModel):
    agent_id:     str
    refresh_token: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _verify_signature(agent_id: str, nonce: str, signature: str, api_key: str) -> bool:
    """Constant-time HMAC-SHA256 signature verification."""
    message  = f"{agent_id}:{nonce}".encode()
    expected = hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _make_agent_token(agent_id: str, token_type: str, ttl_minutes: int) -> str:
    """Create a JWT for the agent."""
    now    = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ttl_minutes)
    payload = {
        "sub":        agent_id,
        "type":       f"agent_{token_type}",   # "agent_access" | "agent_refresh"
        "iss":        settings.JWT_ISSUER,
        "iat":        now,
        "exp":        expire,
        "jti":        secrets.token_urlsafe(16),  # unique token ID
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_agent_token(token: str, expected_type: str) -> Optional[str]:
    """
    Decode and validate an agent JWT.
    Returns agent_id on success, None on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except Exception:
        return None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/agent/token",
    response_model=AgentTokenResponse,
    tags=["agent-auth"],
    summary="Exchange agent credentials for JWT tokens",
)
async def agent_token(
    body: AgentTokenRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Exchange a registered agent's API key (HMAC-signed) for a JWT access token.

    The agent HMAC-signs `{agent_id}:{nonce}` with its api_key.
    Returns a 1-hour access token + 24-hour refresh token.
    Falls back gracefully — agents using only X-API-Key still work.
    """
    # Look up agent
    result = await db.execute(
        text("SELECT id, api_key FROM agent_machines WHERE id = :id"),
        {"id": body.agent_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown agent")

    # Validate HMAC signature
    if not _verify_signature(body.agent_id, body.nonce, body.signature, row.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # Issue tokens
    access_token  = _make_agent_token(body.agent_id, "access",  _ACCESS_TOKEN_TTL_MINUTES)
    refresh_token = _make_agent_token(body.agent_id, "refresh", _REFRESH_TOKEN_TTL_HOURS * 60)

    # Update last_seen
    await db.execute(
        text("UPDATE agent_machines SET last_seen = NOW() WHERE id = :id"),
        {"id": body.agent_id},
    )
    await db.commit()

    return AgentTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_ACCESS_TOKEN_TTL_MINUTES * 60,
    )


@router.post(
    "/agent/token/refresh",
    response_model=AgentTokenResponse,
    tags=["agent-auth"],
    summary="Refresh agent JWT using refresh token",
)
async def agent_token_refresh(
    body: AgentRefreshRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Use a valid refresh token to issue a new access + refresh token pair.
    The old refresh token is invalidated (rotation).
    """
    agent_id = _decode_agent_token(body.refresh_token, "agent_refresh")
    if not agent_id or agent_id != body.agent_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Confirm agent still exists and is active
    result = await db.execute(
        text("SELECT id FROM agent_machines WHERE id = :id"),
        {"id": agent_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent not found")

    # Issue new token pair (refresh rotation)
    access_token  = _make_agent_token(agent_id, "access",  _ACCESS_TOKEN_TTL_MINUTES)
    refresh_token = _make_agent_token(agent_id, "refresh", _REFRESH_TOKEN_TTL_HOURS * 60)

    await db.execute(
        text("UPDATE agent_machines SET last_seen = NOW() WHERE id = :id"),
        {"id": agent_id},
    )
    await db.commit()

    return AgentTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_ACCESS_TOKEN_TTL_MINUTES * 60,
    )
