"""
TBAPS Traffic Monitor - Website Tracker

Aggregates DNS queries and packet metadata into website visits
Tracks time spent, categorizes websites, calculates productivity scores
"""

import asyncio
import asyncpg
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/website-tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ztuser:ztpass@localhost:5432/zerotrust')
AGGREGATION_INTERVAL = int(os.getenv('AGGREGATION_INTERVAL', '60'))  # seconds
VISIT_TIMEOUT = int(os.getenv('VISIT_TIMEOUT', '300'))  # 5 minutes


class WebsiteTracker:
    """
    Website Visit Tracker
    
    Aggregates DNS queries and packet data into meaningful website visits
    Calculates time spent and productivity scores
    """
    
    def __init__(self, database_url: str):
        """
        Initialize website tracker
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.db_pool = None
        self.running = True
        
        logger.info("Website Tracker initialized")
    
    async def start(self):
        """Start the website tracker service"""
        logger.info("Starting Website Tracker Service...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Connect to database
        await self._connect_database()
        
        # Main aggregation loop
        while self.running:
            try:
                await self._aggregate_website_visits()
                await asyncio.sleep(AGGREGATION_INTERVAL)
            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                await asyncio.sleep(AGGREGATION_INTERVAL)
        
        # Cleanup
        await self._disconnect_database()
        logger.info("Website Tracker Service stopped")
    
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
    
    async def _aggregate_website_visits(self):
        """Aggregate DNS queries and packets into website visits"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get employees with active consent
                employees = await conn.fetch('''
                    SELECT employee_id
                    FROM traffic_monitoring_consent
                    WHERE consented = TRUE
                    AND withdrawn_date IS NULL
                ''')
                
                for employee in employees:
                    employee_id = employee['employee_id']
                    await self._aggregate_employee_visits(conn, employee_id)
                
                logger.info(f"Aggregated visits for {len(employees)} employees")
        
        except Exception as e:
            logger.error(f"Error aggregating website visits: {e}")
    
    async def _aggregate_employee_visits(self, conn, employee_id: str):
        """Aggregate website visits for a single employee"""
        try:
            # Get recent DNS queries (last hour, not yet aggregated)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            dns_queries = await conn.fetch('''
                SELECT DISTINCT domain, MIN(timestamp) as first_seen, MAX(timestamp) as last_seen
                FROM traffic_dns_queries
                WHERE employee_id = $1
                AND timestamp > $2
                AND timestamp > (
                    SELECT COALESCE(MAX(last_visit), '1970-01-01'::timestamp)
                    FROM traffic_website_visits
                    WHERE employee_id = $1
                )
                GROUP BY domain
            ''', employee_id, cutoff_time)
            
            for query in dns_queries:
                domain = query['domain']
                first_seen = query['first_seen']
                last_seen = query['last_seen']
                
                # Get packet count and bytes for this domain
                packet_stats = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as packet_count,
                        SUM(packet_size_bytes) as total_bytes
                    FROM traffic_packet_metadata
                    WHERE employee_id = $1
                    AND (tls_sni = $2 OR destination_ip IN (
                        SELECT DISTINCT resolved_ip
                        FROM traffic_dns_queries
                        WHERE employee_id = $1 AND domain = $2
                    ))
                    AND timestamp BETWEEN $3 AND $4
                ''', employee_id, domain, first_seen, last_seen)
                
                # Categorize domain
                category_info = await conn.fetchrow(
                    'SELECT * FROM categorize_domain($1)',
                    domain
                )
                
                category = category_info['category'] if category_info else 'unknown'
                productivity_score = category_info['productivity_score'] if category_info else 50
                
                # Calculate visit duration
                visit_duration = int((last_seen - first_seen).total_seconds())
                
                # Check if visit already exists (update) or create new
                existing = await conn.fetchrow('''
                    SELECT id FROM traffic_website_visits
                    WHERE employee_id = $1
                    AND domain = $2
                    AND first_visit >= $3 - INTERVAL '5 minutes'
                    ORDER BY first_visit DESC
                    LIMIT 1
                ''', employee_id, domain, first_seen)
                
                if existing:
                    # Update existing visit
                    await conn.execute('''
                        UPDATE traffic_website_visits
                        SET 
                            last_visit = $1,
                            visit_duration_seconds = EXTRACT(EPOCH FROM ($1 - first_visit))::INTEGER,
                            page_count = page_count + $2,
                            bytes_transferred = bytes_transferred + $3
                        WHERE id = $4
                    ''', last_seen, 
                        packet_stats['packet_count'] or 0,
                        packet_stats['total_bytes'] or 0,
                        existing['id'])
                else:
                    # Create new visit
                    await conn.execute('''
                        INSERT INTO traffic_website_visits (
                            employee_id, domain, category, productivity_score,
                            first_visit, last_visit, visit_duration_seconds,
                            page_count, bytes_transferred
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''', employee_id, domain, category, productivity_score,
                        first_seen, last_seen, visit_duration,
                        packet_stats['packet_count'] or 1,
                        packet_stats['total_bytes'] or 0)
        
        except Exception as e:
            logger.error(f"Error aggregating visits for {employee_id}: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


async def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("TBAPS Traffic Monitor - Website Tracker Service")
    logger.info("=" * 80)
    
    # Create tracker instance
    tracker = WebsiteTracker(DATABASE_URL)
    
    # Start tracker
    await tracker.start()


if __name__ == '__main__':
    asyncio.run(main())
