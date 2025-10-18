# Adding New Languages

This guide explains how to add support for new Indian languages to the Fake News Detection Bot.

## Current Supported Languages

- English (en)
- Tamil (ta)

## Steps to Add a New Language

### 1. Install Language Support

#### For Tesseract OCR

```bash
# Example: Adding Hindi support
sudo apt-get install tesseract-ocr-hin

# Example: Adding Telugu support
sudo apt-get install tesseract-ocr-tel

# Example: Adding Kannada support
sudo apt-get install tesseract-ocr-kan

# Example: Adding Malayalam support
sudo apt-get install tesseract-ocr-mal
```

List of Tesseract language codes:
- Hindi: `hin`
- Telugu: `tel`
- Kannada: `kan`
- Malayalam: `mal`
- Marathi: `mar`
- Bengali: `ben`
- Gujarati: `guj`
- Punjabi: `pan`

#### Update .env Configuration

```env
TESSERACT_LANGS=eng+tam+hin+tel
```

### 2. Add Response Templates

Edit `backend/utils/response_generator.py`:

```python
# Add your language to the templates dictionary
'hi': {  # Hindi
    'false': {
        'emoji': '🔴',
        'title': 'झूठ',
        'verdict_text': 'यह दावा जाँचा गया है और झूठा पाया गया है।',
        'advice': 'कृपया इस जानकारी को साझा न करें।'
    },
    'misleading': {
        'emoji': '🟡',
        'title': 'भ्रामक',
        'verdict_text': 'यह सामग्री भ्रामक के रूप में चिह्नित की गई है।',
        'advice': 'छवि या दावे को संदर्भ से बाहर उपयोग किया गया है।'
    },
    'unverified': {
        'emoji': '⚪',
        'title': 'सत्यापित नहीं कर सके',
        'verdict_text': 'हम अपने डेटाबेस में इस दावे को सत्यापित नहीं कर सके।',
        'advice': 'कृपया सावधान रहें और साझा करने से पहले कई विश्वसनीय स्रोतों से सत्यापित करें।'
    },
    'true': {
        'emoji': '🟢',
        'title': 'सच',
        'verdict_text': 'यह दावा सच के रूप में सत्यापित किया गया है।',
        'advice': 'यह जानकारी सटीक प्रतीत होती है।'
    },
    'greeting': 'नमस्ते! मैं समाचार, छवियों और लिंक को सत्यापित करने में आपकी मदद कर सकता हूं।',
    'processing': 'विश्लेषण कर रहे हैं... कृपया प्रतीक्षा करें।',
    'error': 'क्षमा करें, आपके अनुरोध को संसाधित करने में त्रुटि हुई। कृपया पुन: प्रयास करें।',
    'source_prefix': '\n\n📌 स्रोत: ',
    'explanation_prefix': '\n\n💡 व्याख्या:\n',
    'original_context': '\n\n🔍 मूल संदर्भ:\n'
}
```

### 3. Update Language Detection

The `langdetect` library automatically detects most Indian languages. Verify the language code mapping in `backend/analyzers/text_analyzer.py`:

```python
lang_map = {
    'en': 'en',
    'ta': 'ta',
    'hi': 'hi',  # Hindi
    'te': 'te',  # Telugu
    'ml': 'ml',  # Malayalam
    'kn': 'kn',  # Kannada
    'mr': 'mr',  # Marathi
    'bn': 'bn',  # Bengali
    'gu': 'gu',  # Gujarati
    'pa': 'pa',  # Punjabi
}
```

### 4. Update Supported Languages Configuration

In `.env`:

```env
SUPPORTED_LANGUAGES=en,ta,hi,te,kn,ml
DEFAULT_LANGUAGE=en
```

### 5. Add NLP Support (Optional)

For better text analysis in your language:

#### Install SpaCy Language Model

```bash
# For multilingual support (already included)
python -m spacy download xx_ent_wiki_sm

# For specific languages (if available)
python -m spacy download hi_core_news_sm  # Hindi (if available)
```

### 6. Update Database

Add language-specific fact-checks to the database:

