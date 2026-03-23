"""
TBAPS Traffic Monitor - Packet Capture Service

Captures network packets from VPN interface and extracts metadata:
- DNS queries
- TLS SNI (Server Name Indication) for HTTPS sites
- Packet timing and sizes

Privacy-balanced approach: Metadata only, no payload inspection
"""

import asyncio
import asyncpg
import logging
import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import signal
import sys
import subprocess

try:
    from scapy.all import sniff, DNS, IP, TCP, TLS, DNSQR, DNSRR
    from scapy.layers.tls.handshake import TLSClientHello
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available, will use tcpdump fallback")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/traffic-monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ztuser:ztpass@localhost:5432/zerotrust')
VPN_INTERFACE = os.getenv('VPN_INTERFACE', 'tun0')
CAPTURE_FILTER = os.getenv('CAPTURE_FILTER', 'udp port 53 or tcp port 443')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
FLUSH_INTERVAL = int(os.getenv('FLUSH_INTERVAL', '10'))  # seconds


class PacketCapture:
    """
    Packet Capture Service
    
    Captures DNS queries and TLS SNI from VPN traffic
    Privacy-focused: metadata only, no payloads
    """
    
    def __init__(self, database_url: str, interface: str):
        """
        Initialize packet capture service
        
        Args:
            database_url: PostgreSQL connection string
            interface: Network interface to capture (e.g., tun0)
        """
        self.database_url = database_url
        self.interface = interface
        self.db_pool = None
        self.running = True
        
        # Buffers for batch inserts
        self.dns_buffer = []
        self.packet_buffer = []
        self.last_flush = datetime.utcnow()
        
        # VPN client IP to employee ID mapping (cached)
        self.ip_to_employee = {}
        
        logger.info(f"Packet Capture initialized on interface {interface}")
    
    async def start(self):
        """Start the packet capture service"""
        logger.info("Starting Traffic Monitor - Packet Capture Service...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Connect to database
        await self._connect_database()
        
        # Load IP to employee mapping
        await self._load_ip_mapping()
        
        # Start background flush task
        flush_task = asyncio.create_task(self._periodic_flush())
        
        # Start packet capture
        try:
            if SCAPY_AVAILABLE:
                await self._capture_with_scapy()
            else:
                await self._capture_with_tcpdump()
        except Exception as e:
            logger.error(f"Capture error: {e}")
        finally:
            # Cleanup
            flush_task.cancel()
            await self._flush_buffers()
            await self._disconnect_database()
            logger.info("Packet Capture Service stopped")
    
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
    
    async def _load_ip_mapping(self):
        """Load VPN IP to employee ID mapping from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT vpn_ip_address::text, employee_id
                    FROM vpn_connections
                    WHERE disconnected_at IS NULL
                ''')
                
                self.ip_to_employee = {row['vpn_ip_address']: row['employee_id'] for row in rows}
                logger.info(f"Loaded {len(self.ip_to_employee)} active VPN connections")
        except Exception as e:
            logger.error(f"Error loading IP mapping: {e}")
    
    async def _capture_with_scapy(self):
        """Capture packets using Scapy"""
        logger.info(f"Starting Scapy packet capture on {self.interface}")
        
        def packet_handler(packet):
            """Handle captured packet"""
            try:
                asyncio.create_task(self._process_packet(packet))
            except Exception as e:
                logger.error(f"Error processing packet: {e}")
        
        # Start sniffing
        sniff(
            iface=self.interface,
            filter=CAPTURE_FILTER,
            prn=packet_handler,
            store=False,
            stop_filter=lambda x: not self.running
        )
    
    async def _capture_with_tcpdump(self):
        """Fallback: Capture packets using tcpdump"""
        logger.info(f"Starting tcpdump capture on {self.interface}")
        
        cmd = [
            'tcpdump',
            '-i', self.interface,
            '-n',  # Don't resolve hostnames
            '-l',  # Line buffered
            '-tttt',  # Timestamp
            CAPTURE_FILTER
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        while self.running:
            line = process.stdout.readline()
            if line:
                await self._process_tcpdump_line(line)
    
    async def _process_packet(self, packet):
        """Process captured packet and extract metadata"""
        try:
            if not packet.haslayer(IP):
                return
            
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            
            # Get employee ID from source IP
            employee_id = self.ip_to_employee.get(src_ip)
            if not employee_id:
                # Refresh mapping periodically
                await self._load_ip_mapping()
                employee_id = self.ip_to_employee.get(src_ip)
                if not employee_id:
                    return  # Not a VPN client
            
            # Process DNS queries
            if packet.haslayer(DNS) and packet.haslayer(DNSQR):
                await self._process_dns_query(packet, employee_id, src_ip)
            
            # Process TLS SNI
            if packet.haslayer(TCP) and packet.haslayer(TLS):
                await self._process_tls_packet(packet, employee_id, src_ip, dst_ip)
            
            # Store packet metadata
            await self._store_packet_metadata(packet, employee_id, src_ip, dst_ip)
            
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
    
    async def _process_dns_query(self, packet, employee_id: str, client_ip: str):
        """Extract and buffer DNS query"""
        try:
            dns_layer = packet[DNS]
            
            if dns_layer.qr == 0:  # Query (not response)
                query = dns_layer.qd.qname.decode('utf-8').rstrip('.')
                query_type = self._get_dns_type(dns_layer.qd.qtype)
                
                dns_data = {
                    'employee_id': employee_id,
                    'domain': query,
                    'query_type': query_type,
                    'client_ip': client_ip,
                    'resolved_ip': None,
                    'timestamp': datetime.utcnow()
                }
                
                self.dns_buffer.append(dns_data)
                
                # Check if buffer is full
                if len(self.dns_buffer) >= BATCH_SIZE:
                    await self._flush_dns_buffer()
                
        except Exception as e:
            logger.error(f"Error processing DNS query: {e}")
    
    async def _process_tls_packet(self, packet, employee_id: str, src_ip: str, dst_ip: str):
        """Extract TLS SNI (Server Name Indication)"""
        try:
            if packet.haslayer(TLSClientHello):
                tls_layer = packet[TLSClientHello]
                
                # Extract SNI from extensions
                sni = None
                if hasattr(tls_layer, 'ext'):
                    for ext in tls_layer.ext:
                        if hasattr(ext, 'servernames'):
                            for servername in ext.servernames:
                                if hasattr(servername, 'servername'):
                                    sni = servername.servername.decode('utf-8')
                                    break
                
                if sni:
                    # Store as packet metadata with SNI
                    packet_data = {
                        'employee_id': employee_id,
                        'source_ip': src_ip,
                        'destination_ip': dst_ip,
                        'destination_port': packet[TCP].dport,
                        'protocol': 'TCP',
                        'tls_sni': sni,
                        'tls_version': 'TLS',
                        'packet_size_bytes': len(packet),
                        'timestamp': datetime.utcnow()
                    }
                    
                    self.packet_buffer.append(packet_data)
                    
                    if len(self.packet_buffer) >= BATCH_SIZE:
                        await self._flush_packet_buffer()
        
        except Exception as e:
            logger.error(f"Error processing TLS packet: {e}")
    
    async def _store_packet_metadata(self, packet, employee_id: str, src_ip: str, dst_ip: str):
        """Store basic packet metadata"""
        try:
            if packet.haslayer(TCP):
                packet_data = {
                    'employee_id': employee_id,
                    'source_ip': src_ip,
                    'destination_ip': dst_ip,
                    'destination_port': packet[TCP].dport,
                    'protocol': 'TCP',
                    'tls_sni': None,
                    'tls_version': None,
                    'packet_size_bytes': len(packet),
                    'timestamp': datetime.utcnow()
                }
                
                self.packet_buffer.append(packet_data)
        
        except Exception as e:
            logger.error(f"Error storing packet metadata: {e}")
    
    async def _process_tcpdump_line(self, line: str):
        """Process tcpdump output line"""
        # Parse tcpdump output for DNS queries
        # Format: timestamp IP src.port > dst.port: query
        dns_match = re.search(r'(\d+\.\d+\.\d+\.\d+)\.(\d+) > \d+\.\d+\.\d+\.\d+\.53.*? ([A-Za-z0-9.-]+)\?', line)
        
        if dns_match:
            src_ip = dns_match.group(1)
            domain = dns_match.group(3)
            
            employee_id = self.ip_to_employee.get(src_ip)
            if employee_id:
                dns_data = {
                    'employee_id': employee_id,
                    'domain': domain,
                    'query_type': 'A',
                    'client_ip': src_ip,
                    'resolved_ip': None,
                    'timestamp': datetime.utcnow()
                }
                
                self.dns_buffer.append(dns_data)
    
    async def _flush_dns_buffer(self):
        """Flush DNS query buffer to database"""
        if not self.dns_buffer:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.executemany('''
                    INSERT INTO traffic_dns_queries (
                        employee_id, domain, query_type, client_ip, 
                        resolved_ip, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                ''', [(d['employee_id'], d['domain'], d['query_type'], 
                       d['client_ip'], d['resolved_ip'], d['timestamp']) 
                      for d in self.dns_buffer])
                
                logger.info(f"Flushed {len(self.dns_buffer)} DNS queries to database")
                self.dns_buffer.clear()
        
        except Exception as e:
            logger.error(f"Error flushing DNS buffer: {e}")
    
    async def _flush_packet_buffer(self):
        """Flush packet metadata buffer to database"""
        if not self.packet_buffer:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.executemany('''
                    INSERT INTO traffic_packet_metadata (
                        employee_id, source_ip, destination_ip, destination_port,
                        protocol, tls_sni, tls_version, packet_size_bytes, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', [(p['employee_id'], p['source_ip'], p['destination_ip'], 
                       p['destination_port'], p['protocol'], p['tls_sni'],
                       p['tls_version'], p['packet_size_bytes'], p['timestamp']) 
                      for p in self.packet_buffer])
                
                logger.info(f"Flushed {len(self.packet_buffer)} packet metadata to database")
                self.packet_buffer.clear()
        
        except Exception as e:
            logger.error(f"Error flushing packet buffer: {e}")
    
    async def _flush_buffers(self):
        """Flush all buffers"""
        await self._flush_dns_buffer()
        await self._flush_packet_buffer()
    
    async def _periodic_flush(self):
        """Periodically flush buffers"""
        while self.running:
            try:
                await asyncio.sleep(FLUSH_INTERVAL)
                await self._flush_buffers()
                
                # Refresh IP mapping every flush
                await self._load_ip_mapping()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    def _get_dns_type(self, qtype: int) -> str:
        """Convert DNS query type to string"""
        types = {
            1: 'A',
            2: 'NS',
            5: 'CNAME',
            6: 'SOA',
            12: 'PTR',
            15: 'MX',
            16: 'TXT',
            28: 'AAAA',
            33: 'SRV'
        }
        return types.get(qtype, 'UNKNOWN')
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


async def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("TBAPS Traffic Monitor - Packet Capture Service")
    logger.info("=" * 80)
    logger.info(f"Interface: {VPN_INTERFACE}")
    logger.info(f"Filter: {CAPTURE_FILTER}")
    logger.info(f"Privacy Mode: Metadata only (no payloads)")
    logger.info("=" * 80)
    
    # Check if running as root (required for packet capture)
    if os.geteuid() != 0:
        logger.error("ERROR: Packet capture requires root privileges")
        logger.error("Run with: sudo python packet_capture.py")
        sys.exit(1)
    
    # Create capture instance
    capture = PacketCapture(DATABASE_URL, VPN_INTERFACE)
    
    # Start capture
    await capture.start()


if __name__ == '__main__':
    asyncio.run(main())
