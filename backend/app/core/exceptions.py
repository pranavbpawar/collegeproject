"""
TBAPS Custom Exceptions
Application-specific exceptions with error codes
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import status


class TBAPSException(Exception):
    """Base exception for TBAPS"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "TBAPS_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class AuthenticationError(TBAPSException):
    """Authentication failed"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(TBAPSException):
    """Authorization failed"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class NotFoundError(TBAPSException):
    """Resource not found"""
    
    def __init__(self, resource: str, resource_id: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{resource} with ID {resource_id} not found",
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {"resource": resource, "resource_id": resource_id}
        )


class ValidationError(TBAPSException):
    """Validation error"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {"field": field} if field else details
        )


class IntegrationError(TBAPSException):
    """Integration error (OAuth, API calls, etc.)"""
    
    def __init__(
        self,
        integration: str,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        super().__init__(
            message=f"{integration}: {message}",
            error_code="INTEGRATION_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details or {"integration": integration, "retry_after": retry_after}
        )


class RateLimitError(TBAPSException):
    """Rate limit exceeded"""
    
    def __init__(self, retry_after: int = 60, details: Optional[Dict] = None):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details or {"retry_after": retry_after}
        )


class DatabaseError(TBAPSException):
    """Database operation error"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {"operation": operation} if operation else details
        )


class TokenExpiredError(TBAPSException):
    """Token expired"""
    
    def __init__(self, token_type: str = "access", details: Optional[Dict] = None):
        super().__init__(
            message=f"{token_type.capitalize()} token has expired",
            error_code="TOKEN_EXPIRED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details or {"token_type": token_type}
        )


class TokenInvalidError(TBAPSException):
    """Token invalid"""
    
    def __init__(self, message: str = "Invalid token", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="TOKEN_INVALID",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class SyncError(TBAPSException):
    """Sync operation error"""
    
    def __init__(
        self,
        integration: str,
        message: str,
        sync_id: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        super().__init__(
            message=f"Sync failed for {integration}: {message}",
            error_code="SYNC_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {"integration": integration, "sync_id": sync_id}
        )


class EncryptionError(TBAPSException):
    """Encryption/decryption error"""
    
    def __init__(self, message: str = "Encryption operation failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="ENCRYPTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )
