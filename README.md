# 🛡️ Fake News Detection System

A comprehensive fake news detection system with AI-powered analysis using Google Gemini 2.0 Flash. The system combines database fact-checking with real-time AI analysis, automated scraping from Indian fact-checkers, and a web interface for testing.

## ✨ Features

### Core Capabilities
- **Hybrid Analysis**: Database-first approach with AI fallback for unverified claims
- **Google Gemini 2.0 Flash Integration**: Real-time fact-checking with 95%+ confidence ratings
- **Automated Learning**: High-confidence AI results (>90%) are automatically added to the database
- **Multi-Source Scraping**: Automated fact-check collection from:
  - Alt News
  - Boom Live  
  - PIB Fact Check
- **Deduplication System**: 75% similarity threshold prevents content pollution
- **Multilingual Support**: English and Tamil (extensible to other Indian languages)

### Analysis Types
- **Text Analysis**: Semantic similarity matching using sentence transformers
- **Image Analysis**: Perceptual hashing and reverse image search
- **URL Analysis**: Domain verification and web scraping
- **OCR**: Extract text from images using Tesseract

## 🏗️ Architecture

```
Fake/
├── backend/
│   ├── api/
│   │   └── app.py                 # Flask API with hybrid analysis logic
│   ├── analyzers/
│   │   ├── gemini_analyzer.py     # Gemini 2.0 Flash integration
│   │   ├── text_analyzer.py       # Semantic similarity matching
│   │   ├── image_analyzer.py      # Image hash comparison
│   │   └── url_analyzer.py        # Web scraping & domain check
│   ├── scrapers/
│   │   ├── sources/               # Individual scraper implementations
│   │   ├── run_all_scrapers.py    # Automated scraping orchestration
│   │   └── deduplicator.py        # Content deduplication
│   ├── models/
│   │   └── database.py            # SQLAlchemy models
│   └── utils/
│       └── response_generator.py  # Multilingual response formatting
├── test_website/                  # Web interface for testing
│   ├── index.html
│   ├── script.js
│   └── style.css
└── whatsapp/                      # WhatsApp bot (optional)
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Tesseract OCR
- Git

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Fake

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr postgresql postgresql-contrib
```

### 3. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE fake_news_db;
CREATE USER fake_news_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fake_news_db TO fake_news_user;
\q

# Initialize database schema
python backend/database/setup_db.py
```

### 4. Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://fake_news_user:your_password@localhost/fake_news_db

# Gemini AI (Get your key from https://ai.google.dev/)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_ENABLED=True
GEMINI_CONFIDENCE_THRESHOLD=0.6
GEMINI_LEARNING_THRESHOLD=0.9

# NLP Models
NLP_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
SIMILARITY_THRESHOLD=0.75

# API Settings
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. Initial Data Collection

```bash
# Run scrapers to populate database
python backend/scrapers/run_all_scrapers.py

# This will scrape from Alt News, Boom Live, and PIB Fact Check
```

### 6. Start the API Server

```bash
python backend/api/app.py

# Server will start on http://localhost:5000
```

### 7. Test with Web Interface

Open `test_website/index.html` in your browser or serve it:

```bash
cd test_website
python -m http.server 8000

# Navigate to http://localhost:8000
```

## 📡 API Endpoints

### Health Check
```bash
GET /health

Response: {
  "status": "healthy",
  "database": "connected",
  "fact_checks_count": 30,
  "gemini_enabled": true
}
```

### Analyze Text
```bash
POST /analyze/text
Content-Type: application/json

{
  "text": "Your claim to check",
  "language": "en"
}

Response: {
  "verdict": "FALSE",
  "confidence": 0.95,
  "explanation": "Detailed explanation...",
  "source": "gemini",  // or "database"
  "analysis_type": "text"
}
```

### Analyze Image
```bash
POST /analyze/image
Content-Type: multipart/form-data

file: <image_file>
language: en

