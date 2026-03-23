"""
TBAPS Security
Authentication, authorization, and token management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, TokenExpiredError, TokenInvalidError
from app.models.employee import Employee

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with issuer and audience claims."""
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
    })

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token with issuer and audience claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "refresh",
    })

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token with issuer/audience verification."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"leeway": 10},  # 10-second clock skew tolerance
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Employee:
    """
    Get current authenticated user from JWT token
    
    Usage:
        @app.get("/me")
        async def get_me(current_user: Employee = Depends(get_current_user)):
            return current_user
    """
    try:
        payload = decode_token(token)
        
        # Verify token type
        if payload.get("type") != "access":
            raise TokenInvalidError("Invalid token type")
        
        # Get user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise TokenInvalidError("Token missing subject")
        
        # Get user from database
        result = await db.execute(
            select(Employee).where(Employee.id == user_id, Employee.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthenticationError("User not found")
        
        if user.status != "active":
            raise AuthenticationError("User account is not active")
        
        return user
        
    except (TokenExpiredError, TokenInvalidError, AuthenticationError):
        raise
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def get_current_active_user(
    current_user: Employee = Depends(get_current_user)
) -> Employee:
    """Get current active user (additional check)"""
    if current_user.status != "active":
        raise AuthenticationError("User account is inactive")
    return current_user


def create_token_pair(user_id: str, email: str) -> Dict[str, str]:
    """Create access and refresh token pair"""
    access_token = create_access_token(
        data={"sub": user_id, "email": email}
    )
    refresh_token = create_refresh_token(
        data={"sub": user_id, "email": email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


async def authenticate_user(email: str, password: str, db: AsyncSession) -> Optional[Employee]:
    """Authenticate user with email and password"""
    result = await db.execute(
        select(Employee).where(
            Employee.email == email,
            Employee.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    # Note: In production, you'd have a password field in the Employee model
    # For now, this is a placeholder
    # if not verify_password(password, user.password_hash):
    #     return None
    
    return user
