"""
Gmail Integration for Email Intelligence
Fetches email metadata from Gmail API and analyzes with EmailAnalyzer
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.nlp.email_analyzer import EmailAnalyzer, EmailSignals
from app.core.encryption import decrypt_token


logger = logging.getLogger(__name__)


class GmailEmailIntelligence:
    """
    Gmail Email Intelligence Service
    
    Fetches email metadata from Gmail and extracts work signals.
    GDPR Compliant: Only fetches subject lines, timestamps, and recipient counts.
    NO email body content is fetched or stored.
    """
    
    def __init__(self, db_connection):
        """
        Initialize Gmail Email Intelligence
        
        Args:
            db_connection: Database connection
        """
        self.db = db_connection
        self.analyzer = EmailAnalyzer(db_connection)
        self.logger = logging.getLogger(__name__)
    
    async def sync_employee_emails(
        self,
        employee_id: str,
        days: int = 7,
        max_results: int = 100
    ) -> List[EmailSignals]:
        """
        Sync and analyze employee emails from Gmail
        
        Args:
            employee_id: Employee identifier
            days: Number of days to fetch (default: 7)
            max_results: Maximum number of emails to fetch
        
        Returns:
            List of EmailSignals
        """
        try:
            # Get OAuth credentials from database
            credentials = await self._get_employee_credentials(employee_id)
            
            if not credentials:
                self.logger.warning(f"No Gmail credentials for employee {employee_id}")
                return []
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Fetch email metadata
            email_metadata_list = await self._fetch_email_metadata(
                service,
                employee_id,
                days,
                max_results
            )
            
            # Analyze emails
            signals_list = []
            for email_metadata in email_metadata_list:
                try:
                    signals = self.analyzer.analyze_email_metadata(email_metadata)
                    
                    # Store signals in database
                    await self.analyzer.store_signals(signals)
                    
                    signals_list.append(signals)
                    
                except Exception as e:
                    self.logger.error(
                        f"Error analyzing email {email_metadata.get('email_id')}: {e}"
                    )
            
            self.logger.info(
                f"Synced and analyzed {len(signals_list)} emails for employee {employee_id}"
            )
            
            return signals_list
            
        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error syncing emails: {e}")
            return []
    
    async def _fetch_email_metadata(
        self,
        service,
        employee_id: str,
        days: int,
        max_results: int
    ) -> List[Dict]:
        """
        Fetch email metadata from Gmail
        
        GDPR Compliant: Only fetches subject, timestamp, and recipient count
        NO email body content is fetched
        
        Args:
            service: Gmail API service
            employee_id: Employee identifier
            days: Number of days to fetch
            max_results: Maximum results
        
        Returns:
            List of email metadata dictionaries
        """
        # Calculate date range
        after_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y/%m/%d')
        
        # Query for sent emails only (to track response times)
        query = f'in:sent after:{after_date}'
        
        try:
            # List messages
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            email_metadata_list = []
            
            for message in messages:
                # Get message details (metadata only)
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata',  # METADATA ONLY - no body
                    metadataHeaders=['Subject', 'To', 'Date', 'In-Reply-To']
                ).execute()
                
                # Extract metadata
                headers = {h['name']: h['value'] for h in msg['payload']['headers']}
                
                # Parse metadata
                email_metadata = {
                    'email_id': message['id'],
                    'employee_id': employee_id,
                    'subject': headers.get('Subject', ''),
                    'sent_at': self._parse_date(headers.get('Date', '')),
                    'recipient_count': len(headers.get('To', '').split(',')),
                    'thread_id': msg.get('threadId'),
                    'is_reply': 'In-Reply-To' in headers,
                    'is_forwarded': headers.get('Subject', '').startswith('Fwd:')
                }
                
                # Try to get reply time if this is a reply
                if email_metadata['is_reply']:
                    reply_time = await self._get_reply_time(
                        service,
                        msg.get('threadId')
                    )
                    email_metadata['replied_at'] = reply_time
                
                email_metadata_list.append(email_metadata)
            
            return email_metadata_list
            
        except HttpError as e:
            self.logger.error(f"Error fetching email metadata: {e}")
            return []
    
    async def _get_reply_time(
        self,
        service,
        thread_id: str
    ) -> Optional[datetime]:
        """
        Get reply time from email thread
        
        Args:
            service: Gmail API service
            thread_id: Thread identifier
        
        Returns:
            Reply timestamp or None
        """
        try:
            # Get thread
            thread = service.users().threads().get(
                userId='me',
                id=thread_id,
                format='metadata'
            ).execute()
            
            messages = thread.get('messages', [])
            
            if len(messages) < 2:
                return None
            
            # Get first message date (original)
            first_msg = messages[0]
            first_headers = {h['name']: h['value'] for h in first_msg['payload']['headers']}
            original_date = self._parse_date(first_headers.get('Date', ''))
            
            # Get second message date (reply)
            second_msg = messages[1]
            second_headers = {h['name']: h['value'] for h in second_msg['payload']['headers']}
            reply_date = self._parse_date(second_headers.get('Date', ''))
            
            return reply_date
            
        except Exception as e:
            self.logger.error(f"Error getting reply time: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse email date string to datetime
        
        Args:
            date_str: Date string from email header
        
        Returns:
            Datetime object
        """
        from email.utils import parsedate_to_datetime
        
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.utcnow()
    
    async def _get_employee_credentials(self, employee_id: str) -> Optional[Credentials]:
        """
        Get decrypted OAuth credentials for employee
        
        Args:
            employee_id: Employee identifier
        
        Returns:
            Google OAuth credentials or None
        """
        try:
            # Fetch encrypted token from database
            query = """
                SELECT access_token, refresh_token, token_expiry
                FROM oauth_tokens
                WHERE employee_id = $1 AND provider = 'google'
            """
            
            result = await self.db.fetchrow(query, employee_id)
            
            if not result:
                return None
            
            # Decrypt tokens
            access_token = decrypt_token(result['access_token'])
            refresh_token = decrypt_token(result['refresh_token'])
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=None,  # Set from config
                client_secret=None  # Set from config
            )
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Error getting credentials: {e}")
            return None


# ============================================================================
# BACKGROUND TASK
# ============================================================================

async def sync_all_employee_emails(db_connection, days: int = 7):
    """
    Background task to sync emails for all employees
    
    Args:
        db_connection: Database connection
        days: Number of days to sync
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get all employees with Gmail integration
        query = """
            SELECT DISTINCT employee_id
            FROM oauth_tokens
            WHERE provider = 'google'
                AND is_active = TRUE
        """
        
        results = await db_connection.fetch(query)
        
        gmail_service = GmailEmailIntelligence(db_connection)
        
        for row in results:
            employee_id = row['employee_id']
            
            try:
                await gmail_service.sync_employee_emails(
                    employee_id,
                    days=days,
                    max_results=100
                )
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error syncing emails for {employee_id}: {e}")
        
        logger.info(f"Completed email sync for {len(results)} employees")
        
    except Exception as e:
        logger.error(f"Error in email sync task: {e}")
