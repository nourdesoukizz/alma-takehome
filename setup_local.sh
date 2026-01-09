#!/bin/bash

echo "📦 Setting up Document Form Filler locally..."

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Install system dependencies for OCR and PDF processing
echo ""
echo "⚠️  System dependencies needed:"
echo "Please ensure you have installed:"
echo "  - Tesseract OCR: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)"
echo "  - Poppler: brew install poppler (macOS) or apt-get install poppler-utils (Linux)"
echo ""

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads
mkdir -p static

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  1. source venv/bin/activate"
echo "  2. python run_local.py"
echo ""
echo "The application will open at http://localhost:8000"
echo "Form filling will happen in a visible browser window!"