Response: Similar to text analysis
```

### Analyze URL
```bash
POST /analyze/url
Content-Type: application/json

{
  "url": "https://example.com/article",
  "language": "en"
}

Response: Similar to text analysis
```

## 🤖 How It Works

### Hybrid Analysis Flow

1. **Database Search**: Query checks against 30+ fact-checks using semantic similarity
2. **Match Found** (>75% similarity): Return verdict from database with confidence score
3. **No Match**: Automatically fall back to Gemini AI for real-time analysis
4. **High Confidence AI Result** (>90%): Automatically saved to database for future queries
5. **Low Confidence** (<60%): Return "unverified" status

### Gemini AI Integration

- **Model**: Google Gemini 2.0 Flash (Fast, efficient, free tier available)
- **Confidence Thresholds**:
  - 0.6+: Results returned to user
  - 0.9+: Results saved to database for learning
- **Features**:
  - Real-time fact-checking
  - Detailed explanations
  - Red flag identification
  - Reasoning breakdown

## 📊 Current Database Stats

- **Total Fact-Checks**: 30+ (29 scraped + AI-generated)
- **Sources**: Alt News, Boom Live, PIB Fact Check, Gemini AI
- **Deduplication**: 75% similarity threshold
- **Languages**: English, Tamil

## 🔧 Maintenance

### Update Fact-Check Database

```bash
# Run scrapers manually
python backend/scrapers/run_all_scrapers.py

# Or set up automated scheduling (cron example)
# Daily at 2 AM
0 2 * * * cd /path/to/Fake && venv/bin/python backend/scrapers/run_all_scrapers.py
```

### Database Migrations

```bash
# If you need to migrate the database
python backend/database/migrate_db.py
```

## 🛠️ Tech Stack

- **Backend**: Flask, Python 3.13
- **AI**: Google Gemini 2.0 Flash
- **NLP**: Sentence Transformers, NLTK, LangDetect
- **Database**: PostgreSQL, SQLAlchemy
- **Image Processing**: PIL, ImageHash, Tesseract OCR
- **Web Scraping**: BeautifulSoup4, Requests
- **Frontend**: Vanilla HTML/CSS/JavaScript

## 📝 Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GEMINI_ENABLED` | Enable/disable Gemini fallback | `True` |
| `GEMINI_CONFIDENCE_THRESHOLD` | Minimum confidence to return results | `0.6` |
| `GEMINI_LEARNING_THRESHOLD` | Minimum confidence to save to DB | `0.9` |
| `SIMILARITY_THRESHOLD` | Database matching threshold | `0.75` |
| `NLP_MODEL` | Sentence transformer model | `paraphrase-multilingual-MiniLM-L12-v2` |

## 🚦 Verdict System

- **TRUE**: Verified as true
- **FALSE**: Verified as false  
- **MISLEADING**: Partially true or lacks context
- **UNVERIFIED**: Cannot be verified with available information

## 🌐 Multilingual Support

Currently supports:
- **English** (en)
- **Tamil** (ta)

Easily extensible to other languages by:
1. Adding translations in `backend/utils/response_generator.py`
2. Using multilingual NLP models

## 🔒 Security Notes

- Never commit `.env` file with API keys
- Use environment variables for sensitive configuration
- Implement rate limiting in production
- Validate all user inputs
- Use HTTPS in production

## 📄 License

[MIT License](LICENSE)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues or questions, please open an issue on GitHub.

## 🎯 Roadmap

- [ ] Add more Indian fact-checker sources
- [ ] Implement rate limiting
- [ ] Add caching layer
- [ ] WhatsApp bot integration
- [ ] Docker containerization
- [ ] API authentication
- [ ] Admin dashboard
- [ ] Batch processing API
- [ ] Export reports functionality

## 🙏 Acknowledgments

- Indian fact-checkers: Alt News, Boom Live, PIB Fact Check
- Google Gemini AI
- Open source NLP community
