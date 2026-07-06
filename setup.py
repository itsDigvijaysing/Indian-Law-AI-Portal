"""
Setup and initialization script for Indian Law AI Portal

This script helps set up the environment and initialize the system.
"""

import os
import sys
import subprocess
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "vector_db", 
        "assets",
        "backend/temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def setup_environment():
    """Setup environment file"""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists() and not env_file.exists():
        print("Setting up environment file...")
        content = env_example.read_text()
        env_file.write_text(content)
        print("✓ Created .env file from .env.example")
        print("⚠️  Please edit .env and add your GROQ_API_KEY (or GOOGLE_API_KEY with LLM_PROVIDER=gemini)")
    elif env_file.exists():
        print("✓ Environment file already exists")
    else:
        print("❌ .env.example file not found")

def install_backend_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    # Check if we're in a conda environment
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env:
        print(f"Using conda environment: {conda_env}")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✓ Python dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        print("You can manually install with: pip install -r requirements.txt")

def setup_frontend():
    """Setup frontend dependencies"""
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        print("Setting up frontend...")
        try:
            os.chdir(frontend_dir)
            subprocess.run(["npm", "install"], check=True, capture_output=True, text=True)
            os.chdir("..")
            print("✓ Frontend dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install frontend dependencies: {e}")
            print("You can manually install with: cd frontend && npm install")
        except FileNotFoundError:
            print("⚠️  npm not found. Please install Node.js to set up the frontend")
    else:
        print("❌ Frontend directory not found")

def display_usage():
    """Display usage instructions"""
    print("\n" + "="*60)
    print("🚀 INDIAN LAW AI PORTAL - SETUP COMPLETE")
    print("="*60)
    print("\n📋 NEXT STEPS:")
    print("\n1. Environment Setup:")
    print("   - Edit .env and add your GROQ_API_KEY (recommended)")
    print("   - Or set LLM_PROVIDER=gemini with GOOGLE_API_KEY")

    print("\n2. Add Legal Documents:")
    print("   - Place PDF files in the 'assets/' folder")
    print("   - Examples: IPC.pdf, CrPC.pdf, Constitution.pdf")

    print("\n3. Start the Application:")
    print("   ./start_dev.sh")
    print("   # Or manually (ALWAYS from the project root, never inside backend/):")
    print("   python backend/main.py")
    print("   # In another terminal:")
    print("   cd frontend && npm start")
    
    print("\n4. Access the Application:")
    print("   - Frontend: http://localhost:3000")
    print("   - API: http://localhost:8000")
    print("   - API Docs: http://localhost:8000/docs")
    
    print("\n🔧 System Architecture:")
    print("   ├── Agent Development Kit (ADK)")
    print("   │   ├── Criminal Law Agent")
    print("   │   ├── Civil Law Agent")
    print("   │   ├── Constitutional Law Agent")
    print("   │   └── General Legal Agent")
    print("   ├── RAG Fusion Pipeline")
    print("   │   ├── Document Processing")
    print("   │   ├── Embedding Generation")
    print("   │   ├── Vector Database (FAISS)")
    print("   │   └── Query Reformulation")
    print("   └── FastAPI Backend + React Frontend")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("   - Requires a Groq API key (or Google AI key with LLM_PROVIDER=gemini) for LLM features")
    print("   - Add legal PDF documents to assets/ folder")
    print("   - First document processing may take time")
    print("   - This is for educational/research purposes")
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("🔧 Setting up Indian Law AI Portal...")
    print("-" * 40)
    
    create_directories()
    setup_environment()
    
    # Check if running interactively
    if sys.stdin.isatty():
        install_deps = input("\nInstall Python dependencies now? (y/n): ").lower().strip()
        if install_deps in ['y', 'yes']:
            install_backend_dependencies()
        
        setup_frontend_deps = input("Setup frontend dependencies now? (y/n): ").lower().strip()
        if setup_frontend_deps in ['y', 'yes']:
            setup_frontend()
    else:
        # Non-interactive mode - install everything
        print("\nRunning in non-interactive mode. Installing all dependencies...")
        install_backend_dependencies()
        setup_frontend()
    
    display_usage()

if __name__ == "__main__":
    main()