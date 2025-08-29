#!/usr/bin/env python3
"""
Reddit Penpal Parser - Simple Keyword Filtering Streamlit App
"""

import streamlit as st
import pandas as pd
import os

from utils.data_loader import fetch_reddit_data
from utils.text_processing import format_post_date, highlight_keywords_in_text, get_full_text
from datetime import datetime

def get_badge_color_for_date(row) -> str:
    """Determine badge color based on post age"""
    # Try created_time first (string format), then created_utc (timestamp)
    date_field = row.get('created_time') or row.get('created_utc')
    if pd.notna(date_field):
        try:
            if isinstance(date_field, str):
                # Parse string date (CSV format: "2025-08-24 22:32:22")
                date_obj = datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
            else:
                # Assume it's a timestamp (API format)
                date_obj = datetime.fromtimestamp(float(date_field))
            
            # Calculate days difference
            now = datetime.now()
            diff = now - date_obj
            days = diff.days
            
            # Return appropriate color
            if days <= 1:  # Today and yesterday
                return "green"
            elif days <= 30:  # 2 days to 1 month
                return "orange"  # Using orange instead of yellow as it's more visible
            else:  # Beyond 1 month
                return "red"
                
        except Exception:
            # Fallback to green if parsing fails
            return "green"
    
    return "green"  # Default fallback

if 'fetched_data_penpals' not in st.session_state:
    st.session_state.fetched_data_penpals = None
if 'fetched_data_penpalsover30' not in st.session_state:
    st.session_state.fetched_data_penpalsover30 = None
if 'current_keywords' not in st.session_state:
    st.session_state.current_keywords = []
if 'current_subreddit' not in st.session_state:
    st.session_state.current_subreddit = None
if 'selected_subreddit' not in st.session_state:
    st.session_state.selected_subreddit = "penpals"
if 'fetch_requested' not in st.session_state:
    st.session_state.fetch_requested = False
if 'fetch_success' not in st.session_state:
    st.session_state.fetch_success = None
if 'fetch_warning' not in st.session_state:
    st.session_state.fetch_warning = None
if 'fetch_error' not in st.session_state:
    st.session_state.fetch_error = None
if 'fetch_start_time' not in st.session_state:
    st.session_state.fetch_start_time = None
if 'penpals_page' not in st.session_state:
    st.session_state.penpals_page = 0
if 'penpalsover30_page' not in st.session_state:
    st.session_state.penpalsover30_page = 0
if 'ui_enabled' not in st.session_state:
    st.session_state.ui_enabled = False  # Start with UI disabled during initial load

# Main UI starts here