```python
from backend.models.database import FactCheck
from backend.database.setup_db import db

session = db.get_session()

fact_check = FactCheck(
    claim='Your claim in the new language',
    verdict='false',
    explanation='Explanation in the new language',
    source='source_name',
    source_url='https://example.com',
    language='hi',  # Language code
    keywords=[],
    embedding=[]
)

session.add(fact_check)
session.commit()
```

### 7. Test the New Language

Create a test script:

```python
from backend.utils.response_generator import response_generator

# Test the new language responses
response = response_generator.get_verdict_response(
    verdict='false',
    language='hi',  # Your language code
    explanation='यह एक परीक्षण व्याख्या है',
    confidence_score=0.9
)

print(response)
```

## Example: Complete Hindi Integration

Here's a complete example for adding Hindi:

### 1. Install Tesseract

```bash
sudo apt-get install tesseract-ocr-hin
```

### 2. Update .env

```env
TESSERACT_LANGS=eng+tam+hin
SUPPORTED_LANGUAGES=en,ta,hi
```

### 3. Add Hindi Templates

See the code example in step 2 above.

### 4. Test

```python
# Test text analysis
from backend.analyzers.text_analyzer import text_analyzer

text = "यह एक झूठी खबर है"
result = text_analyzer.analyze_text(text)
print(f"Detected language: {result['language']}")

# Test response
from backend.utils.response_generator import response_generator

response = response_generator.get_verdict_response(
    verdict='false',
    language='hi',
    explanation='यह दावा गलत है'
)
print(response)
```

## Translation Resources

For accurate translations of technical terms:

### Common Terms

| English | Hindi | Tamil | Telugu | Kannada | Malayalam |
|---------|-------|-------|---------|---------|-----------|
| False | झूठ | பொய் | అబద్ధం | ಸುಳ್ಳು | കള്ളം |
| Misleading | भ्रामक | தவறான | తప్పుదోవ పట్టించే | ತಪ್ಪು ದಾರಿ ಹಿಡಿಸುವ | തെറ്റിദ്ധരിപ്പിക്കുന്ന |
| Cannot Verify | सत्यापित नहीं कर सके | சரிபார்க்க முடியவில்லை | ధృవీకరించలేము | ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ | പരിശോധിക്കാൻ കഴിയില്ല |
| True | सच | உண்மை | నిజం | ನಿಜ | സത്യം |
| Source | स्रोत | ஆதாரம் | మూలం | ಮೂಲ | സ്രോതസ്സ് |

## Language-Specific Scrapers

To add scrapers for fact-checkers in your language:

```python
class HindiFactCheckerScraper(BaseScraper):
    """Scraper for Hindi fact-checking website."""
    
    def __init__(self):
        base_url = 'https://hindi-factchecker.com'
        super().__init__('Hindi Fact Checker', base_url)
    
    def scrape_article(self, url):
        # Implement scraping logic
        # Make sure to set language='hi' in the returned dict
        return {
            'claim': 'Claim in Hindi',
            'verdict': 'false',
            'explanation': 'Explanation in Hindi',
            'source': 'hindi_checker',
            'source_url': url,
            'language': 'hi'  # Important!
        }
```

## Testing Multilingual Support

Run comprehensive tests:

```bash
# Test all components with new language
python test_system.py

# Test via API
curl -X POST http://localhost:5000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"text": "यह एक परीक्षण संदेश है", "language": "hi"}'
```

## Community Contributions

When adding a new language:

1. Update this documentation
2. Add test cases
3. Provide sample data in the new language
4. Submit a pull request with:
   - Language code
   - Response templates
   - Sample fact-checks
   - Updated documentation

## Resources

- Tesseract Language Data: https://github.com/tesseract-ocr/tessdata
- SpaCy Models: https://spacy.io/models
- langdetect: https://pypi.org/project/langdetect/
- Google Translate API (for translations): https://cloud.google.com/translate

## Need Help?

If you need help adding a new language:
1. Open an issue on GitHub
2. Provide sample text in your language
3. Share any language-specific fact-checking resources
4. Join our community discussions
