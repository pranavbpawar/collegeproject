"""
TBAPS VPN Connection Logger

Monitors OpenVPN status log and records connections to PostgreSQL database.
Provides real-time connection tracking and statistics.
"""

import asyncio
import asyncpg
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/vpn-logger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ztuser:ztpass@localhost:5432/zerotrust')
STATUS_LOG_FILE = os.getenv('LOG_FILE', '/var/log/openvpn/openvpn-status.log')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '30'))  # seconds


class VPNConnectionLogger:
    """
    VPN Connection Logger
    
    Monitors OpenVPN status log and records connection events to database.
    """
    
    def __init__(self, database_url: str, status_log_file: str):
        """
        Initialize VPN logger
        
        Args:
            database_url: PostgreSQL connection string
            status_log_file: Path to OpenVPN status log
        """
        self.database_url = database_url
        self.status_log_file = status_log_file
        self.db_pool = None
        self.running = True
        self.known_connections = {}  # Track active connections
        
        logger.info(f"VPN Logger initialized")
        logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")
        logger.info(f"Status log: {status_log_file}")
    
    async def start(self):
        """Start the logger service"""
        logger.info("Starting VPN Connection Logger...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Connect to database
        await self._connect_database()
        
        # Main monitoring loop
        while self.running:
            try:
                await self._process_status_log()
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(POLL_INTERVAL)
        
        # Cleanup
        await self._disconnect_database()
        logger.info("VPN Connection Logger stopped")
    
    async def _connect_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.db_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def _disconnect_database(self):
        """Disconnect from database"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database connection closed")
    
    async def _process_status_log(self):
        """Process OpenVPN status log"""
        try:
            if not os.path.exists(self.status_log_file):
                logger.warning(f"Status log file not found: {self.status_log_file}")
                return
            
            with open(self.status_log_file, 'r') as f:
                content = f.read()
            
            # Parse connections
            current_connections = self._parse_status_log(content)
            
            # Update database
            await self._update_connections(current_connections)
            
            logger.info(f"Processed {len(current_connections)} active connections")
            
        except Exception as e:
            logger.error(f"Error processing status log: {e}")
    
    def _parse_status_log(self, content: str) -> Dict[str, Dict]:
        """
        Parse OpenVPN status log
        
        Args:
            content: Status log content
        
        Returns:
            Dictionary of active connections
        """
        connections = {}
        
        # Parse client list section
        in_client_list = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('OpenVPN CLIENT LIST'):
                in_client_list = True
                continue
            
            if line.startswith('ROUTING TABLE'):
                in_client_list = False
                continue
            
            if in_client_list and line and not line.startswith('Common Name'):
                # Parse client line
                # Format: Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
                parts = line.split(',')
                
                if len(parts) >= 5:
                    cert_name = parts[0].strip()
                    real_address = parts[1].strip()
                    bytes_received = int(parts[2].strip()) if parts[2].strip().isdigit() else 0
                    bytes_sent = int(parts[3].strip()) if parts[3].strip().isdigit() else 0
                    connected_since = parts[4].strip()
                    
                    # Extract employee ID from cert name (emp-XXX)
                    employee_id_match = re.match(r'emp-(.+)', cert_name)
                    employee_id = employee_id_match.group(1) if employee_id_match else cert_name
                    
                    # Extract IP and port
                    ip_match = re.match(r'(.+):(\d+)', real_address)
                    client_ip = ip_match.group(1) if ip_match else real_address
                    
                    connections[cert_name] = {
                        'employee_id': employee_id,
                        'certificate_name': cert_name,
                        'client_ip': client_ip,
                        'bytes_received': bytes_received,
                        'bytes_sent': bytes_sent,
                        'connected_since': connected_since,
                    }
        
        return connections
    
    async def _update_connections(self, current_connections: Dict[str, Dict]):
        """
        Update connection records in database
        
        Args:
            current_connections: Currently active connections
        """
        async with self.db_pool.acquire() as conn:
            # Check for new connections
            for cert_name, conn_data in current_connections.items():
                if cert_name not in self.known_connections:
                    # New connection
                    await self._log_new_connection(conn, conn_data)
                    self.known_connections[cert_name] = conn_data
                else:
                    # Update existing connection stats
                    await self._update_connection_stats(conn, conn_data)
            
            # Check for disconnections
            disconnected = set(self.known_connections.keys()) - set(current_connections.keys())
            for cert_name in disconnected:
                await self._log_disconnection(conn, self.known_connections[cert_name])
                del self.known_connections[cert_name]
    
    async def _log_new_connection(self, conn, conn_data: Dict):
        """Log new VPN connection"""
        try:
            await conn.execute('''
                INSERT INTO vpn_connections (
                    id,
                    employee_id,
                    certificate_name,
                    connected_at,
                    client_ip_address,
                    connection_protocol,
                    cipher,
                    bytes_received,
                    bytes_sent
                ) VALUES (
                    gen_random_uuid(),
                    $1,
                    $2,
                    NOW(),
                    $3,
                    'udp',
                    'AES-256-CBC',
                    $4,
                    $5
                )
            ''', conn_data['employee_id'], conn_data['certificate_name'],
                conn_data['client_ip'], conn_data['bytes_received'], conn_data['bytes_sent'])
            
            # Log audit event
            await conn.execute('''
                INSERT INTO vpn_audit_log (
                    id,
                    event_type,
                    employee_id,
                    certificate_name,
                    source_ip,
                    details,
                    severity
                ) VALUES (
                    gen_random_uuid(),
                    'connection_established',
                    $1,
                    $2,
                    $3,
                    $4,
                    'info'
                )
            ''', conn_data['employee_id'], conn_data['certificate_name'],
                conn_data['client_ip'], f'{{"connected_at": "{datetime.utcnow().isoformat()}"}}')
            
            logger.info(f"New connection: {conn_data['certificate_name']} from {conn_data['client_ip']}")
            
        except Exception as e:
            logger.error(f"Error logging new connection: {e}")
    
    async def _update_connection_stats(self, conn, conn_data: Dict):
        """Update connection statistics"""
        try:
            await conn.execute('''
                UPDATE vpn_connections
                SET 
                    bytes_received = $1,
                    bytes_sent = $2
                WHERE certificate_name = $3
                AND disconnected_at IS NULL
            ''', conn_data['bytes_received'], conn_data['bytes_sent'], conn_data['certificate_name'])
            
        except Exception as e:
            logger.error(f"Error updating connection stats: {e}")
    
    async def _log_disconnection(self, conn, conn_data: Dict):
        """Log VPN disconnection"""
        try:
            await conn.execute('''
                UPDATE vpn_connections
                SET 
                    disconnected_at = NOW(),
                    disconnect_reason = 'normal'
                WHERE certificate_name = $1
                AND disconnected_at IS NULL
            ''', conn_data['certificate_name'])
            
            # Log audit event
            await conn.execute('''
                INSERT INTO vpn_audit_log (
                    id,
                    event_type,
                    employee_id,
                    certificate_name,
                    source_ip,
                    details,
                    severity
                ) VALUES (
                    gen_random_uuid(),
                    'connection_terminated',
                    $1,
                    $2,
                    $3,
                    $4,
                    'info'
                )
            ''', conn_data['employee_id'], conn_data['certificate_name'],
                conn_data['client_ip'], f'{{"disconnected_at": "{datetime.utcnow().isoformat()}"}}')
            
            logger.info(f"Disconnection: {conn_data['certificate_name']}")
            
        except Exception as e:
            logger.error(f"Error logging disconnection: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


async def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("TBAPS VPN Connection Logger")
    logger.info("=" * 80)
    
    # Create logger instance
    vpn_logger = VPNConnectionLogger(DATABASE_URL, STATUS_LOG_FILE)
    
    # Start monitoring
    await vpn_logger.start()


if __name__ == '__main__':
    asyncio.run(main())
