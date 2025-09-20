# Indian Law AI Portal - Development Guide

## Quick Start

1. **Setup Environment**:
```bash
python setup.py
```

2. **Start Development Servers**:
```bash
./start_dev.sh
```

3. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Manual Setup

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r ../requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

## Configuration

### Required Environment Variables
Create a `.env` file in the root directory:

```bash
# Google AI Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Model Configuration  
LLM_MODEL=gemini-1.5-pro
EMBEDDING_MODEL=text-embedding-004

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG_MODE=true
```

### Adding Legal Documents
1. Place PDF files in the `assets/` directory
2. Use the admin API to process documents:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/documents/process" \
     -H "Content-Type: application/json" \
     -d '{"file_paths": ["IPC.pdf", "CrPC.pdf"]}'
```

## Development Commands

### Backend Commands
```bash
# Start backend server
cd backend && python main.py

# Run tests
cd backend && python -m pytest

# Check API health
curl http://localhost:8000/health
```

### Frontend Commands
```bash
# Start development server
cd frontend && npm start

# Build for production
cd frontend && npm run build

# Run tests
cd frontend && npm test
```

## API Endpoints

### Query Endpoints
- `POST /api/v1/query` - Process legal queries
- `GET /api/v1/agents` - List available agents
- `POST /api/v1/validate` - Validate queries

### Admin Endpoints
- `POST /api/v1/admin/documents/process` - Process documents
- `GET /api/v1/admin/documents/list` - List documents
- `GET /api/v1/admin/statistics` - System statistics

### Health Endpoints
- `GET /health` - System health check
- `GET /health/ping` - Simple ping
- `GET /health/ready` - Readiness check

## Architecture Overview

```
Indian Law AI Portal
├── Backend (Python/FastAPI)
│   ├── Agent Development Kit (ADK)
│   │   ├── Base Agent Framework
│   │   ├── Criminal Law Agent
│   │   ├── Civil Law Agent
│   │   ├── Constitutional Law Agent
│   │   └── General Legal Agent
│   ├── RAG Pipeline
│   │   ├── Document Processor
│   │   ├── Embedding Generator
│   │   ├── Vector Database (FAISS)
│   │   └── RAG Fusion Retriever
│   └── API Endpoints
├── Frontend (React)
│   ├── Query Interface
│   ├── Response Display
│   └── System Status
└── Assets
    └── Legal PDF Documents
```

## Troubleshooting

### Common Issues

1. **Google API Key Error**:
   - Ensure GOOGLE_API_KEY is set in .env file
   - Verify the API key is valid and has proper permissions

2. **No Documents Found**:
   - Add PDF files to assets/ directory
   - Process documents via admin API

3. **Port Already in Use**:
   - Change API_PORT in .env file
   - Or kill existing processes: `pkill -f "python main.py"`

4. **Frontend Build Issues**:
   - Delete node_modules and reinstall: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility

### Logs
- Backend logs: `logs/app.log`
- Frontend logs: Browser console
- System logs: Terminal output

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Security Notes

- This is a development/research tool
- Do not use in production without proper security review
- Always validate legal advice with qualified professionals
- Keep API keys secure and never commit them to version control