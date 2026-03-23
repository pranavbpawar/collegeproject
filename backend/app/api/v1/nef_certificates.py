"""
TBAPS NEF Certificate Management API

FastAPI endpoints for programmatic .nef certificate management,
including generation, download, revocation, and monitoring.
"""

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import subprocess
import os
import hashlib
import asyncpg
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://tbaps:password@localhost:5432/tbaps')
NEF_CONFIG_DIR = "/srv/tbaps/vpn/configs"
SCRIPT_DIR = "/srv/tbaps/scripts"

# Pydantic models
class CertificateRequest(BaseModel):
    employee_id: Optional[str] = None
    employee_name: str
    employee_email: EmailStr
    department: Optional[str] = None
    role: Optional[str] = None
    
    @validator('employee_name')
    def validate_name(cls, v):
        if not v or len(v) < 2:
            raise ValueError('Employee name must be at least 2 characters')
        return v


class CertificateRevoke(BaseModel):
    certificate_id: str
    reason: Optional[str] = "Manual revocation"
    
    @validator('reason')
    def validate_reason(cls, v):
        if v and len(v) > 500:
            raise ValueError('Reason must be less than 500 characters')
        return v


class CertificateResponse(BaseModel):
    status: str
    certificate_id: str
    filename: str
    checksum: str
    generated_at: datetime
    expires_at: datetime


class ConnectionLog(BaseModel):
    certificate_id: str
    employee_id: Optional[str]
    connected_at: datetime
    disconnected_at: Optional[datetime]
    ip_address: Optional[str]
    bytes_sent: Optional[int]
    bytes_received: Optional[int]
    status: str


# Database connection pool
db_pool = None


