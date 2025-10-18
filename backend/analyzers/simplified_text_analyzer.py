"""Simple text analyzer fallback without heavy models."""

import os
import re
import nltk
from typing import List, Dict, Tuple, Optional
from langdetect import detect, LangDetectException
from collections import Counter
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
    
try:
    from nltk.corpus import stopwords
    STOPWORDS_EN = set(stopwords.words('english'))
except LookupError:
    STOPWORDS_EN = set()

class SimplifiedTextAnalyzer:
    """Simplified text analyzer using keyword matching instead of semantic similarity."""
    
    def __init__(self):
        """Initialize with basic NLP tools."""
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.75))
        print("✓ Simplified text analyzer initialized (using keyword matching)")
        
    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            return detect(text)
        except LangDetectException:
            return 'en'  # Default to English
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.lower().strip()
    
    def extract_keywords(self, text: str, language: str = 'en', top_n: int = 10) -> List[str]:
        """Extract important keywords from text."""
        text = self.clean_text(text)
        words = nltk.word_tokenize(text.lower())
        
        # Filter out stopwords and short words
        keywords = [w for w in words if len(w) > 3 and w.isalpha() and w not in STOPWORDS_EN]
        
        # Get most frequent keywords
        keyword_freq = Counter(keywords)
        return [kw for kw, _ in keyword_freq.most_common(top_n)]
    
    def compute_keyword_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity based on common keywords."""
        keywords1 = set(self.extract_keywords(text1, top_n=20))
        keywords2 = set(self.extract_keywords(text2, top_n=20))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        return intersection / union if union > 0 else 0.0
    
    def find_matching_claims(self, query_text: str, fact_checks: List[Dict]) -> List[Tuple[Dict, float]]:
        """Find matching fact-checks using keyword similarity."""
        query_keywords = set(self.extract_keywords(query_text, top_n=20))
        
        matches = []
        for fact_check in fact_checks:
            claim = fact_check.get('claim', '')
            if not claim:
                continue
                
            # Calculate keyword similarity
            score = self.compute_keyword_similarity(query_text, claim)
            
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
        
        return {
            'language': language,
            'cleaned_text': cleaned_text,
            'keywords': keywords,
            'original_length': len(text),
            'cleaned_length': len(cleaned_text)
        }

# Create instance
simplified_text_analyzer = SimplifiedTextAnalyzer()