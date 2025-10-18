"""Text analysis module using NLP for claim extraction and matching."""

import os
import re
import nltk
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
from langdetect import detect, LangDetectException
import torch
from dotenv import load_dotenv

load_dotenv()

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Try to import spacy (optional)
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("⚠️  SpaCy not available, using NLTK for all NLP tasks")


class TextAnalyzer:
    """Analyze text for fake news detection."""
    
    def __init__(self):
        """Initialize NLP models."""
        self.model_name = os.getenv('NLP_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.75))
        
        # Load sentence transformer for semantic similarity (CPU only)
        print(f"Loading NLP model: {self.model_name}...")
        # Force CPU to avoid CUDA initialization issues
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        self.sentence_model = SentenceTransformer(self.model_name, device='cpu')
        
        # Load spaCy for entity extraction (optional)
        self.nlp_en = None
        if SPACY_AVAILABLE:
            try:
                import spacy
                self.nlp_en = spacy.load('en_core_web_sm')
            except (OSError, ImportError):
                print("⚠️  English spaCy model not found. Using NLTK instead")
            
        # Stop words
        self.stop_words_en = set(nltk.corpus.stopwords.words('english'))
        
        print("✓ Text analyzer initialized")
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            lang = detect(text)
            # Map language codes
            lang_map = {
                'en': 'en',
                'ta': 'ta',
                'hi': 'hi',
                'te': 'te',
                'ml': 'ml',
                'kn': 'kn'
            }
            return lang_map.get(lang, 'en')
        except LangDetectException:
            return 'en'
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_keywords(self, text: str, language: str = 'en', top_n: int = 10) -> List[str]:
        """Extract important keywords from text."""
        text = self.clean_text(text)
        
        if language == 'en' and self.nlp_en and SPACY_AVAILABLE:
            # Use spaCy for English (if available)
            try:
                import spacy
                doc = self.nlp_en(text)
                # Extract named entities and important nouns
                keywords = []
                for ent in doc.ents:
                    keywords.append(ent.text.lower())
                for token in doc:
                    if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop:
                        keywords.append(token.lemma_.lower())
            except Exception:
                # Fallback to NLTK
                words = nltk.word_tokenize(text.lower())
                keywords = [w for w in words if len(w) > 3 and w.isalpha()]
        else:
            # Simple keyword extraction using NLTK
            words = nltk.word_tokenize(text.lower())
            keywords = [w for w in words if len(w) > 3 and w.isalpha()]
        
        # Get most frequent keywords
        from collections import Counter
        keyword_freq = Counter(keywords)
        return [kw for kw, _ in keyword_freq.most_common(top_n)]
    
    def extract_claims(self, text: str) -> List[str]:
        """Extract potential claims from text."""
        text = self.clean_text(text)
        
        # Split into sentences
        sentences = nltk.sent_tokenize(text)
        
        # Filter sentences that look like claims
        claims = []
        for sentence in sentences:
            # Look for declarative statements (not questions)
            if len(sentence.split()) >= 5 and not sentence.strip().endswith('?'):
                claims.append(sentence)
        
        return claims
    
    def compute_embedding(self, text: str) -> List[float]:
        """Compute sentence embedding for semantic search."""
        embedding = self.sentence_model.encode(text, convert_to_tensor=True)
        return embedding.cpu().tolist()
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts."""
        embedding1 = self.sentence_model.encode(text1, convert_to_tensor=True)
        embedding2 = self.sentence_model.encode(text2, convert_to_tensor=True)
        
        cosine_score = util.pytorch_cos_sim(embedding1, embedding2)
        return float(cosine_score[0][0])
    
    def find_matching_claims(self, query_text: str, fact_checks: List[Dict]) -> List[Tuple[Dict, float]]:
        """Find matching fact-checks for the query text."""
        query_embedding = self.sentence_model.encode(query_text, convert_to_tensor=True)
        
        matches = []
        for fact_check in fact_checks:
            claim = fact_check.get('claim', '')
            if not claim:
                continue
                
            claim_embedding = self.sentence_model.encode(claim, convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(query_embedding, claim_embedding)
            score = float(similarity[0][0])
            
            if score >= self.similarity_threshold:
                matches.append((fact_check, score))
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def analyze_text(self, text: str) -> Dict:
        """Complete analysis of text."""
        language = self.detect_language(text)
        cleaned_text = self.clean_text(text)
        keywords = self.extract_keywords(cleaned_text, language)
        claims = self.extract_claims(cleaned_text)
        embedding = self.compute_embedding(cleaned_text)
        
        return {
            'language': language,
            'cleaned_text': cleaned_text,
            'keywords': keywords,
            'claims': claims,
            'embedding': embedding,
            'original_length': len(text),
            'cleaned_length': len(cleaned_text)
        }


# Global instance
text_analyzer = TextAnalyzer()


if __name__ == "__main__":
    # Test the analyzer
    test_text = """
    Breaking News: A video claiming that the Prime Minister announced free electricity 
    for all citizens is going viral. The claim states that this will be implemented 
    from next month across all states.
    """
    
    print("Testing Text Analyzer...")
    print("-" * 50)
    
    result = text_analyzer.analyze_text(test_text)
    
    print(f"Language: {result['language']}")
    print(f"\nCleaned Text: {result['cleaned_text']}")
    print(f"\nKeywords: {', '.join(result['keywords'])}")
    print(f"\nExtracted Claims:")
    for i, claim in enumerate(result['claims'], 1):
        print(f"  {i}. {claim}")
    print(f"\nEmbedding dimension: {len(result['embedding'])}")
    
    # Test similarity
    text1 = "The Prime Minister announced free electricity"
    text2 = "PM declares no-cost power for citizens"
    similarity = text_analyzer.compute_similarity(text1, text2)
    print(f"\nSimilarity between related texts: {similarity:.4f}")
