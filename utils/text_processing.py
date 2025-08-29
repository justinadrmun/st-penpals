"""
Text processing utilities.
Handles age extraction and keyword highlighting.
"""

import re
import pandas as pd
from datetime import datetime
from typing import List, Optional


def highlight_keywords_in_text(text: str, keywords: List[str]) -> str:
    """
    Highlight exact keyword matches in text using violet badges.
    
    Args:
        text: The text to highlight
        keywords: List of keywords to search for
    
    Returns:
        Text with highlighted keywords wrapped in :violet-badge[]
    """
    if not text or not keywords:
        return text
    
    import re
    
    highlighted_text = text
    words_to_highlight = set()
    
    # Add exact keyword matches (case-insensitive)
    for keyword in keywords:
        keyword = keyword.strip()
        if len(keyword) >= 2:  # Allow shorter keywords
            words_to_highlight.add(keyword.lower())
            
            # For multi-word keywords, also add individual words
            keyword_words = keyword.lower().split()
            for word in keyword_words:
                if len(word) >= 2:  # Allow shorter individual words
                    words_to_highlight.add(word)
    
    # Remove very common stop words but keep it minimal
    # Removed "the" to allow searching for it
    stop_words = {
        'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'a', 'an', 'this', 'that', 'it', 'he', 'she'
    }
    
    # Filter out only the most common stop words
    words_to_highlight = {word for word in words_to_highlight 
                         if word not in stop_words and len(word) >= 2}
    
    # Sort by length (longest first) to avoid partial matches
    sorted_words = sorted(words_to_highlight, key=len, reverse=True)
    
    for word in sorted_words:
        # Create case-insensitive regex pattern that handles word variations
        # For words 4+ characters, allow matching as prefix (e.g., "golf" matches "golfing")
        if len(word) >= 4:
            pattern = r'(?<!\w)' + re.escape(word) + r'(?:ing|ed|er|s|ly)?\b'
        else:
            # For shorter words, require exact match to avoid false positives
            pattern = r'(?<!\w)' + re.escape(word) + r'(?!\w)'
        
        # Use a function to preserve original case and create proper badge
        def replacement(match):
            original_word = match.group(0)
            return f":violet-badge[{original_word}]"
        
        highlighted_text = re.sub(pattern, replacement, highlighted_text, flags=re.IGNORECASE)
    
    return highlighted_text


def get_full_text(row) -> str:
    """Get combined title and body text"""
    title = str(row.get('title', '')) if pd.notna(row.get('title')) else ''
    # Handle both 'body' (from API) and 'selftext' (from CSV) 
    body = ''
    if pd.notna(row.get('body')):
        body = str(row.get('body', ''))
    elif pd.notna(row.get('selftext')):
        body = str(row.get('selftext', ''))
    
    return f"{title} {body}".strip()


def format_post_date(row) -> str:
    """Format the post date for display as relative time"""
    # Try created_time first (string format), then created_utc (timestamp)
    date_field = row.get('created_time') or row.get('created_utc')
    if pd.notna(date_field):
        try:
            if isinstance(date_field, str):
                # Parse string date (CSV format: "2025-08-24 22:32:22")
                from datetime import datetime
                date_obj = datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
            else:
                # Assume it's a timestamp (API format)
                from datetime import datetime
                date_obj = datetime.fromtimestamp(float(date_field))
            
            # Calculate relative time
            now = datetime.now()
            diff = now - date_obj
            
            # Calculate different time units
            seconds = int(diff.total_seconds())
            minutes = seconds // 60
            hours = minutes // 60
            days = diff.days
            weeks = days // 7
            months = days // 30
            years = days // 365
            
            # Return appropriate relative time string
            if seconds < 60:
                return "just now"
            elif minutes < 60:
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif hours < 24:
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif days < 7:
                return f"{days} day{'s' if days != 1 else ''} ago"
            elif weeks < 4:
                return f"{weeks} week{'s' if weeks != 1 else ''} ago"
            elif months < 12:
                return f"{months} month{'s' if months != 1 else ''} ago"
            else:
                return f"{years} year{'s' if years != 1 else ''} ago"
                
        except Exception as e:
            # Fallback to original string if parsing fails
            if isinstance(date_field, str) and len(str(date_field)) > 8:
                return str(date_field)[:10]  # Just return date part
            return f"Parse error: {str(e)[:30]}"
    return "Unknown date"
