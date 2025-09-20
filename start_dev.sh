#!/bin/bash

# Indian Law AI Portal - Development Startup Script

echo "🚀 Starting Indian Law AI Portal Development Environment"
echo "======================================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your Google API key."
    echo "   Edit .env and set GOOGLE_API_KEY=your_actual_api_key"
    echo ""
fi

# Function to start backend
start_backend() {
    echo "🐍 Starting Python Backend..."
    cd backend
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r ../requirements.txt
    python main.py &
    BACKEND_PID=$!
    cd ..
    echo "✅ Backend started with PID: $BACKEND_PID"
    echo "📡 API available at: http://localhost:8000"
    echo "📚 API docs at: http://localhost:8000/docs"
}

# Function to start frontend
start_frontend() {
    echo "⚛️  Starting React Frontend..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi
    npm start &
    FRONTEND_PID=$!
    cd ..
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

# Create necessary directories
mkdir -p logs vector_db assets

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