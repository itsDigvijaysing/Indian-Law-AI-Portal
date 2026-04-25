#!/bin/bash

# Indian Law AI Portal - Development Startup Script

echo "🚀 Starting Indian Law AI Portal Development Environment"
echo "======================================================="

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your Google API key."
    echo "   Edit .env and set GOOGLE_API_KEY=your_actual_api_key"
    echo ""
fi

# Create necessary directories
mkdir -p logs vector_db assets

# Function to start backend
start_backend() {
    echo "🐍 Starting Python Backend..."

    # Activate the conda env "my_env" (created with python=3.11 from conda-forge).
    # If conda isn't initialised in this shell, source it; if my_env doesn't exist
    # yet, fall back to whatever python is on PATH and warn.
    if command -v conda >/dev/null 2>&1; then
        # shellcheck disable=SC1091
        source "$(conda info --base)/etc/profile.d/conda.sh"
        if conda env list | grep -qE '^\s*my_env\s'; then
            conda activate my_env
            echo "Using conda environment: my_env ($(python --version))"
        else
            echo "⚠️  conda env 'my_env' not found. Create it with:"
            echo "    conda create -n my_env -c conda-forge python=3.11 -y"
            echo "    conda activate my_env"
            echo "    pip install -r requirements.txt groq"
        fi
    else
        echo "⚠️  conda not found on PATH; using system python: $(python3 --version 2>&1)"
    fi

    pip install -q -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null

    # IMPORTANT: launch from project root so relative paths
    # (assets/, vector_db/) resolve correctly.
    cd "$SCRIPT_DIR"
    python backend/main.py &
    BACKEND_PID=$!
    echo "✅ Backend started with PID: $BACKEND_PID"
    echo "📡 API available at: http://localhost:8000"
    echo "📚 API docs at: http://localhost:8000/docs"
}

# Function to start frontend
start_frontend() {
    echo "⚛️  Starting React Frontend..."
    cd "$SCRIPT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi
    npm start &
    FRONTEND_PID=$!
    cd "$SCRIPT_DIR"
    echo "✅ Frontend started with PID: $FRONTEND_PID"
    echo "🌐 Frontend available at: http://localhost:3000"
}

# Function to cleanup processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ Frontend stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
start_backend
sleep 3  # Give backend time to start
start_frontend

echo ""
echo "🎉 Both services are starting up!"
echo "📖 Check the logs above for any errors"
echo "🔗 Access the application at: http://localhost:3000"
echo "📋 Press Ctrl+C to stop all services"
echo ""

# Wait for services
wait