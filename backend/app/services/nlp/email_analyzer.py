"""
Email Intelligence Analyzer
Analyzes email metadata for work signals while maintaining GDPR compliance.
NO email body content is stored or analyzed - subject lines only.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

# NLP libraries (local only)
try:
    from nltk.sentiment import SentimentIntensityAnalyzer
    import nltk
    # Download required NLTK data if not present
    try:
        nltk.data.find('vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logging.warning("VADER sentiment analyzer not available. Install nltk.")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available. Install spacy for advanced NLP.")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class EmailMetadata:
    """Email metadata structure (NO body content)"""
    email_id: str
    employee_id: str
    subject: str
    sent_at: datetime
    recipient_count: int
    replied_at: Optional[datetime] = None
    thread_id: Optional[str] = None
    is_reply: bool = False
    is_forwarded: bool = False


@dataclass
class SentimentScore:
    """Sentiment analysis results"""
    compound: float
    positive: float
    negative: float
    neutral: float
    label: str  # 'positive', 'negative', 'neutral'


@dataclass
class EmailSignals:
    """Extracted email signals"""
    email_id: str
    employee_id: str
    response_time_minutes: Optional[float]
    sentiment: SentimentScore
    is_urgent: bool
    urgency_score: float
    recipient_count: int
    subject_word_count: int
    communication_pattern: str
    extracted_at: datetime


# ============================================================================
# EMAIL ANALYZER
# ============================================================================

class EmailAnalyzer:
    """
    Email Intelligence Analyzer
    
    Analyzes email metadata to extract work signals:
    - Response time patterns
    - Sentiment analysis (subject line only)
    - Urgency detection
    - Communication patterns
    
    GDPR Compliant: NO email body content is analyzed or stored
    """
    
    # Urgency keywords
    URGENT_KEYWORDS = [
        'urgent', 'asap', 'emergency', 'critical', 'immediate',
        'now', 'deadline', 'priority', 'rush', 'important',
        'time-sensitive', 'action required', 'attention needed'
    ]
    
    # Communication pattern thresholds
    QUICK_RESPONSE_THRESHOLD = 30  # minutes
    SLOW_RESPONSE_THRESHOLD = 240  # minutes (4 hours)
    
    def __init__(self, db_connection=None):
        """
        Initialize Email Analyzer
        
        Args:
            db_connection: Database connection for storing signals
        """
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
        
        # Initialize sentiment analyzer
        if VADER_AVAILABLE:
            self.sia = SentimentIntensityAnalyzer()
        else:
            self.sia = None
            self.logger.warning("VADER not available. Sentiment analysis disabled.")
        
        # Initialize spaCy (optional)
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.nlp = None
                self.logger.warning("spaCy model not found. Advanced NLP disabled.")
        else:
            self.nlp = None
    
    # ========================================================================
    # MAIN ANALYSIS
    # ========================================================================
    
    def analyze_email_metadata(self, email_data: Dict[str, Any]) -> EmailSignals:
        """
        Analyze email metadata and extract signals
        
        Args:
            email_data: Dictionary containing email metadata
                - email_id: Unique email identifier
                - employee_id: Employee identifier
                - subject: Subject line (NO body content)
                - sent_at: Send timestamp
                - recipient_count: Number of recipients
                - replied_at: Reply timestamp (optional)
                - thread_id: Email thread ID (optional)
                - is_reply: Whether this is a reply
                - is_forwarded: Whether this is forwarded
        
        Returns:
            EmailSignals object with extracted signals
        """
        # Convert dict to EmailMetadata
        metadata = EmailMetadata(
            email_id=email_data['email_id'],
            employee_id=email_data['employee_id'],
            subject=email_data.get('subject', ''),
            sent_at=email_data['sent_at'],
            recipient_count=email_data.get('recipient_count', 1),
            replied_at=email_data.get('replied_at'),
            thread_id=email_data.get('thread_id'),
            is_reply=email_data.get('is_reply', False),
            is_forwarded=email_data.get('is_forwarded', False)
        )
        
        # Extract signals
        response_time = self.extract_response_time(metadata)
        sentiment = self.analyze_sentiment(metadata.subject)
        is_urgent, urgency_score = self.detect_urgency(metadata.subject)
        word_count = self.count_words(metadata.subject)
        pattern = self.determine_communication_pattern(
            response_time, 
            metadata.recipient_count,
            is_urgent
        )
        
        return EmailSignals(
            email_id=metadata.email_id,
            employee_id=metadata.employee_id,
            response_time_minutes=response_time,
            sentiment=sentiment,
            is_urgent=is_urgent,
            urgency_score=urgency_score,
            recipient_count=metadata.recipient_count,
            subject_word_count=word_count,
            communication_pattern=pattern,
            extracted_at=datetime.utcnow()
        )
    
    # ========================================================================
    # SENTIMENT ANALYSIS
    # ========================================================================
    
    def analyze_sentiment(self, subject_line: str) -> SentimentScore:
        """
        Analyze sentiment from subject line only
        
        Uses VADER (Valence Aware Dictionary and sEntiment Reasoner)
        - Optimized for social media text and short messages
        - Works well with subject lines
        
        Args:
            subject_line: Email subject line
        
        Returns:
            SentimentScore with compound score and label
        """
        if not subject_line or not self.sia:
            return SentimentScore(
                compound=0.0,
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                label='neutral'
            )
        
        # Get VADER scores
        scores = self.sia.polarity_scores(subject_line)
        
        # Determine label based on compound score
        if scores['compound'] > 0.1:
            label = 'positive'
        elif scores['compound'] < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return SentimentScore(
            compound=scores['compound'],
            positive=scores['pos'],
            negative=scores['neg'],
            neutral=scores['neu'],
            label=label
        )
    
    # ========================================================================
    # URGENCY DETECTION
    # ========================================================================
    
    def detect_urgency(self, subject_line: str) -> tuple[bool, float]:
        """
        Detect urgency markers in subject line
        
        Checks for:
        - Urgent keywords
        - Excessive capitalization
        - Multiple exclamation marks
        - Deadline mentions
        
        Args:
            subject_line: Email subject line
        
        Returns:
            Tuple of (is_urgent: bool, urgency_score: float)
        """
        if not subject_line:
            return False, 0.0
        
        urgency_score = 0.0
        
        subject_lower = subject_line.lower()
        
        # Check for urgent keywords (40 points each)
        keyword_matches = sum(
            1 for keyword in self.URGENT_KEYWORDS 
            if keyword in subject_lower
        )
        urgency_score += keyword_matches * 0.4
        
        # Check for excessive capitalization (30 points)
        if len(subject_line) > 0:
            caps_ratio = sum(1 for c in subject_line if c.isupper()) / len(subject_line)
            if caps_ratio > 0.3:  # More than 30% caps
                urgency_score += 0.3
        
        # Check for multiple exclamation marks (20 points)
        exclaim_count = subject_line.count('!')
        if exclaim_count > 1:
            urgency_score += 0.2
        elif exclaim_count == 1:
            urgency_score += 0.1
        
        # Check for deadline patterns (30 points)
        deadline_patterns = [
            r'by\s+\d+',  # "by 5pm"
            r'due\s+\w+',  # "due tomorrow"
            r'eod',  # "end of day"
            r'asap',
            r'today',
            r'tonight'
        ]
        
        for pattern in deadline_patterns:
            if re.search(pattern, subject_lower):
                urgency_score += 0.3
                break
        
        # Cap at 1.0
        urgency_score = min(urgency_score, 1.0)
        
        # Consider urgent if score > 0.5
        is_urgent = urgency_score > 0.5
        
        return is_urgent, urgency_score
    
    # ========================================================================
    # RESPONSE TIME
    # ========================================================================
    
    def extract_response_time(self, metadata: EmailMetadata) -> Optional[float]:
        """
        Calculate response time in minutes
        
        Args:
            metadata: EmailMetadata object
        
        Returns:
            Response time in minutes, or None if not a reply
        """
        if not metadata.replied_at or not metadata.sent_at:
            return None
        
        time_diff = metadata.replied_at - metadata.sent_at
        
        # Convert to minutes
        response_minutes = time_diff.total_seconds() / 60
        
        # Sanity check: negative response time means data error
        if response_minutes < 0:
            self.logger.warning(
                f"Negative response time for email {metadata.email_id}: "
                f"{response_minutes} minutes"
            )
            return None
        
        return response_minutes
    
    # ========================================================================
    # COMMUNICATION PATTERNS
    # ========================================================================
    
    def determine_communication_pattern(
        self,
        response_time: Optional[float],
        recipient_count: int,
        is_urgent: bool
    ) -> str:
        """
        Determine communication pattern based on signals
        
        Patterns:
        - quick_responder: Fast responses (<30 min)
        - slow_responder: Slow responses (>4 hours)
        - broadcaster: Many recipients (>5)
        - urgent_communicator: Frequent urgent messages
        - normal: Standard communication
        
        Args:
            response_time: Response time in minutes
            recipient_count: Number of recipients
            is_urgent: Whether message is urgent
        
        Returns:
            Communication pattern label
        """
        patterns = []
        
        if response_time is not None:
            if response_time < self.QUICK_RESPONSE_THRESHOLD:
                patterns.append('quick_responder')
            elif response_time > self.SLOW_RESPONSE_THRESHOLD:
                patterns.append('slow_responder')
        
        if recipient_count > 5:
            patterns.append('broadcaster')
        
        if is_urgent:
            patterns.append('urgent_communicator')
        
        if not patterns:
            return 'normal'
        
        # Return primary pattern (first one)
        return patterns[0]
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def count_words(self, subject_line: str) -> int:
        """
        Count words in subject line
        
        Args:
            subject_line: Email subject line
        
        Returns:
            Word count
        """
        if not subject_line:
            return 0
        
        # Remove special characters and split
        words = re.findall(r'\b\w+\b', subject_line)
        return len(words)
    
    def extract_entities(self, subject_line: str) -> List[str]:
        """
        Extract named entities from subject line (if spaCy available)
        
        Args:
            subject_line: Email subject line
        
        Returns:
            List of entity labels
        """
        if not self.nlp or not subject_line:
            return []
        
        doc = self.nlp(subject_line)
        return [ent.label_ for ent in doc.ents]
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    def analyze_batch(
        self,
        email_batch: List[Dict[str, Any]]
    ) -> List[EmailSignals]:
        """
        Analyze multiple emails in batch
        
        Args:
            email_batch: List of email metadata dictionaries
        
        Returns:
            List of EmailSignals
        """
        signals = []
        
        for email_data in email_batch:
            try:
                signal = self.analyze_email_metadata(email_data)
                signals.append(signal)
            except Exception as e:
                self.logger.error(
                    f"Error analyzing email {email_data.get('email_id')}: {e}"
                )
        
        return signals
    
    # ========================================================================
    # DATABASE INTEGRATION
    # ========================================================================
    
    async def store_signals(self, signals: EmailSignals) -> bool:
        """
        Store extracted signals in database
        
        Args:
            signals: EmailSignals object
        
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            self.logger.warning("No database connection available")
            return False
        
        try:
            query = """
                INSERT INTO email_signals (
                    email_id,
                    employee_id,
                    response_time_minutes,
                    sentiment_compound,
                    sentiment_label,
                    is_urgent,
                    urgency_score,
                    recipient_count,
                    subject_word_count,
                    communication_pattern,
                    extracted_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (email_id) DO UPDATE SET
                    response_time_minutes = EXCLUDED.response_time_minutes,
                    sentiment_compound = EXCLUDED.sentiment_compound,
                    sentiment_label = EXCLUDED.sentiment_label,
                    is_urgent = EXCLUDED.is_urgent,
                    urgency_score = EXCLUDED.urgency_score,
                    recipient_count = EXCLUDED.recipient_count,
                    subject_word_count = EXCLUDED.subject_word_count,
                    communication_pattern = EXCLUDED.communication_pattern,
                    extracted_at = EXCLUDED.extracted_at
            """
            
            await self.db.execute(
                query,
                signals.email_id,
                signals.employee_id,
                signals.response_time_minutes,
                signals.sentiment.compound,
                signals.sentiment.label,
                signals.is_urgent,
                signals.urgency_score,
                signals.recipient_count,
                signals.subject_word_count,
                signals.communication_pattern,
                signals.extracted_at
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing email signals: {e}")
            return False
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    async def get_employee_email_stats(
        self,
        employee_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get email statistics for employee
        
        Args:
            employee_id: Employee identifier
            days: Number of days to analyze
        
        Returns:
            Dictionary with email statistics
        """
        if not self.db:
            return {}
        
        try:
            query = """
                SELECT
                    COUNT(*) as total_emails,
                    AVG(response_time_minutes) as avg_response_time,
                    AVG(sentiment_compound) as avg_sentiment,
                    SUM(CASE WHEN is_urgent THEN 1 ELSE 0 END) as urgent_count,
                    AVG(recipient_count) as avg_recipients,
                    AVG(subject_word_count) as avg_subject_length,
                    MODE() WITHIN GROUP (ORDER BY communication_pattern) as primary_pattern
                FROM email_signals
                WHERE employee_id = $1
                    AND extracted_at > NOW() - INTERVAL '$2 days'
            """
            
            result = await self.db.fetchrow(query, employee_id, days)
            
            return dict(result) if result else {}
            
        except Exception as e:
            self.logger.error(f"Error getting email stats: {e}")
            return {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_business_hours(timestamp: datetime) -> bool:
    """Check if timestamp is during business hours (9 AM - 5 PM weekdays)"""
    return (
        timestamp.weekday() < 5 and  # Monday-Friday
        9 <= timestamp.hour < 17  # 9 AM - 5 PM
    )


def calculate_response_time_score(response_minutes: float) -> float:
    """
    Calculate response time score (0-100)
    
    - < 30 min: 100
    - 30-60 min: 90
    - 1-2 hours: 80
    - 2-4 hours: 70
    - 4-8 hours: 60
    - > 8 hours: 50
    """
    if response_minutes < 30:
        return 100.0
    elif response_minutes < 60:
        return 90.0
    elif response_minutes < 120:
        return 80.0
    elif response_minutes < 240:
        return 70.0
    elif response_minutes < 480:
        return 60.0
    else:
        return 50.0
