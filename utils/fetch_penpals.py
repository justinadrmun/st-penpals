#!/usr/bin/env python3
"""
Reddit API Fetcher for r/penpals - Uses .env file for credentials
Fetches the most recent 1000 posts from r/penpals
"""

import os
import requests
import time
import csv
from datetime import datetime
from typing import List, Dict, Optional

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file or Streamlit secrets"""
    # First, try to load from Streamlit secrets (for deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and st.secrets:
            # Load from Streamlit secrets
            os.environ['CLIENT_ID'] = str(st.secrets.get('CLIENT_ID', ''))
            os.environ['CLIENT_SECRET'] = str(st.secrets.get('CLIENT_SECRET', ''))
            os.environ['REDDIT_USERNAME'] = str(st.secrets.get('REDDIT_USERNAME', 'unknown'))
            os.environ['APP_NAME'] = str(st.secrets.get('APP_NAME', 'reddit-parser'))
            return True
    except (ImportError, AttributeError):
        # Not running in Streamlit or no secrets available
        pass

    # Fallback: Load from .env file (for local development)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

    if not os.path.exists(env_path):
        return False

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

    return True

class RedditPenpalsFetcher:
    def __init__(self):
        """Initialize Reddit API client for penpals"""
        # Load credentials from environment
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.reddit_username = os.getenv('REDDIT_USERNAME', 'unknown')
        self.app_name = os.getenv('APP_NAME', 'penpals-insights')
        
        # Validate credentials
        if not self.client_id or not self.client_secret:
            raise ValueError("Error: CLIENT_ID and CLIENT_SECRET must be set in .env file")
        
        self.user_agent = f"script:{self.app_name}:v1.0 (by /u/{self.reddit_username})"
        self.access_token = None
        self.base_url = "https://oauth.reddit.com"
        self.rate_limit_delay = 0.6  # Delay between requestss
        
    def authenticate(self) -> bool:
        """Authenticate with Reddit OAuth2"""
        auth_url = "https://www.reddit.com/api/v1/access_token"
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        
        headers = {'User-Agent': self.user_agent}
        data = {'grant_type': 'client_credentials'}
        
        try:
            response = requests.post(auth_url, auth=auth, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            return True
            
        except requests.exceptions.RequestException as e:
            return False
    
    def fetch_penpals_posts(self, total_posts: int = 1000, subreddit: str = "penpals") -> List[Dict]:
        """
        Fetch recent posts from specified penpal subreddit
        
        Args:
            total_posts: Number of posts to fetch (default 1000)
            subreddit: Subreddit name (default "penpals")
        
        Returns:
            List of post dictionaries
        """
        if not self.access_token:
            return []
        
        sort = "new"  # Get most recent posts
        
        all_posts = []
        after = None  # Pagination cursor
        
        while len(all_posts) < total_posts:
            # Calculate batch size
            remaining = total_posts - len(all_posts)
            batch_size = min(remaining, 100)  # Reddit's max per request
            
            # Fetch batch
            batch_posts, next_after = self._fetch_batch(subreddit, sort, batch_size, after)
            
            if not batch_posts:
                break
            
            all_posts.extend(batch_posts)
            after = next_after

            # Rate limiting
            if len(all_posts) < total_posts and next_after:
                time.sleep(self.rate_limit_delay)
        
        final_posts = all_posts[:total_posts]
        return final_posts
    
    def _fetch_batch(self, subreddit: str, sort: str, limit: int, 
                     after: Optional[str]) -> tuple[List[Dict], Optional[str]]:
        """Fetch a single batch of posts"""
        url = f"{self.base_url}/r/{subreddit}/{sort}"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        
        params = {
            'limit': limit,
            'raw_json': 1
        }
        
        if after:
            params['after'] = after
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            posts = []
            next_after = None
            
            if 'data' in data:
                next_after = data['data'].get('after')
                
                if 'children' in data['data']:
                    for item in data['data']['children']:
                        if item['kind'] == 't3':  # Link/post
                            post_data = item['data']
                            
                            # Convert timestamp to readable format
                            created_time = datetime.fromtimestamp(
                                post_data.get('created_utc', 0)
                            ).strftime('%Y-%m-%d %H:%M:%S')
                            
                            post = {
                                'id': post_data.get('id', ''),
                                'title': post_data.get('title', ''),
                                'author': post_data.get('author', '[deleted]'),
                                'created_utc': post_data.get('created_utc', 0),
                                'created_time': created_time,
                                'score': post_data.get('score', 0),
                                'num_comments': post_data.get('num_comments', 0),
                                'url': post_data.get('url', ''),
                                'permalink': f"https://reddit.com{post_data.get('permalink', '')}",
                                'selftext': post_data.get('selftext', ''),
                                'is_self': post_data.get('is_self', False),
                                'over_18': post_data.get('over_18', False),
                                'spoiler': post_data.get('spoiler', False),
                                'locked': post_data.get('locked', False),
                                'stickied': post_data.get('stickied', False),
                                'upvote_ratio': post_data.get('upvote_ratio', 0),
                                'subreddit': post_data.get('subreddit', ''),
                                'flair_text': post_data.get('link_flair_text', ''),
                                'domain': post_data.get('domain', ''),
                            }
                            posts.append(post)
            
            return posts, next_after
            
        except requests.exceptions.RequestException as e:
            return [], None
    
    def save_to_csv(self, posts: List[Dict], filename: str):
        """Save posts to CSV file optimized for penpals analysis"""
        if not posts:
            return
        
        # Key fields for penpals analysis
        fieldnames = [
            'id', 'title', 'author', 'created_time', 'score', 'num_comments',
            'permalink', 'selftext', 'flair_text', 'over_18', 'locked'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for post in posts:
                # Only include relevant fields
                filtered_post = {k: post.get(k, '') for k in fieldnames}
                writer.writerow(filtered_post)

def main():
    """Main function to fetch 1000 recent posts from r/penpals or r/penpalsover30"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch posts from Reddit penpal communities")
    parser.add_argument('--subreddit', '-s', 
                       choices=['penpals', 'penpalsover30'], 
                       default='penpals',
                       help='Subreddit to fetch from (default: penpals)')
    parser.add_argument('--count', '-c', type=int, default=1000,
                       help='Number of posts to fetch (default: 1000)')
    
    args = parser.parse_args()
    
    # Load environment variables
    if not load_env():
        return
    
    try:
        # Initialize fetcher
        fetcher = RedditPenpalsFetcher()
        
        # Authenticate
        if not fetcher.authenticate():
            return
        
        # Fetch posts from specified subreddit
        posts = fetcher.fetch_penpals_posts(total_posts=args.count, subreddit=args.subreddit)
        
        if posts:
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save as CSV
            csv_filename = f"data/{args.subreddit}_recent_{args.count}_{timestamp}.csv"
            
            fetcher.save_to_csv(posts, csv_filename)
    
    except Exception as e:
        pass

if __name__ == "__main__":
    main()
