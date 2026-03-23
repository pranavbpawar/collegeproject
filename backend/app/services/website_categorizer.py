"""
TBAPS Traffic Monitor - Website Categorizer

Classifies websites into productivity categories
Provides productivity scoring for behavioral analysis
"""

import asyncio
import asyncpg
import logging
import os
import re
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ztuser:ztpass@localhost:5432/zerotrust')


class WebsiteCategor

izer:
    """
    Website Categorization Engine
    
    Classifies domains into productivity categories
    Supports pattern matching and custom rules
    """
    
    def __init__(self, database_url: str):
        """Initialize categorizer"""
        self.database_url = database_url
        self.db_pool = None
        self.category_cache = {}
    
    async def connect(self):
        """Connect to database"""
        self.db_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=5
        )
        await self._load_categories()
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.db_pool:
            await self.db_pool.close()
    
    async def _load_categories(self):
        """Load category patterns from database"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT domain_pattern, category, productivity_score
                FROM website_categories
                ORDER BY LENGTH(domain_pattern) DESC
            ''')
            
            self.category_cache = {
                row['domain_pattern']: {
                    'category': row['category'],
                    'score': row['productivity_score']
                }
                for row in rows
            }
            
            logger.info(f"Loaded {len(self.category_cache)} category patterns")
    
    def categorize(self, domain: str) -> Tuple[str, int]:
        """
        Categorize a domain
        
        Args:
            domain: Domain name to categorize
        
        Returns:
            Tuple of (category, productivity_score)
        """
        # Normalize domain
        domain = domain.lower().strip()
        
        # Check exact match first
        if domain in self.category_cache:
            cat = self.category_cache[domain]
            return (cat['category'], cat['score'])
        
        # Check pattern matches
        for pattern, cat in self.category_cache.items():
            if self._match_pattern(domain, pattern):
                return (cat['category'], cat['score'])
        
        # Default: unknown category
        return ('unknown', 50)
    
    def _match_pattern(self, domain: str, pattern: str) -> bool:
        """
        Match domain against pattern
        
        Supports wildcards:
        - %.example.com matches any.example.com
        - example.% matches example.com, example.org, etc.
        """
        # Convert SQL LIKE pattern to regex
        regex_pattern = pattern.replace('.', r'\.')
        regex_pattern = regex_pattern.replace('%', '.*')
        regex_pattern = f'^{regex_pattern}$'
        
        return bool(re.match(regex_pattern, domain))
    
    async def add_category(self, domain_pattern: str, category: str, 
                          productivity_score: int, description: str = None):
        """Add new category pattern"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO website_categories (
                    domain_pattern, category, productivity_score, description
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (domain_pattern) DO UPDATE
                SET category = $2, productivity_score = $3, description = $4
            ''', domain_pattern, category, productivity_score, description)
        
        # Reload cache
        await self._load_categories()
        logger.info(f"Added category: {domain_pattern} -> {category} ({productivity_score})")


async def main():
    """Test categorizer"""
    categorizer = WebsiteCategorizer(DATABASE_URL)
    await categorizer.connect()
    
    # Test domains
    test_domains = [
        'github.com',
        'api.github.com',
        'stackoverflow.com',
        'facebook.com',
        'youtube.com',
        'docs.google.com',
        'unknown-site.com'
    ]
    
    print("\n" + "=" * 60)
    print("Website Categorization Test")
    print("=" * 60)
    
    for domain in test_domains:
        category, score = categorizer.categorize(domain)
        print(f"{domain:30} -> {category:20} (score: {score})")
    
    await categorizer.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
