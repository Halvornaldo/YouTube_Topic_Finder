#!/bin/bash

# YouTube Topic Finder - Setup Script
# Run this script to set up the project for the first time

set -e  # Exit on error

echo "========================================="
echo "YouTube Topic Finder - Setup Script"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if Docker is installed
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ Pip upgraded"
echo ""

# Install requirements
echo "Installing Python dependencies (this may take a few minutes)..."
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys!"
else
    echo "✓ .env file already exists"
fi
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p logs downloads temp
echo "✓ Directories created"
echo ""

# Start Docker containers
echo "Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis
echo "✓ Containers started"
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5
echo "✓ PostgreSQL should be ready"
echo ""

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "✓ Database migrations completed"
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Start the server: uvicorn src.main:app --reload"
echo "3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "To activate virtual environment in the future:"
echo "  source venv/bin/activate"
echo ""
echo "To stop Docker containers:"
echo "  docker-compose down"
echo ""
