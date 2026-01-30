#!/bin/bash

# Quick setup script for SmartLead Accounts Viewer

echo "🚀 Setting up SmartLead Accounts Viewer..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create secrets file
echo "🔐 Creating secrets file..."
if [ ! -f .streamlit/secrets.toml ]; then
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml
    echo "⚠️  IMPORTANT: Edit .streamlit/secrets.toml and add your actual credentials!"
    echo "   - SMARTLEAD_BEARER_TOKEN"
    echo "   - APP_PASSWORD"
else
    echo "ℹ️  secrets.toml already exists, skipping..."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .streamlit/secrets.toml with your credentials"
echo "   2. Run: source venv/bin/activate"
echo "   3. Run: streamlit run app.py"
echo ""
echo "🌐 App will be available at: http://localhost:8501"
