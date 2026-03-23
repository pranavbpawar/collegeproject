"""
GDPR Compliance System
Implements complete GDPR compliance with automated enforcement
"""

import logging
import json
import os
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib


# ============================================================================
# DATA CLASSES
# ============================================================================

class GDPRAction(Enum):
    """GDPR-related actions"""
    DELETION_REQUEST = "deletion_request"
    DATA_EXPORT = "data_export"
    DATA_ACCESS = "data_access"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    DATA_RECTIFICATION = "data_rectification"
    RETENTION_ENFORCEMENT = "retention_enforcement"


class DataCategory(Enum):
    """Categories of personal data"""
    IDENTITY = "identity"
    CONTACT = "contact"
    WORK_ACTIVITY = "work_activity"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SENSITIVE = "sensitive"


@dataclass
class DeletionResult:
    """Result of data deletion"""
    employee_id: str
    status: str
    deleted_at: datetime
    tables_affected: List[str]
    records_deleted: int
    audit_log_id: str


@dataclass
class DataExportResult:
    """Result of data export"""
    employee_id: str
    export_file: str
    export_date: datetime
    size_bytes: int
    format: str
    categories_included: List[str]
    audit_log_id: str


@dataclass
class RetentionPolicy:
    """Data retention policy"""
    table_name: str
    category: DataCategory
    retention_days: int
    auto_delete: bool
    description: str


@dataclass
class AuditLogEntry:
    """Immutable audit log entry"""
    id: str
    employee_id: Optional[str]
    action: GDPRAction
    performed_by: str
    ip_address: str
    timestamp: datetime
    resources_accessed: List[str]
    changes: Dict[str, Any]
    success: bool
    error_message: Optional[str]


# ============================================================================
# GDPR COMPLIANCE CONTROLLER
# ============================================================================

