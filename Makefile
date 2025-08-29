# Reddit Penpal Parser - Makefile for development and deployment

.PHONY: help init run clean test verify

# Default target
help:
	@echo "Available commands:"
	@echo "  make init        - Set up virtual environment and install dependencies"
	@echo "  make run         - Run the Streamlit app locally"
	@echo "  make verify      - Check if setup is complete and ready to run"
	@echo "  make clean       - Remove virtual environment and cache files"
	@echo "  make test        - Run basic tests"

# Initialize development environment
init:
	@echo "Checking for uv installation..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install it with: pip install uv"; exit 1; }
	@echo "Setting up virtual environment with uv..."
	uv venv
	@echo "Activating virtual environment and installing dependencies..."
	uv pip install -r requirements.txt
	@echo "✅ Virtual environment created and dependencies installed!"
	@echo ""
	@echo "To activate the environment manually:"
	@echo "  source .venv/bin/activate  # On Linux/Mac"
	@echo "  .venv\\Scripts\\activate   # On Windows"
	@echo ""
	@echo "To run the app:"
	@echo "  make run"

# Run the Streamlit app
run:
	@if command -v uv >/dev/null 2>&1 && [ -d ".venv" ]; then \
		echo "Running with uv virtual environment..."; \
		uv run streamlit run streamlit_app.py; \
	else \
		echo "No virtual environment found. Please run 'make init' first."; \
		exit 1; \
	fi

# Clean up environments and cache
clean:
	@echo "Cleaning up..."
	@if [ -d ".venv" ]; then \
		rm -rf .venv; \
		echo "Removed uv virtual environment"; \
	fi
	@if [ -d "__pycache__" ]; then \
		rm -rf __pycache__; \
	fi
	@if [ -d "utils/__pycache__" ]; then \
		rm -rf utils/__pycache__; \
	fi
	@echo "✅ Cleanup complete!"

# Basic test
test:
	@echo "Running basic tests..."
	@if command -v uv >/dev/null 2>&1 && [ -d ".venv" ]; then \
		uv run python -c "import streamlit, pandas, requests; print('✅ All dependencies imported successfully')"; \
	else \
		python -c "import streamlit, pandas, requests; print('✅ All dependencies imported successfully')"; \
	fi

# Verify complete setup
verify:
	@echo "🔍 Verifying setup..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not installed"; exit 1; }
	@[ -d ".venv" ] || { echo "❌ Virtual environment not found. Run 'make init' first."; exit 1; }
	@[ -f ".streamlit/secrets.toml" ] || { echo "❌ Reddit API secrets not configured. Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and add your credentials."; exit 1; }
	@echo "✅ uv installed"
	@echo "✅ Virtual environment exists"
	@echo "✅ Secrets file exists"
	@make test
	@echo "🎉 Setup complete! Run 'make run' to start the app."
