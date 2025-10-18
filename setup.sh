#!/bin/bash

# Setup script for Fake News Detection Bot

echo "========================================"
echo "Fake News Detection Bot - Setup Script"
echo "========================================"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is designed for Linux systems"
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get install -y python3-pip python3-dev python3-venv
sudo apt-get install -y postgresql postgresql-contrib libpq-dev
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-tam
sudo apt-get install -y libopencv-dev
sudo apt-get install -y chromium-browser chromium-chromedriver

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Download NLP models
echo "🧠 Downloading NLP models..."
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Set up PostgreSQL database
echo "🗄️  Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE fakenews_db;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER fakenews_user WITH PASSWORD 'fakenews123';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fakenews_db TO fakenews_user;"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p whatsapp/session
mkdir -p data/images
mkdir -p /tmp/uploads

# Initialize database
echo "🗄️  Initializing database..."
python backend/database/setup_db.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run scrapers to populate database: python backend/scrapers/run_all_scrapers.py"
echo "3. Start the API: python backend/api/app.py"
echo "4. Start the WhatsApp bot: python whatsapp/bot.py"
echo ""
echo "For more information, see README.md"