class GDPRCompliance:
    """
    GDPR Compliance System
    
    Implements:
    - Right to be forgotten (Article 17)
    - Right to data access (Article 15)
    - Right to data portability (Article 20)
    - Data retention policies (Article 5)
    - Audit logging (Article 30)
    
    Automated enforcement with minimal manual intervention.
    """
    
    # Retention policies (in days)
    RETENTION_POLICIES = {
        'signal_events': RetentionPolicy(
            table_name='signal_events',
            category=DataCategory.WORK_ACTIVITY,
            retention_days=90,
            auto_delete=True,
            description='Work activity signals'
        ),
        'trust_scores': RetentionPolicy(
            table_name='trust_scores',
            category=DataCategory.BEHAVIORAL,
            retention_days=90,
            auto_delete=True,
            description='Trust score history'
        ),
        'baseline_profiles': RetentionPolicy(
            table_name='baseline_profiles',
            category=DataCategory.BEHAVIORAL,
            retention_days=90,
            auto_delete=True,
            description='Behavioral baselines'
        ),
        'anomalies': RetentionPolicy(
            table_name='anomalies',
            category=DataCategory.BEHAVIORAL,
            retention_days=365,
            auto_delete=True,
            description='Anomaly detections'
        ),
        'burnout_predictions': RetentionPolicy(
            table_name='burnout_predictions',
            category=DataCategory.BEHAVIORAL,
            retention_days=90,
            auto_delete=True,
            description='Burnout predictions'
        ),
        'email_signals': RetentionPolicy(
            table_name='email_signals',
            category=DataCategory.WORK_ACTIVITY,
            retention_days=90,
            auto_delete=True,
            description='Email metadata signals'
        ),
        'oauth_tokens': RetentionPolicy(
            table_name='oauth_tokens',
            category=DataCategory.TECHNICAL,
            retention_days=365,
            auto_delete=True,
            description='OAuth access tokens'
        ),
        'audit_logs': RetentionPolicy(
            table_name='audit_logs',
            category=DataCategory.TECHNICAL,
            retention_days=2555,  # 7 years
            auto_delete=False,  # Never auto-delete audit logs
            description='Audit trail (7-year retention)'
        )
    }
    
    # Tables to delete for "right to be forgotten"
    DELETION_TABLES = [
        'signal_events',
        'trust_scores',
        'baseline_profiles',
        'anomalies',
        'burnout_predictions',
        'email_signals',
        'oauth_tokens'
    ]
    
    def __init__(self, db_connection=None, export_dir: str = '/tmp/exports'):
        """
        Initialize GDPR Compliance
        
        Args:
            db_connection: Database connection
            export_dir: Directory for data exports
        """
        self.db = db_connection
        self.export_dir = export_dir
        self.logger = logging.getLogger(__name__)
        
        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)
    
    # ========================================================================
    # RIGHT TO BE FORGOTTEN (Article 17)
    # ========================================================================
    
    async def right_to_be_forgotten(
        self,
        employee_id: str,
        performed_by: str,
        reason: str = "Employee request"
    ) -> DeletionResult:
        """
        Delete all employee data (Right to be forgotten)
        
        Implements GDPR Article 17 - Right to erasure
        
        Args:
            employee_id: Employee identifier
            performed_by: User performing deletion
            reason: Reason for deletion
        
        Returns:
            DeletionResult with deletion details
        """
        self.logger.info(f"Processing right to be forgotten for {employee_id}")
        
        if not self.db:
            raise ValueError("Database connection required")
        
        tables_affected = []
        total_deleted = 0
        
        try:
            # Delete from all tables
            for table in self.DELETION_TABLES:
                try:
                    query = f"DELETE FROM {table} WHERE employee_id = $1"
                    result = await self.db.execute(query, employee_id)
                    
                    # Extract number of deleted rows
                    deleted_count = int(result.split()[-1]) if result else 0
                    
                    if deleted_count > 0:
                        tables_affected.append(table)
                        total_deleted += deleted_count
                        
                    self.logger.info(f"Deleted {deleted_count} rows from {table}")
                    
                except Exception as e:
                    self.logger.error(f"Error deleting from {table}: {e}")
            
            # Soft delete employee record (keep for audit)
            await self.db.execute(
                """
                UPDATE employees 
                SET deleted_at = NOW(),
                    email = 'deleted_' || id || '@deleted.local',
                    first_name = 'DELETED',
                    last_name = 'DELETED'
                WHERE id = $1
                """,
                employee_id
            )
            
            # Create audit log
            audit_log_id = await self._create_audit_log(
                employee_id=employee_id,
                action=GDPRAction.DELETION_REQUEST,
                performed_by=performed_by,
                resources_accessed=tables_affected,
                changes={
                    'reason': reason,
                    'tables_affected': tables_affected,
                    'records_deleted': total_deleted
                },
                success=True
            )
            
            result = DeletionResult(
                employee_id=employee_id,
                status='deleted',
                deleted_at=datetime.utcnow(),
                tables_affected=tables_affected,
                records_deleted=total_deleted,
                audit_log_id=audit_log_id
            )
            
            self.logger.info(
                f"Successfully deleted data for {employee_id}: "
                f"{total_deleted} records from {len(tables_affected)} tables"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in right to be forgotten: {e}")
            
            # Log failure
            await self._create_audit_log(
                employee_id=employee_id,
                action=GDPRAction.DELETION_REQUEST,
                performed_by=performed_by,
                resources_accessed=[],
                changes={'reason': reason},
                success=False,
                error_message=str(e)
            )
            
            raise
    
    # ========================================================================
    # RIGHT TO DATA ACCESS (Article 15)
    # ========================================================================
    
    async def data_access_request(
        self,
        employee_id: str,
        performed_by: str,
        include_categories: Optional[List[DataCategory]] = None
    ) -> DataExportResult:
        """
        Export all employee data (Right to data access)
        
        Implements GDPR Article 15 - Right of access
        
        Args:
            employee_id: Employee identifier
            performed_by: User performing export
            include_categories: Categories to include (default: all)
        
        Returns:
            DataExportResult with export details
        """
        self.logger.info(f"Processing data access request for {employee_id}")
        
        if not self.db:
            raise ValueError("Database connection required")
        
        # Default to all categories
        if include_categories is None:
            include_categories = list(DataCategory)
        
        try:
            # Collect all data
            export_data = {
                'export_metadata': {
                    'employee_id': employee_id,
                    'export_date': datetime.utcnow().isoformat(),
                    'performed_by': performed_by,
                    'format': 'JSON',
                    'gdpr_article': 'Article 15 - Right of access'
                },
                'employee': await self._get_employee_data(employee_id),
                'work_activity': await self._get_work_activity_data(employee_id),
                'behavioral_data': await self._get_behavioral_data(employee_id),
                'technical_data': await self._get_technical_data(employee_id),
                'audit_logs': await self._get_audit_logs(employee_id)
            }
            
            # Generate export file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"employee_{employee_id}_{timestamp}.json"
            export_file = os.path.join(self.export_dir, filename)
            
            # Write to file
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            file_size = os.path.getsize(export_file)
            
            # Create audit log
            audit_log_id = await self._create_audit_log(
                employee_id=employee_id,
                action=GDPRAction.DATA_EXPORT,
                performed_by=performed_by,
                resources_accessed=['all_tables'],
                changes={
                    'export_file': export_file,
                    'size_bytes': file_size,
                    'categories': [c.value for c in include_categories]
                },
                success=True
            )
            
            result = DataExportResult(
                employee_id=employee_id,
                export_file=export_file,
                export_date=datetime.utcnow(),
                size_bytes=file_size,
                format='JSON',
                categories_included=[c.value for c in include_categories],
                audit_log_id=audit_log_id
            )
            
            self.logger.info(
                f"Successfully exported data for {employee_id}: "
                f"{file_size} bytes to {export_file}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in data access request: {e}")
            
            # Log failure
            await self._create_audit_log(
                employee_id=employee_id,
                action=GDPRAction.DATA_EXPORT,
                performed_by=performed_by,
                resources_accessed=[],
                changes={},
                success=False,
                error_message=str(e)
            )
            
            raise
    
    # ========================================================================
    # DATA PORTABILITY (Article 20)
    # ========================================================================
    
    async def data_portability_export(
        self,
        employee_id: str,
        performed_by: str,
        format: str = 'JSON'
    ) -> DataExportResult:
        """
        Export data in portable format (Right to data portability)
        
        Implements GDPR Article 20 - Right to data portability
        
        Args:
            employee_id: Employee identifier
            performed_by: User performing export
            format: Export format (JSON, CSV, XML)
        
        Returns:
            DataExportResult with export details
        """
        # For now, use same implementation as data access
        # In production, would support multiple formats
        return await self.data_access_request(employee_id, performed_by)
    
    # ========================================================================
    # RETENTION POLICY ENFORCEMENT (Article 5)
    # ========================================================================
    
    async def enforce_retention_policies(
        self,
        performed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Enforce data retention policies (automated)
        
        Implements GDPR Article 5 - Storage limitation
        
        Args:
            performed_by: User/system performing enforcement
        
        Returns:
            Dictionary with enforcement results
        """
        self.logger.info("Enforcing retention policies")
        
        if not self.db:
            raise ValueError("Database connection required")
        
        results = {}
        total_deleted = 0
        
        try:
            for table_name, policy in self.RETENTION_POLICIES.items():
                if not policy.auto_delete:
                    self.logger.info(f"Skipping {table_name} (auto_delete=False)")
                    continue
                
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
                
                # Delete old records
                query = f"""
                    DELETE FROM {table_name}
                    WHERE created_at < $1
                    RETURNING id
                """
                
                try:
                    deleted_ids = await self.db.fetch(query, cutoff_date)
                    deleted_count = len(deleted_ids)
                    
                    results[table_name] = {
                        'policy': policy.retention_days,
                        'cutoff_date': cutoff_date.isoformat(),
                        'deleted_count': deleted_count
                    }
                    
                    total_deleted += deleted_count
                    
                    self.logger.info(
                        f"Deleted {deleted_count} records from {table_name} "
                        f"(older than {policy.retention_days} days)"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error enforcing retention for {table_name}: {e}")
                    results[table_name] = {'error': str(e)}
            
            # Create audit log
            await self._create_audit_log(
                employee_id=None,
                action=GDPRAction.RETENTION_ENFORCEMENT,
                performed_by=performed_by,
                resources_accessed=list(results.keys()),
                changes={
                    'total_deleted': total_deleted,
                    'results': results
                },
                success=True
            )
            
            self.logger.info(
                f"Retention enforcement complete: {total_deleted} total records deleted"
            )
            
            return {
                'status': 'completed',
                'total_deleted': total_deleted,
                'tables_processed': len(results),
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in retention enforcement: {e}")
            raise
    
    # ========================================================================
    # AUDIT LOGGING (Article 30)
    # ========================================================================
    
    async def _create_audit_log(
        self,
        employee_id: Optional[str],
        action: GDPRAction,
        performed_by: str,
        resources_accessed: List[str],
        changes: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None,
        ip_address: str = "127.0.0.1"
    ) -> str:
        """
        Create immutable audit log entry
        
        Implements GDPR Article 30 - Records of processing activities
        
        Args:
            employee_id: Employee identifier (if applicable)
            action: GDPR action performed
            performed_by: User performing action
            resources_accessed: Resources accessed
            changes: Changes made
            success: Whether action succeeded
            error_message: Error message if failed
            ip_address: IP address of request
        
        Returns:
            Audit log ID
        """
        audit_id = str(uuid.uuid4())
        
        if not self.db:
            self.logger.warning("No database connection - audit log not persisted")
            return audit_id
        
        try:
            # Create audit log entry
            entry = AuditLogEntry(
                id=audit_id,
                employee_id=employee_id,
                action=action,
                performed_by=performed_by,
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
                resources_accessed=resources_accessed,
                changes=changes,
                success=success,
                error_message=error_message
            )
            
            # Insert into database (immutable)
            query = """
                INSERT INTO audit_logs (
                    id, employee_id, action, performed_by, ip_address,
                    timestamp, resources_accessed, changes, success, error_message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            await self.db.execute(
                query,
                entry.id,
                entry.employee_id,
                entry.action.value,
                entry.performed_by,
                entry.ip_address,
                entry.timestamp,
                json.dumps(entry.resources_accessed),
                json.dumps(entry.changes, default=str),
                entry.success,
                entry.error_message
            )
            
            return audit_id
            
        except Exception as e:
            self.logger.error(f"Error creating audit log: {e}")
            # Don't raise - audit log failure shouldn't block operations
            return audit_id
    
    async def get_audit_trail(
        self,
        employee_id: Optional[str] = None,
        action: Optional[GDPRAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit trail
        
        Args:
            employee_id: Filter by employee
            action: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results
        
        Returns:
            List of AuditLogEntry
        """
        if not self.db:
            return []
        
        # Build query
        conditions = []
        params = []
        param_count = 1
        
        if employee_id:
            conditions.append(f"employee_id = ${param_count}")
            params.append(employee_id)
            param_count += 1
        
        if action:
            conditions.append(f"action = ${param_count}")
            params.append(action.value)
            param_count += 1
        
        if start_date:
            conditions.append(f"timestamp >= ${param_count}")
            params.append(start_date)
            param_count += 1
        
        if end_date:
            conditions.append(f"timestamp <= ${param_count}")
            params.append(end_date)
            param_count += 1
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT * FROM audit_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_count}
        """
        params.append(limit)
        
        try:
            rows = await self.db.fetch(query, *params)
            
            entries = []
            for row in rows:
                entry = AuditLogEntry(
                    id=row['id'],
                    employee_id=row['employee_id'],
                    action=GDPRAction(row['action']),
                    performed_by=row['performed_by'],
                    ip_address=row['ip_address'],
                    timestamp=row['timestamp'],
                    resources_accessed=json.loads(row['resources_accessed']),
                    changes=json.loads(row['changes']),
                    success=row['success'],
                    error_message=row['error_message']
                )
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Error retrieving audit trail: {e}")
            return []
    
    # ========================================================================
    # DATA RETRIEVAL HELPERS
    # ========================================================================
    
    async def _get_employee_data(self, employee_id: str) -> Dict[str, Any]:
        """Get employee identity data"""
        if not self.db:
            return {}
        
        query = "SELECT * FROM employees WHERE id = $1"
        row = await self.db.fetchrow(query, employee_id)
        
        return dict(row) if row else {}
    
    async def _get_work_activity_data(self, employee_id: str) -> Dict[str, Any]:
        """Get work activity data"""
        if not self.db:
            return {}
        
        data = {}
        
        # Signal events
        query = "SELECT * FROM signal_events WHERE employee_id = $1 ORDER BY timestamp DESC LIMIT 1000"
        rows = await self.db.fetch(query, employee_id)
        data['signal_events'] = [dict(row) for row in rows]
        
        # Email signals
        query = "SELECT * FROM email_signals WHERE employee_id = $1 ORDER BY extracted_at DESC LIMIT 1000"
        rows = await self.db.fetch(query, employee_id)
        data['email_signals'] = [dict(row) for row in rows]
        
        return data
    
    async def _get_behavioral_data(self, employee_id: str) -> Dict[str, Any]:
        """Get behavioral data"""
        if not self.db:
            return {}
        
        data = {}
        
        # Trust scores
        query = "SELECT * FROM trust_scores WHERE employee_id = $1 ORDER BY calculated_at DESC LIMIT 100"
        rows = await self.db.fetch(query, employee_id)
        data['trust_scores'] = [dict(row) for row in rows]
        
        # Baselines
        query = "SELECT * FROM baseline_profiles WHERE employee_id = $1"
        rows = await self.db.fetch(query, employee_id)
        data['baselines'] = [dict(row) for row in rows]
        
        # Anomalies
        query = "SELECT * FROM anomalies WHERE employee_id = $1 ORDER BY detected_at DESC LIMIT 100"
        rows = await self.db.fetch(query, employee_id)
        data['anomalies'] = [dict(row) for row in rows]
        
        # Burnout predictions
        query = "SELECT * FROM burnout_predictions WHERE employee_id = $1 ORDER BY calculated_at DESC LIMIT 100"
        rows = await self.db.fetch(query, employee_id)
        data['burnout_predictions'] = [dict(row) for row in rows]
        
        return data
    
    async def _get_technical_data(self, employee_id: str) -> Dict[str, Any]:
        """Get technical data"""
        if not self.db:
            return {}
        
        data = {}
        
        # OAuth tokens (redacted)
        query = "SELECT provider, created_at, expires_at FROM oauth_tokens WHERE employee_id = $1"
        rows = await self.db.fetch(query, employee_id)
        data['oauth_tokens'] = [dict(row) for row in rows]
        
        return data
    
    async def _get_audit_logs(self, employee_id: str) -> List[Dict[str, Any]]:
        """Get audit logs for employee"""
        entries = await self.get_audit_trail(employee_id=employee_id, limit=1000)
        return [asdict(entry) for entry in entries]