# Page configuration
st.set_page_config(
    page_title="Search and filter r/penpals", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# # Environment check
# script_dir = os.path.dirname(os.path.abspath(__file__))
# env_path = os.path.join(script_dir, ".env")
# if not os.path.exists(env_path):
#     st.error("Error: Missing .env file with Reddit API credentials")
#     st.stop()

# Set default subreddit if none selected
if 'selected_subreddit' not in st.session_state:
    st.session_state.selected_subreddit = "penpals"

# Enable UI if data already exists (for subsequent app runs)
if st.session_state.get('has_fetched_data', False) and not st.session_state.get('ui_enabled', False):
    st.session_state.ui_enabled = True

# Create input interface
def create_input_interface():
    """Create the main input interface in the sidebar"""
    # Determine if UI should be enabled (data loaded or not currently fetching)
    ui_disabled = not st.session_state.get('ui_enabled', False)
    
    with st.sidebar:
        
        # Show loading status if data is being fetched
        if st.session_state.get('fetch_requested', False):
            st.info("🔄 Loading data... Please wait.")
        
        # Simple keyword input
        keywords_text = st.text_input(
            "Enter keywords (comma-separated):", 
            "", 
            disabled=ui_disabled
        )
        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
        
        with st.expander("Filters", expanded=True):
            # Age range slider for title filtering
            age_range = st.slider(
                "Age range (title only):", 
                min_value=18, 
                max_value=99, 
                value=(18, 99), 
                step=1, 
                key="age_range",
                disabled=ui_disabled
            )
            min_age, max_age = age_range
            
            # Generate age keywords if range is not default
            age_keywords = []
            if min_age != 18 or max_age != 99:
                age_keywords = [str(age) for age in range(min_age, max_age + 1)]
            
            # Post recency filter
            recency_options = ["Today", "Last week", "Last month", "No filter"]
            recency_filter = st.select_slider(
                "Filter by date posted:",
                options=recency_options,
                value="No filter",  # Default to show all posts
                key="recency_slider",
                disabled=ui_disabled
            )

            # Sort order selection with key
            sort_options = ["Date Posted", "Title Alphabetically"]
            default_index = 0  # Default to Date Posted
            
            sort_option = st.radio(
                "Sort by:",
                options=sort_options,
                index=default_index,
                key="sort_option",
                disabled=ui_disabled
            )

        # Auto-fetch logic: trigger fetch when first loading
        if not st.session_state.get('has_fetched_data', False) and not st.session_state.get('fetch_requested', False):
            # Clear previous messages
            st.session_state.fetch_warning = None
            st.session_state.fetch_error = None
            st.session_state.fetch_success = None
            # Store fetch parameters
            st.session_state.fetch_requested = True
            st.session_state.fetch_keywords = keywords  # Can be empty for initial load
            st.session_state.fetch_sort_option = sort_option
            st.session_state.fetch_start_time = None  # Will be set when fetch starts

        # Help button at the bottom of sidebar
        if st.button("More info",  
                     disabled=ui_disabled, 
                     type="primary"):
            show_help_dialog()

    return keywords, age_keywords, sort_option, recency_filter

@st.dialog("App Info", width="medium")
def show_help_dialog():
    """Display a comprehensive help dialog explaining how to use the app"""
    
    st.markdown("""
    This app helps you search and filter posts from **r/penpals** and **r/penpalsover30**. Expand the sections below to learn more about each filter.

    """
    )
    with st.expander("**Keywords Search**", expanded=False):
        st.markdown(
            """
            - Enter keywords separated by commas (e.g., "travel, books, music")
            - The app searches both post titles and content. Keywords are highlighted using :violet-badge[violet tags].
            - Keywords are case-insensitive and support partial matching
            - Example: "music" will match "musician", "musical", etc.
            """
        )
    
    with st.expander("**Age Range Filter**", expanded=False):
        st.markdown("""
        - Use the slider to filter posts by age mentioned in titles
        - Only searches in post titles (not content)
        - Useful for finding age-specific penpals
        - Example: Setting 25-35 will show posts mentioning ages 25, 26, 27... 35
        """
    )

    with st.expander("**Post Date Filter**", expanded=False):
        st.markdown("""
        - **Today**: Posts from the last 24 hours
        - **Last week**: Posts from the last 7 days  
        - **Last month**: Posts from the last 30 days
        - **No filter**: All posts regardless of post age
        """
    )   
        
    with st.expander("**Sorting Options**", expanded=False):
        st.markdown("""
        - **Date Posted**: Shows newest posts first (recommended)
        - **Title Alphabetically**: Sorts posts A-Z by title. This can be used as a proxy for sorting by Age, but not perfect as this is a free-text field.
        """
    )   


    st.markdown("""
    ### **Data details**
    - Data is sourced from the Reddit API. Limited historical data is available (1000 posts).
    - Duplicate posts from the same user have been removed. Only the most recent post is kept.
    - Data is cached for 20 minutes, then it will refresh automatically.
    - If a previous user was using the app within the last 20 minutes, you may benefit from their cached data, resulting in faster load times.
    """)

def handle_fetch_data(keywords):
    """Handle the data fetching for both subreddits"""
    from datetime import datetime, timedelta

    # Set fetch start time if not already set
    if st.session_state.fetch_start_time is None:
        st.session_state.fetch_start_time = datetime.now()

    # Check for timeout (3 minutes)
    if datetime.now() - st.session_state.fetch_start_time > timedelta(minutes=3):
        st.session_state.fetch_error = "Fetch timed out after 3 minutes. Please try again."
        st.session_state.fetch_requested = False
        st.session_state.fetch_start_time = None
        return

    try:
        df_penpals = fetch_reddit_data("penpals")
        st.toast("✅\u2002 **r/penpals** data fetching complete!")
        df_penpalsover30 = fetch_reddit_data("penpalsover30")
        st.toast("✅\u2002 **r/penpalsover30** data fetching complete!")

        # Add subreddit identifier to each dataframe
        if not df_penpals.empty:
            df_penpals = df_penpals.copy()
            df_penpals['subreddit'] = 'penpals'
        if not df_penpalsover30.empty:
            df_penpalsover30 = df_penpalsover30.copy()
            df_penpalsover30['subreddit'] = 'penpalsover30'

        # Store results in session state
        st.session_state.fetched_data_penpals = df_penpals
        st.session_state.fetched_data_penpalsover30 = df_penpalsover30
        st.session_state.current_keywords = keywords
        st.session_state.has_fetched_data = True  # Mark that data has been fetched

        # Clear fetch request and set success
        st.session_state.fetch_requested = False
        st.session_state.fetch_success = True
        st.session_state.fetch_error = None
        st.session_state.fetch_warning = None
        st.session_state.fetch_start_time = None  # Clear timeout timer
        st.session_state.ui_enabled = True  # Enable UI now that data is loaded
        st.rerun()

    except Exception as e:
        # Store error message in session state
        st.session_state.fetch_error = f"Error: {e}"
        st.session_state.fetch_requested = False
        st.session_state.fetch_success = False
        st.session_state.fetch_warning = None
        st.session_state.fetch_start_time = None  # Clear timeout timer
        st.session_state.ui_enabled = True  # Enable UI even on error so user can retry
        st.rerun()
                
def filter_posts_by_recency(df, recency_filter):
    """Filter posts based on the selected time period"""
    if df.empty:
        return df
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    filtered_df = df.copy()
    
    def get_post_datetime(row):
        """Extract datetime from a row, handling both string and timestamp formats"""
        date_field = row.get('created_time') or row.get('created_utc')
        if pd.notna(date_field):
            try:
                if isinstance(date_field, str):
                    # Parse string date (CSV format: "2025-08-24 22:32:22")
                    return datetime.strptime(date_field, '%Y-%m-%d %H:%M:%S')
                else:
                    # Assume it's a timestamp (API format)
                    return datetime.fromtimestamp(float(date_field))
            except Exception:
                return None
        return None
    
    # Apply the time filter
    def is_within_timeframe(row):
        post_date = get_post_datetime(row)
        if post_date is None:
            return True  # Include posts with invalid dates by default
        
        diff = now - post_date
        
        if recency_filter == "Today":
            return diff.days == 0
        elif recency_filter == "Last week":
            return diff.days <= 7
        elif recency_filter == "Last month":
            return diff.days <= 30
        elif recency_filter == "All time":
            return True  # Include all posts regardless of age
        elif recency_filter == "More than a month":  # Legacy support
            return True  # Include all posts regardless of age
        else:
            return True  # Default to include all
    
    # Filter the dataframe
    if not filtered_df.empty:
        mask = filtered_df.apply(is_within_timeframe, axis=1)
        filtered_df = filtered_df[mask]
    
    return filtered_df

def sort_results(df, sort_option):
    """Sort results based on the selected option"""
    if df.empty:
        return df
    
    if sort_option == "Date Posted":
        # Sort by date - most recent first
        if 'created_time' in df.columns:
            return df.sort_values('created_time', ascending=False)
        elif 'created_utc' in df.columns:
            return df.sort_values('created_utc', ascending=False)
        else:
            return df  # Fallback to original order
    elif sort_option == "Title Alphabetically":
        # Sort by title alphabetically, but skip "[" if title starts with it
        if 'title' in df.columns:
            def get_sort_key(title):
                """Get sort key for title, skipping '[' at the beginning"""
                if pd.isna(title):
                    return ""
                title_str = str(title).strip()
                if title_str.startswith('[') and len(title_str) > 1:
                    # Skip the '[' and sort by what comes after
                    return title_str[1:].lower()
                else:
                    return title_str.lower()
            
            # Create a temporary column for sorting
            df_copy = df.copy()
            df_copy['sort_key'] = df_copy['title'].apply(get_sort_key)
            sorted_df = df_copy.sort_values('sort_key', ascending=True, na_position='last')
            # Remove the temporary sort column and return
            return sorted_df.drop('sort_key', axis=1)
        else:
            return df  # Fallback to original order
    else:
        return df  # Default fallback

def get_combined_data():
    """Get combined data from both subreddits"""
    # Get original fetched data
    df_penpals = st.session_state.get('fetched_data_penpals', pd.DataFrame())
    df_penpalsover30 = st.session_state.get('fetched_data_penpalsover30', pd.DataFrame())
    
    # Add subreddit identifiers
    if not df_penpals.empty:
        df_penpals = df_penpals.copy()
        df_penpals['subreddit'] = 'penpals'
    if not df_penpalsover30.empty:
        df_penpalsover30 = df_penpalsover30.copy()
        df_penpalsover30['subreddit'] = 'penpalsover30'
    
    # Combine datasets
    combined_df = pd.concat([df_penpals, df_penpalsover30], ignore_index=True)
    return combined_df

def create_pagination_controls(total_posts, current_page, subreddit_name, posts_per_page=100):
    """Create pagination controls using radio buttons for more reliable navigation"""
    if total_posts <= posts_per_page:
        return current_page  # No pagination needed
    
    total_pages = (total_posts - 1) // posts_per_page + 1
    
    # Create page options
    page_options = []
    for i in range(total_pages):
        start = i * posts_per_page + 1
        end = min((i + 1) * posts_per_page, total_posts)
        page_options.append(f"{start}-{end}")
    
    # Use radio buttons in horizontal layout for better reliability
    selected_page_text = st.radio(
        label="_",
        label_visibility="collapsed",
        options=page_options,
        index=current_page if current_page < len(page_options) else 0,
        key=f"page_radio_{subreddit_name}",
        horizontal=True
    )
    
    # Return the selected page index
    if selected_page_text and selected_page_text in page_options:
        return page_options.index(selected_page_text)
    else:
        return current_page

def display_subreddit_results(current_keywords, age_keywords, subreddit_name):
    """Display the search results for a specific subreddit with dual keyword filtering"""
    # Get current filters from session state
    current_recency = st.session_state.get('recency_slider', 'All time')
    current_sort = st.session_state.get('sort_option', 'Date Posted')
    
    # Get combined data
    combined_data = get_combined_data()
    
    if combined_data.empty:
        st.info(f"No data available for r/{subreddit_name}.")
        return
    
    # Filter combined data for this specific subreddit
    subreddit_data = combined_data[combined_data['subreddit'] == subreddit_name].copy()
    
    if subreddit_data.empty:
        st.info(f"No posts available for r/{subreddit_name}")
        return

    # Apply keyword filtering if keywords are provided
    if current_keywords or age_keywords:
        def has_keyword_match(row):
            """Check if a post has any keyword matches"""
            body = row.get('body', '')
            title = row.get('title', '')
            full_text = str(title) + ' ' + str(body)
            title_text = str(title)
            
            # Use the same logic as highlight_keywords_in_text to detect matches
            import re
            
            # Check regular keywords in both title and body
            regular_match = False
            if current_keywords:
                words_to_highlight = set()
                
                # Add exact keyword matches (case-insensitive)
                for keyword in current_keywords:
                    keyword = keyword.strip()
                    if len(keyword) >= 2:
                        words_to_highlight.add(keyword.lower())
                        
                        # For multi-word keywords, also add individual words
                        keyword_words = keyword.lower().split()
                        for word in keyword_words:
                            if len(word) >= 2:
                                words_to_highlight.add(word)
                
                # Remove common stop words
                stop_words = {
                    'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                    'is', 'are', 'was', 'were', 'be', 'a', 'an', 'this', 'that', 'it', 'he', 'she'
                }
                words_to_highlight = {word for word in words_to_highlight 
                                     if word not in stop_words and len(word) >= 2}
                
                # Check if any words match in the full text (title + body)
                for word in words_to_highlight:
                    if len(word) >= 4:
                        pattern = r'(?<!\w)' + re.escape(word) + r'(?:ing|ed|er|s|ly)?\b'
                    else:
                        pattern = r'(?<!\w)' + re.escape(word) + r'(?!\w)'
                    
                    if re.search(pattern, full_text, flags=re.IGNORECASE):
                        regular_match = True
                        break
            
            # Check age keywords in title only
            age_match = False
            if age_keywords:
                age_words_to_highlight = set()
                
                # Add exact age keyword matches (case-insensitive)
                for keyword in age_keywords:
                    keyword = keyword.strip()
                    if len(keyword) >= 2:
                        age_words_to_highlight.add(keyword.lower())
                        
                        # For multi-word keywords, also add individual words
                        keyword_words = keyword.lower().split()
                        for word in keyword_words:
                            if len(word) >= 2:
                                age_words_to_highlight.add(word)
                
                # Check if any words match in the title only
                for word in age_words_to_highlight:
                    if len(word) >= 4:
                        pattern = r'(?<!\w)' + re.escape(word) + r'(?:ing|ed|er|s|ly)?\b'
                    else:
                        pattern = r'(?<!\w)' + re.escape(word) + r'(?!\w)'
                    
                    if re.search(pattern, title_text, flags=re.IGNORECASE):
                        age_match = True
                        break
            
            # Hard filtering logic:
            # If age keywords exist, they act as a hard filter (must match)
            # If regular keywords also exist, they must also match (AND logic)
            # If only regular keywords exist, only check regular match
            # If only age keywords exist, only check age match
            if current_keywords and age_keywords:
                # Both must match for hard filtering
                return regular_match and age_match
            elif age_keywords and not current_keywords:
                return age_match
            else:
                return regular_match
        
        # Filter to only posts that have keyword matches
        relevant_posts = subreddit_data[subreddit_data.apply(has_keyword_match, axis=1)]
    else:
        # Show all posts when no keywords
        relevant_posts = subreddit_data
    
    # Apply recency filter
    relevant_posts = filter_posts_by_recency(relevant_posts, current_recency)
    
    if relevant_posts.empty:
        st.warning(f"No posts found in r/{subreddit_name} matching your current filters")
        return
    
    # Apply sorting
    relevant_posts = sort_results(relevant_posts, current_sort)
    
    # Get current page for this subreddit
    page_key = f"{subreddit_name}_page"
    current_page = st.session_state.get(page_key, 0)
    
    # Create pagination controls
    posts_per_page = 100
    total_posts = len(relevant_posts)
    
    # Update page if it's out of bounds
    max_page = max(0, (total_posts - 1) // posts_per_page)
    if current_page > max_page:
        current_page = max_page
        st.session_state[page_key] = current_page
    
    # Show pagination controls at the top
    new_page = create_pagination_controls(total_posts, current_page, subreddit_name, posts_per_page)
    if new_page != current_page:
        st.session_state[page_key] = new_page
        st.rerun()  # Need rerun for pagination to work properly
    
    # Show result count when pagination is not needed (few results)
    if total_posts <= posts_per_page:
        st.caption(f"Found {total_posts} results.")
    
    # Calculate slice for current page
    start_idx = current_page * posts_per_page
    end_idx = min(start_idx + posts_per_page, total_posts)
    page_posts = relevant_posts.iloc[start_idx:end_idx]
    
    # Display results with title as header and metadata inside
    for _, row in page_posts.iterrows():
        # Use title as the header
        title = row.get('title', 'No title available')
        
        # Apply keyword highlighting to the title - only for regular keywords, not age keywords
        highlighted_title = str(title)
        if current_keywords:
            highlighted_title = highlight_keywords_in_text(
                str(title), 
                current_keywords
            )
        
        badge_color = get_badge_color_for_date(row)
        header_text = f":{badge_color}-badge[{format_post_date(row)}]\u2002" + highlighted_title

        with st.expander(header_text, expanded=True):
            st.caption(f"u/{row.get('author', 'unknown')}\u2002[Go to Post]({row.get('permalink', '')})")
            body = row.get('body', 'No content available')
            if pd.notna(body) and str(body).strip() and str(body).strip() != 'nan':
                # Highlight keywords in the body text if keywords exist
                highlighted_body = str(body)
                if current_keywords:
                    highlighted_body = highlight_keywords_in_text(
                        str(body), 
                        current_keywords
                    )
                st.markdown(highlighted_body)
            else:
                st.markdown("**Content:** *No content available*")


def display_results(current_keywords, age_keywords):
    """Display the search results in tabs for both subreddits"""
    # Show any fetch messages first
    if st.session_state.get('fetch_warning'):
        st.warning(st.session_state.fetch_warning)

    if st.session_state.get('fetch_error'):
        st.error(st.session_state.fetch_error)
        # Add a retry button for failed fetches
        if st.button("Retry Fetch", key="retry_fetch"):
            st.session_state.fetch_error = None
            st.session_state.fetch_requested = True
            st.rerun()
        return

    # Check if fetch is currently in progress
    if st.session_state.get('fetch_requested', False):
        st.info("Fetching data from Reddit... Please wait.")
        return

    # Check if any data is available
    has_penpals_data = (st.session_state.get('fetched_data_penpals') is not None and
                       not st.session_state.fetched_data_penpals.empty)
    has_penpalsover30_data = (st.session_state.get('fetched_data_penpalsover30') is not None and
                             not st.session_state.fetched_data_penpalsover30.empty)

    if not has_penpals_data and not has_penpalsover30_data:
        if st.session_state.get('has_fetched_data', False):
            st.info("No posts found. Try adjusting your filters or fetch again.")
            if st.button("Fetch Again", key="refetch"):
                st.session_state.fetch_requested = True
                st.rerun()
        else:
            st.info("Loading data from **r/penpals** and **r/penpalsover30**...")
        return

    # Create tabs for both subreddits
    st.caption(
        "Below you will find the latest posts from both subreddits. " \
        "Use the search and filtering options in the sidebar to refine your results i.e., Keywords, Age, Recency."
    )
    tab1, tab2 = st.tabs(["r/penpals", "r/penpalsover30"])

    with tab1:
        display_subreddit_results(current_keywords, age_keywords, "penpals")

    with tab2:
        display_subreddit_results(current_keywords, age_keywords, "penpalsover30")


# Main app flow
def main():
    """Main application flow"""
    # Create input interface
    keywords, age_keywords, sort_option, recency_filter = create_input_interface()

    # Handle fetch request if triggered from sidebar
    if st.session_state.get('fetch_requested', False):
        with st.spinner(
            "Fetching data for r/penpals and r/penpalsover30... This can take a minute.",
            show_time=True
        ):
            # Call the fetch function with UI elements
            handle_fetch_data(
                st.session_state.fetch_keywords,
            )

    # Display results with current filter values
    display_results(keywords, age_keywords)

if __name__ == "__main__":
    main()
