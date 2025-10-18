"""AltNews scraper - scrapes fact-checks from altnews.in"""

import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.scrapers.fact_check_scrapers import BaseScraper


class AltNewsScraper(BaseScraper):
    """Scraper for AltNews fact-checking website."""
    
    def __init__(self):
        super().__init__(
            name="AltNews",
            base_url="https://www.altnews.in"
        )
        self.fact_check_url = f"{self.base_url}/category/fact-check/"
        
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """
        Scrape fact-checks from AltNews.
        
        Args:
            max_pages: Number of pages to scrape
            
        Returns:
            List of fact-check dictionaries
        """
        print(f"\n🔍 Starting AltNews scraper...")
        print(f"📄 Scraping up to {max_pages} pages")
        
        all_fact_checks = []
        
        for page in range(1, max_pages + 1):
            if page == 1:
                url = self.fact_check_url
            else:
                url = f"{self.fact_check_url}page/{page}/"
            
            print(f"📄 Scraping page {page}: {url}")
            
            soup = self.fetch_page(url)
            if not soup:
                print(f"❌ Failed to fetch page {page}")
                continue
            
            # Find all article links
            articles = soup.find_all('article', class_='post')
            
            if not articles:
                print(f"⚠️  No articles found on page {page}")
                break
            
            print(f"   Found {len(articles)} articles")
            
            for article in articles:
                try:
                    fact_check = self._extract_article(article)
                    if fact_check:
                        all_fact_checks.append(fact_check)
                        
                        # Limit total articles
                        if len(all_fact_checks) >= self.max_articles:
                            print(f"✓ Reached max articles limit ({self.max_articles})")
                            return all_fact_checks
                    
                except Exception as e:
                    print(f"⚠️  Error extracting article: {e}")
                    continue
            
            # Be nice to the server
            if page < max_pages:
                import time
                time.sleep(self.delay)
        
        print(f"✓ AltNews scraping completed: {len(all_fact_checks)} fact-checks extracted")
        return all_fact_checks
    
    def _extract_article(self, article) -> Optional[Dict]:
        """Extract fact-check data from an article element."""
        try:
            # Get article link
            title_elem = article.find('h2', class_='entry-title')
            if not title_elem or not title_elem.find('a'):
                return None
            
            link = title_elem.find('a')
            article_url = link.get('href', '')
            title = self.clean_text(link.get_text())
            
            if not article_url:
                return None
            
            print(f"   📰 Processing: {title[:60]}...")
            
            # Fetch full article for details
            article_soup = self.fetch_page(article_url)
            if not article_soup:
                return None
            
            # Extract claim and verdict
            content = article_soup.find('div', class_='entry-content')
            if not content:
                return None
            
            # Try to extract the claim
            claim = self._extract_claim(content, title)
            
            # Extract verdict
            verdict = self._extract_verdict(title, content)
            
            # Extract explanation
            explanation = self._extract_explanation(content)
            
            # Extract published date
            published_date = self._extract_date(article_soup)
            
            # Detect language (simple heuristic)
            language = self._detect_language(claim + " " + explanation)
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'AltNews',
                'source_url': article_url,
                'original_url': None,
                'published_date': published_date,
                'language': language,
                'source_type': 'scraped',
                'gemini_generated': False
            }
            
        except Exception as e:
            print(f"⚠️  Error in _extract_article: {e}")
            return None
    
    def _extract_claim(self, content, title: str) -> str:
        """Extract the claim being fact-checked."""
        # Look for common claim indicators
        claim_indicators = [
            'Claim:',
            'The claim:',
            'A viral',
            'A video',
            'A post',
            'An image',
            'It is claimed',
            'It was claimed'
        ]
        
        # Check first few paragraphs
        paragraphs = content.find_all('p', limit=5)
        
        for p in paragraphs:
            text = self.clean_text(p.get_text())
            
            for indicator in claim_indicators:
                if indicator.lower() in text.lower():
                    # Extract the claim part
                    parts = text.split(indicator, 1)
                    if len(parts) > 1:
                        claim = parts[1].strip()
                        # Clean up
                        claim = re.sub(r'^[:\s\-]+', '', claim)
                        return claim[:500]  # Limit length
        
        # Fallback: use title
        return title[:200]
    
    def _extract_verdict(self, title: str, content) -> str:
        """Determine the verdict from title or content."""
        title_lower = title.lower()
        
        # Check title for verdict keywords
        if any(word in title_lower for word in ['false', 'fake', 'hoax', 'fabricated', 'morphed']):
            return 'false'
        elif any(word in title_lower for word in ['misleading', 'misrepresent', 'miscaptioned', 'out of context']):
            return 'misleading'
        elif any(word in title_lower for word in ['true', 'correct', 'genuine', 'real']):
            return 'true'
        elif any(word in title_lower for word in ['unverified', 'unclear', 'inconclusive']):
            return 'unverified'
        
        # Default to false for AltNews (most debunk false claims)
        return 'false'
    
    def _extract_explanation(self, content) -> str:
        """Extract the fact-check explanation."""
        # Get all paragraphs
        paragraphs = content.find_all('p')
        
        explanation_parts = []
        
        # Skip first paragraph (usually the claim), take next few
        for p in paragraphs[1:6]:  # Get up to 5 paragraphs
            text = self.clean_text(p.get_text())
            if text and len(text) > 20:  # Skip very short paragraphs
                explanation_parts.append(text)
        
        explanation = ' '.join(explanation_parts)
        return explanation[:1000]  # Limit length
    
    def _extract_date(self, soup) -> Optional[datetime]:
        """Extract published date from article."""
        try:
            # Look for date in meta tags
            date_meta = soup.find('meta', property='article:published_time')
            if date_meta:
                date_str = date_meta.get('content', '')
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Look for time element
            time_elem = soup.find('time', class_='entry-date')
            if time_elem:
                date_str = time_elem.get('datetime', '')
                if date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
        except Exception as e:
            print(f"⚠️  Error parsing date: {e}")
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection (English or Hindi/Tamil)."""
        # Count ASCII vs non-ASCII characters
        ascii_count = sum(1 for c in text if ord(c) < 128)
        total = len(text)
        
        if total == 0:
            return 'en'
        
        ascii_ratio = ascii_count / total
        
        # If mostly ASCII, it's English
        if ascii_ratio > 0.8:
            return 'en'
        else:
            # Could be Hindi, Tamil, etc.
            # Check for specific Unicode ranges
            if any('\u0b80' <= c <= '\u0bff' for c in text):  # Tamil
                return 'ta'
            elif any('\u0900' <= c <= '\u097f' for c in text):  # Hindi
                return 'hi'
            else:
                return 'hi'  # Default to Hindi for Devanagari


def test_altnews_scraper():
    """Test the AltNews scraper."""
    print("🧪 Testing AltNews Scraper\n")
    
    scraper = AltNewsScraper()
    fact_checks = scraper.scrape(max_pages=1)
    
    print(f"\n📊 Results:")
    print(f"Total fact-checks: {len(fact_checks)}")
    
    if fact_checks:
        print(f"\n📰 Sample fact-check:")
        sample = fact_checks[0]
        print(f"Claim: {sample['claim'][:100]}...")
        print(f"Verdict: {sample['verdict']}")
        print(f"Source: {sample['source']}")
        print(f"URL: {sample['source_url']}")
        print(f"Language: {sample['language']}")


if __name__ == "__main__":
    test_altnews_scraper()
