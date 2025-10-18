# Architecture Overview

## System Design

The Fake News Detection Bot is designed as a modular, scalable system with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                        WhatsApp Users                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Bot Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Selenium   │  │   Message    │  │   Response   │      │
│  │  Automation  │──│   Handler    │──│   Sender     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      REST API Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Flask     │  │   Endpoints  │  │    Rate      │      │
│  │   Server     │──│   /analyze/* │──│   Limiter    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Analysis Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Text     │  │    Image     │  │     URL      │      │
│  │   Analyzer   │  │   Analyzer   │  │   Analyzer   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     NLP      │  │  Perceptual  │  │  Web Scraper │      │
│  │   Models     │  │   Hashing    │  │   & Domain   │      │
│  │  (BERT etc)  │  │  & OCR       │  │   Checker    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Fact-Check  │  │    Image     │  │  Unreliable  │      │
│  │   Database   │  │    Hashes    │  │   Domains    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                     PostgreSQL                               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Scraper Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Alt News   │  │  Boom Live   │  │     PIB      │      │
│  │   Scraper    │  │   Scraper    │  │  Fact Check  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. WhatsApp Bot Layer

**Technology**: Selenium WebDriver

**Responsibilities**:
- Monitor incoming WhatsApp messages
- Extract message content (text, images, URLs)
- Send responses back to users
- Maintain WhatsApp Web session

**Key Files**:
- `whatsapp/bot.py`

### 2. REST API Layer

**Technology**: Flask

**Endpoints**:
- `POST /analyze/text`: Analyze text messages
- `POST /analyze/image`: Analyze images
- `POST /analyze/url`: Analyze URLs
- `GET /stats`: System statistics
- `GET /health`: Health check

**Key Files**:
- `backend/api/app.py`

### 3. Analysis Layer

#### Text Analyzer

**Technology**: NLTK, SpaCy, Hugging Face Transformers

**Capabilities**:
- Language detection
- Keyword extraction
- Claim extraction
- Semantic similarity matching
- Embedding generation

**Key Files**:
- `backend/analyzers/text_analyzer.py`

#### Image Analyzer

**Technology**: OpenCV, Tesseract OCR, ImageHash

**Capabilities**:
- Perceptual hashing (pHash, dHash, aHash)
- Image similarity detection
- OCR text extraction
- Image preprocessing

**Key Files**:
- `backend/analyzers/image_analyzer.py`

#### URL Analyzer

**Technology**: BeautifulSoup, Requests

**Capabilities**:
- Web page content extraction
- Domain reliability checking
- URL structure analysis
- Suspicious pattern detection

**Key Files**:
- `backend/analyzers/url_analyzer.py`

### 4. Database Layer

**Technology**: PostgreSQL with SQLAlchemy ORM

**Schema**:

```sql
fact_checks (
    id, claim, verdict, explanation,
    source, source_url, published_date,
    language, keywords, embedding
)

image_hashes (
    id, phash, dhash, ahash,
    context, misleading_context,
    source, source_url
)

unreliable_domains (
    id, domain, category, reason,
    source, is_active
)

user_queries (
    id, user_id, query_type, query_content,
    verdict, confidence_score, timestamp
)

scraper_logs (
    id, scraper_name, start_time, end_time,
    status, articles_scraped, errors
)
```

**Key Files**:
- `backend/models/database.py`
- `backend/database/setup_db.py`

### 5. Scraper Layer

**Technology**: BeautifulSoup, Requests

**Sources**:
- Alt News (https://www.altnews.in)
- Boom Live (https://www.boomlive.in)
- PIB Fact Check (https://factcheck.pib.gov.in)

**Key Files**:
- `backend/scrapers/fact_check_scrapers.py`
- `backend/scrapers/run_all_scrapers.py`

### 6. Response Generator

**Technology**: Python with multilingual templates

**Capabilities**:
- Generate emoji-coded responses
- Multilingual support (English, Tamil)
- Context-aware messaging

**Key Files**:
- `backend/utils/response_generator.py`

## Data Flow

### Text Message Analysis

```
User sends text message
    ↓
WhatsApp Bot extracts text
    ↓
API receives text via /analyze/text
    ↓
Text Analyzer processes:
  - Detects language
  - Extracts claims
  - Computes embedding
    ↓
Database query for matching fact-checks
    ↓
Semantic similarity matching
    ↓
Response Generator creates verdict
    ↓
Response sent back via WhatsApp
```

### Image Analysis

```
User sends image
    ↓
WhatsApp Bot extracts image
    ↓
API receives image via /analyze/image
    ↓
Image Analyzer processes:
  - Computes perceptual hashes
  - Extracts text via OCR
    ↓
Database query for matching images
    ↓
Hash comparison (Hamming distance)
    ↓
If text found, analyze via Text Analyzer
    ↓
Response Generator creates verdict
    ↓
Response sent back via WhatsApp
```

### URL Analysis

```
User sends URL
    ↓
WhatsApp Bot extracts URL
    ↓
API receives URL via /analyze/url
    ↓
URL Analyzer processes:
  - Validates URL
  - Checks domain reliability
  - Fetches webpage content
    ↓
Text Analyzer processes content
    ↓
Database query for matching claims
    ↓
Response Generator creates verdict
    ↓
Response sent back via WhatsApp
```

## Scalability Considerations

### Horizontal Scaling

- API can be run on multiple servers behind a load balancer
- Database can use read replicas for queries
- Scrapers can run on separate machines

### Performance Optimization

- Caching frequently accessed fact-checks
- Pre-computed embeddings for all claims
- Indexed database queries
- Rate limiting to prevent abuse

### Storage Management

- Regular database cleanup of old logs
- Image hash deduplication
- Compressed storage for embeddings

## Security

### Data Privacy

- User IDs are hashed
- No message content stored long-term
- Secure database connections

### API Security

- Rate limiting per user/IP
- Input validation and sanitization
- CORS configuration
- SQL injection prevention via ORM

### WhatsApp Security

- Session data stored locally
- No credential storage
- Encrypted database connections

## Deployment Options

### Local Development

- Run all components on a single machine
- SQLite can be used instead of PostgreSQL
- Suitable for testing and development

### Self-Hosted Server

- Deploy on a personal server or VPS
- PostgreSQL for production database
- Nginx reverse proxy for API
- systemd services for auto-restart

### Raspberry Pi

- Lightweight deployment
- Reduced model sizes
- Limited concurrent users
- Perfect for personal/small group use

## Monitoring and Logging

### Logs

- API access logs
- Scraper execution logs
- Error logs with stack traces
- User query logs (anonymized)

### Metrics

- API response times
- Analysis accuracy
- Database query performance
- Scraper success rates

### Health Checks

- API endpoint: `/health`
- Database connectivity
- Model availability
- Scraper status

## Future Enhancements

1. **Machine Learning Improvements**
   - Fine-tune models on Indian context
   - Active learning from user feedback
   - Multi-modal analysis (text + image)

2. **Feature Additions**
   - Video analysis
   - Audio/voice message analysis
   - Real-time fact-checking
   - Browser extension

3. **Infrastructure**
   - Kubernetes deployment
   - Microservices architecture
   - Cloud storage for images
   - CDN for static assets

4. **Community Features**
   - User reporting system
   - Crowdsourced fact-checking
   - Public API access
   - Mobile app
