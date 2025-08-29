"""
Data loading functionality for Reddit posts.
Handles API fetching.
"""

import pandas as pd
import os
from datetime import datetime
import streamlit as st

from .fetch_penpals import RedditPenpalsFetcher, load_env

def filter_deleted_and_deduplicate_users(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only the most recent post per user, but preserve all [deleted] posts
    since they represent different users who have deleted their profiles.
    
    Args:
        df: DataFrame with Reddit posts
        
    Returns:
        Filtered DataFrame with one post per identifiable user, all [deleted] posts preserved
    """
    if df.empty:
        return df
    
    # Sort by created_time (or created_utc if created_time not available)
    if 'created_time' in df.columns:
        df_sorted = df.sort_values('created_time', ascending=False)
    elif 'created_utc' in df.columns:
        df_sorted = df.sort_values('created_utc', ascending=False)
    else:
        df_sorted = df.copy()
    
    # Separate [deleted] users from identifiable users
    mask_deleted = df_sorted['author'] == '[deleted]'
    
    # For identifiable users, deduplicate normally (keep most recent post per user)
    df_identifiable = df_sorted[~mask_deleted]
    df_deduplicated_identifiable = df_identifiable.drop_duplicates(subset=['author'], keep='first')
    
    # For [deleted] users, keep all posts (they are different people)
    df_deleted_users = df_sorted[mask_deleted]
    
    # Combine the results
    df_final = pd.concat([df_deduplicated_identifiable, df_deleted_users], ignore_index=True)
    
    # Re-sort the final result
    if 'created_time' in df_final.columns:
        df_final = df_final.sort_values('created_time', ascending=False)
    elif 'created_utc' in df_final.columns:
        df_final = df_final.sort_values('created_utc', ascending=False)
    
    return df_final


@st.cache_data(ttl=1200, show_spinner=False)  # Cache API calls for 20 minutes
def fetch_reddit_data(subreddit: str) -> pd.DataFrame:
    """
    Fetch Reddit data -  API
    """
    return _fetch_from_api(subreddit)

def _fetch_from_api(subreddit: str) -> pd.DataFrame:
    """Fetch data from Reddit API"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        original_cwd = os.getcwd()
        os.chdir(script_dir)
        
        load_env()
        fetcher = RedditPenpalsFetcher()
        
        if not fetcher.authenticate():
            raise Exception("Failed to authenticate with Reddit API")
        
        posts = fetcher.fetch_penpals_posts(total_posts=1000, subreddit=subreddit)
        
        if not posts:
            raise Exception("No posts fetched")
        
        # Convert to DataFrame
        df = pd.DataFrame(posts)
        
        # Standardize column names to match CSV format
        if 'selftext' in df.columns and 'body' not in df.columns:
            df['body'] = df['selftext']
        
        # Ensure both created_utc and created_time are available
        if 'created_utc' in df.columns and 'created_time' not in df.columns:
            # Convert created_utc timestamp to created_time string format
            df['created_time'] = pd.to_datetime(df['created_utc'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        df['fetch_time'] = datetime.now()
        df['subreddit'] = subreddit
        df['source'] = 'reddit_api'
        
        # Ensure we have the expected columns
        expected_cols = ['title', 'body', 'age', 'author', 'created_utc', 'created_time', 'score', 'num_comments']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # Filter deleted posts and deduplicate users
        df = filter_deleted_and_deduplicate_users(df)
        
        os.chdir(original_cwd)
        return df
        
    except Exception as e:
        try:
            os.chdir(original_cwd)
        except:
            pass
        raise e