async def get_db_pool():
    """Get database connection pool"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return db_pool


async def get_db():
    """Get database connection"""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn


# API Router
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/nef", tags=["NEF Certificates"])


@router.post("/generate", response_model=CertificateResponse)
async def generate_nef_certificate(
    request: CertificateRequest,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Generate a new .nef VPN certificate for an employee
    
    Args:
        request: Certificate generation request with employee details
    
    Returns:
        CertificateResponse with certificate details
    """
    try:
        logger.info(f"Generating NEF certificate for {request.employee_name}")
        
        # Run certificate generation script
        script_path = os.path.join(SCRIPT_DIR, "generate-nef-certificate.sh")
        result = subprocess.run(
            [script_path, request.employee_name, request.employee_email],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Certificate generation failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Certificate generation failed: {result.stderr}"
            )
        
        # Get certificate details
        cert_id = request.employee_name.replace(' ', '_').lower()
        nef_file = os.path.join(NEF_CONFIG_DIR, f"{cert_id}.nef")
        
        if not os.path.exists(nef_file):
            raise HTTPException(
                status_code=500,
                detail="Certificate file not found after generation"
            )
        
        # Calculate checksum
        with open(nef_file, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        # Get certificate from database
        cert = await db.fetchrow('''
            SELECT issued_at, expires_at
            FROM vpn_certificates
            WHERE certificate_id = $1
        ''', cert_id)
        
        if not cert:
            raise HTTPException(
                status_code=500,
                detail="Certificate not found in database"
            )
        
        logger.info(f"Certificate generated successfully: {cert_id}")
        
        return CertificateResponse(
            status="success",
            certificate_id=cert_id,
            filename=f"{cert_id}.nef",
            checksum=checksum,
            generated_at=cert['issued_at'],
            expires_at=cert['expires_at']
        )
    
    except subprocess.TimeoutExpired:
        logger.error("Certificate generation timeout")
        raise HTTPException(status_code=504, detail="Certificate generation timeout")
    except Exception as e:
        logger.error(f"Error generating certificate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{certificate_id}")
async def download_nef_certificate(
    certificate_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Download a .nef certificate file
    
    Args:
        certificate_id: Certificate identifier
    
    Returns:
        FileResponse with .nef file
    """
    try:
        # Verify certificate exists in database
        cert = await db.fetchrow('''
            SELECT id, status, config_file
            FROM vpn_certificates
            WHERE certificate_id = $1
        ''', certificate_id)
        
        if not cert:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        if cert['status'] != 'active':
            raise HTTPException(
                status_code=403,
                detail=f"Certificate is {cert['status']}, cannot download"
            )
        
        # Get file path
        nef_file = os.path.join(NEF_CONFIG_DIR, cert['config_file'])
        
        if not os.path.exists(nef_file):
            raise HTTPException(status_code=404, detail="Certificate file not found")
        
        # Increment download count
        await db.execute('''
            UPDATE vpn_certificates
            SET download_count = download_count + 1,
                last_downloaded_at = NOW()
            WHERE certificate_id = $1
        ''', certificate_id)
        
        # Log download event
        await db.execute('''
            INSERT INTO nef_delivery_audit (
                id, certificate_id, employee_email, delivery_method,
                delivery_status, checksum
            )
            SELECT 
                gen_random_uuid(), $1, employee_email, 'api_download',
                'delivered', checksum
            FROM vpn_certificates
            WHERE certificate_id = $1
        ''', certificate_id)
        
        logger.info(f"Certificate downloaded: {certificate_id}")
        
        return FileResponse(
            path=nef_file,
            filename=cert['config_file'],
            media_type='application/x-openvpn-profile'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading certificate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revoke")
async def revoke_nef_certificate(
    request: CertificateRevoke,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Revoke a .nef certificate
    
    Args:
        request: Revocation request with certificate ID and reason
    
    Returns:
        Revocation confirmation
    """
    try:
        # Check if certificate exists
        cert = await db.fetchrow('''
            SELECT id, status, employee_email
            FROM vpn_certificates
            WHERE certificate_id = $1
        ''', request.certificate_id)
        
        if not cert:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        if cert['status'] == 'revoked':
            raise HTTPException(status_code=400, detail="Certificate already revoked")
        
        # Revoke certificate
        await db.execute('''
            UPDATE vpn_certificates
            SET status = 'revoked',
                revoked_at = NOW(),
                notes = $2,
                updated_at = NOW()
            WHERE certificate_id = $1
        ''', request.certificate_id, request.reason)
        
        # Log revocation
        await db.execute('''
            INSERT INTO vpn_audit_log (
                id, event_type, certificate_name, details, severity
            ) VALUES (
                gen_random_uuid(), 'certificate_revoked', $1,
                jsonb_build_object('reason', $2, 'revoked_at', NOW()),
                'warning'
            )
        ''', request.certificate_id, request.reason)
        
        # Disconnect active sessions
        await db.execute('''
            UPDATE vpn_connection_logs
            SET disconnected_at = NOW(),
                disconnect_reason = 'certificate_revoked',
                status = 'disconnected'
            WHERE certificate_id = $1
            AND disconnected_at IS NULL
        ''', request.certificate_id)
        
        logger.info(f"Certificate revoked: {request.certificate_id}")
        
        return {
            "status": "revoked",
            "certificate_id": request.certificate_id,
            "reason": request.reason,
            "revoked_at": datetime.now()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking certificate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_nef_certificates(
    status: str = "active",
    limit: int = 100,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    List .nef certificates
    
    Args:
        status: Certificate status filter (active, revoked, expired, all)
        limit: Maximum number of results
    
    Returns:
        List of certificates
    """
    try:
        if status == "all":
            query = '''
                SELECT id, employee_name, employee_email, certificate_id,
                       issued_at, expires_at, status, download_count,
                       last_connection_at, total_connections
                FROM vpn_certificates
                ORDER BY issued_at DESC
                LIMIT $1
            '''
            results = await db.fetch(query, limit)
        else:
            query = '''
                SELECT id, employee_name, employee_email, certificate_id,
                       issued_at, expires_at, status, download_count,
                       last_connection_at, total_connections
                FROM vpn_certificates
                WHERE status = $1
                ORDER BY issued_at DESC
                LIMIT $2
            '''
            results = await db.fetch(query, status, limit)
        
        return [dict(row) for row in results]
    
    except Exception as e:
        logger.error(f"Error listing certificates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{certificate_id}")
async def nef_certificate_status(
    certificate_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Get certificate status and details
    
    Args:
        certificate_id: Certificate identifier
    
    Returns:
        Certificate details
    """
    try:
        cert = await db.fetchrow('''
            SELECT id, employee_name, employee_email, certificate_id,
                   issued_at, expires_at, revoked_at, status,
                   download_count, last_downloaded_at, last_connection_at,
                   total_connections, checksum, notes
            FROM vpn_certificates
            WHERE certificate_id = $1
        ''', certificate_id)
        
        if not cert:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        return dict(cert)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting certificate status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expiring")
async def nef_expiring_soon(
    days: int = 30,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Get certificates expiring soon
    
    Args:
        days: Number of days threshold (default 30)
    
    Returns:
        List of expiring certificates
    """
    try:
        results = await db.fetch('''
            SELECT employee_name, employee_email, certificate_id,
                   expires_at,
                   EXTRACT(DAYS FROM (expires_at - NOW())) AS days_remaining
            FROM vpn_certificates
            WHERE status = 'active'
            AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '$1 days'
            ORDER BY expires_at ASC
        ''', days)
        
        return [dict(row) for row in results]
    
    except Exception as e:
        logger.error(f"Error getting expiring certificates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connection-logs")
async def nef_connection_logs(
    certificate_id: Optional[str] = None,
    limit: int = 100,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Get VPN connection logs
    
    Args:
        certificate_id: Optional certificate ID filter
        limit: Maximum number of results
    
    Returns:
        List of connection logs
    """
    try:
        if certificate_id:
            results = await db.fetch('''
                SELECT id, certificate_id, employee_name, connected_at,
                       disconnected_at, session_duration, ip_address,
                       bytes_sent, bytes_received, status
                FROM vpn_connection_logs
                WHERE certificate_id = $1
                ORDER BY connected_at DESC
                LIMIT $2
            ''', certificate_id, limit)
        else:
            results = await db.fetch('''
                SELECT id, certificate_id, employee_name, connected_at,
                       disconnected_at, ip_address, status
                FROM vpn_connection_logs
                ORDER BY connected_at DESC
                LIMIT $1
            ''', limit)
        
        return [dict(row) for row in results]
    
    except Exception as e:
        logger.error(f"Error getting connection logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def nef_statistics(db: asyncpg.Connection = Depends(get_db)):
    """
    Get NEF certificate statistics
    
    Returns:
        Statistics summary
    """
    try:
        stats = await db.fetchrow('''
            SELECT 
                COUNT(*) FILTER (WHERE status = 'active') AS active_certificates,
                COUNT(*) FILTER (WHERE status = 'revoked') AS revoked_certificates,
                COUNT(*) FILTER (WHERE status = 'expired') AS expired_certificates,
                COUNT(*) AS total_certificates,
                SUM(download_count) AS total_downloads,
                SUM(total_connections) AS total_connections
            FROM vpn_certificates
        ''')
        
        recent_connections = await db.fetchval('''
            SELECT COUNT(*)
            FROM vpn_connection_logs
            WHERE connected_at > NOW() - INTERVAL '24 hours'
        ''')
        
        active_sessions = await db.fetchval('''
            SELECT COUNT(*)
            FROM vpn_connection_logs
            WHERE disconnected_at IS NULL
        ''')
        
        return {
            "certificates": dict(stats),
            "recent_connections_24h": recent_connections,
            "active_sessions": active_sessions,
            "timestamp": datetime.now()
        }
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NEF Certificate Management API",
        "timestamp": datetime.now()
    }
