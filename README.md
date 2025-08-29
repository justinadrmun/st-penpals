# st-penpals

A Streamlit web application for fetching, filtering, and displaying posts from Reddit subreddits `r/penpals` and `r/penpalsover30`. This app helps users find relevant penpal posts by applying keyword search, age range filtering, and various sorting options.

## Features

- **Dual Subreddit Support**: Fetches posts from both `r/penpals` and `r/penpalsover30`
- **Advanced Filtering**:
  - Keyword search with highlighting (supports multi-word phrases)
  - Age range filtering (applied to post titles only)
  - Recency filters (Today, Last week, Last month, etc.)
  - Sorting by date or title
- **Smart Deduplication**: Removes duplicate posts per user while preserving deleted accounts
- **Pagination**: Handles large result sets with 100 posts per page
- **Responsive UI**: Clean, modern interface with expandable post views
- **Color-coded Badges**: Visual indicators for post age (green=recent, orange=1 month, red=older)

## Prerequisites

- Python 3.12+ (recommended)
- Reddit API credentials (get from [Reddit Apps](https://www.reddit.com/prefs/apps))

## Quick Start

### 1. Clone and Setup

```bash
git clone git@github.com:justinadrmun/st-penpals.git
cd st-penpals
```

**Prerequisites Check:**
- Ensure you have Python 3.8+ installed: `python --version`
- Install uv (modern Python package manager): `pip install uv` or see [uv installation](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Set up Virtual Environment

```bash
make init
```

### 3. Configure Reddit API Credentials

**For Local Development:**
```bash
# Copy the example secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Edit with your Reddit API credentials
nano .streamlit/secrets.toml
```

**Required credentials:**
- `CLIENT_ID`: Your Reddit app's client ID
- `CLIENT_SECRET`: Your Reddit app's secret  
- `REDDIT_USERNAME`: Your Reddit username
- `APP_NAME`: A name for your app (e.g., "penpal-parser")

💡 **New to Reddit API?** See the [Getting Reddit API Credentials](#getting-reddit-api-credentials) section below for step-by-step instructions.

### 4. Run the Application

```bash
make run
```

Or manually:
```bash
uv run streamlit run streamlit_app.py
```

The app will be available at `http://localhost:8501`

## Project Structure

```
st-penpals/
├── streamlit_app.py          # Main Streamlit application
├── requirements.txt          # Python dependencies
├── Makefile                  # Development commands
├── .streamlit/
│   └── secrets.toml.example  # Template for local secrets
├── utils/
│   ├── __init__.py
│   ├── data_loader.py        # Data fetching and processing
│   ├── fetch_penpals.py      # Reddit API client
│   └── text_processing.py    # Text utilities and highlighting
└── README.md
```

## Usage

1. **Enter Keywords**: Comma-separated keywords for searching post content
2. **Set Age Range**: Filter posts by age mentioned in titles (18-99)
3. **Choose Filters**:
   - Recency: Filter by post date
   - Sort: Order by date or title
4. **Browse Results**: Use tabs to switch between subreddits
5. **Navigate**: Use pagination controls for large result sets

### Filtering Logic

- **Regular Keywords**: Searched in both title and body text
- **Age Keywords**: Searched only in titles
- **AND Logic**: If both keyword types are provided, posts must match both
- **Highlighting**: Matching keywords are highlighted in violet badges


## Deployment

### Streamlit Community Cloud

1. **Push to GitHub**: Ensure your code is in a public GitHub repository
2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repo and select `streamlit_app.py`
3. **Add Secrets**:
   - In Advanced settings, paste the contents of your `.streamlit/secrets.toml` into the "Secrets" field
   - Format should match the TOML structure:
   ```toml
   CLIENT_ID = "your_actual_client_id"
   CLIENT_SECRET = "your_actual_client_secret"
   REDDIT_USERNAME = "your_username"
   APP_NAME = "penpal-parser"
   ```
4. **Deploy**: Click "Deploy!" and your app will be live in minutes

## Development

### Available Make Commands

```bash
make help      # Show all available commands
make init      # Set up development environment (uv)
make verify    # Check if setup is complete and ready to run
make run       # Run the Streamlit app
make clean     # Remove environments and cache
make test      # Test dependency imports
```

💡 **Pro tip**: Run `make verify` after setup to ensure everything is configured correctly!

## Troubleshooting

### Common Issues

**"Error: CLIENT_ID and CLIENT_SECRET must be set"**
- Ensure `.streamlit/secrets.toml` exists with valid Reddit API credentials
- For deployment, check that secrets are properly set in Streamlit Cloud

**"Module not found" errors**
- Run `make init` to set up the virtual environment
- Ensure you're using the correct Python environment

**"Connection timeout"**
- Check your internet connection
- Reddit API may be rate-limiting; the app includes delays between requests

**Large dataset performance**
- The app fetches 1000 posts per subreddit on first load
- Results are cached in session state for subsequent filtering

### Getting Reddit API Credentials

1. Go to [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Choose "script" as the app type
4. Fill in:
   - Name: Your app name
   - Description: Brief description
   - Redirect URI: `http://localhost:8080` (not used for script apps)
5. Copy the client ID (under the app name) and secret