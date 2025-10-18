"""WebQoof (The Quint) scraper - scrapes fact-checks from thequint.com/news/webqoof"""

import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.scrapers.fact_check_scrapers import BaseScraper


class WebQoofScraper(BaseScraper):
    """Scraper for WebQoof (The Quint's fact-checking initiative)."""
    
    def __init__(self):
        super().__init__(
            name="WebQoof",
            base_url="https://www.thequint.com"
        )
        self.fact_check_url = f"{self.base_url}/news/webqoof"
        
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """
        Scrape fact-checks from WebQoof.
        
        Args:
            max_pages: Number of pages to scrape
            
        Returns:
            List of fact-check dictionaries
        """
        print(f"\n🔍 Starting WebQoof scraper...")
        print(f"📄 Scraping up to {max_pages} pages")
        
        all_fact_checks = []
        
        for page in range(1, max_pages + 1):
            if page == 1:
                url = self.fact_check_url
            else:
                url = f"{self.fact_check_url}?page={page}"
            
            print(f"📄 Scraping page {page}: {url}")
            
            soup = self.fetch_page(url)
            if not soup:
                print(f"❌ Failed to fetch page {page}")
                continue
            
            # Find all article cards
            articles = soup.find_all('div', class_='story-card')
            if not articles:
                articles = soup.find_all('article')
            
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
        
        print(f"✓ WebQoof scraping completed: {len(all_fact_checks)} fact-checks extracted")
        return all_fact_checks
    
    def _extract_article(self, article) -> Optional[Dict]:
        """Extract fact-check data from an article element."""
        try:
            # Get article link
            link = article.find('a', href=True)
            if not link:
                return None
            
            article_url = link.get('href', '')
            if not article_url.startswith('http'):
                article_url = self.base_url + article_url
            
            # Get title
            title_elem = article.find('h2') or article.find('h3')
            if not title_elem:
                title_elem = link
            
            title = self.clean_text(title_elem.get_text())
            
            print(f"   📰 Processing: {title[:60]}...")
            
            # Fetch full article
            article_soup = self.fetch_page(article_url)
            if not article_soup:
                return None
            
            # Extract content
            content = article_soup.find('div', class_='story-details')
            if not content:
                content = article_soup.find('article')
            
            if not content:
                return None
            
            # Extract claim
            claim = self._extract_claim(content, title)
            
            # Extract verdict
            verdict = self._extract_verdict(title, content)
            
            # Extract explanation
            explanation = self._extract_explanation(content)
            
            # Extract date
            published_date = self._extract_date(article_soup)
            
            # Detect language
            language = self._detect_language(claim + " " + explanation)
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'WebQoof',
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
        # Look for WebQoof's specific structure
        claim_indicators = [
            'claim:',
            'the claim:',
            'viral post',
            'viral video',
            'a video',
            'a post',
            'an image',
            'it is being claimed'
        ]
        
        paragraphs = content.find_all('p', limit=6)
        
        for p in paragraphs:
            text = self.clean_text(p.get_text())
            
            for indicator in claim_indicators:
                if indicator in text.lower():
                    parts = text.split(indicator, 1)
                    if len(parts) > 1:
                        claim = parts[1].strip()
                        claim = re.sub(r'^[:\s\-]+', '', claim)
                        return claim[:500]
        
        # Look for highlighted text
        highlight = content.find('strong') or content.find('b')
        if highlight:
            claim_text = self.clean_text(highlight.get_text())
            if claim_text and len(claim_text) > 20:
                return claim_text[:500]
        
        # Fallback to title
        return title[:200]
    
    def _extract_verdict(self, title: str, content) -> str:
        """Determine the verdict."""
        title_lower = title.lower()
        
        # WebQoof uses specific verdict labels
        if any(word in title_lower for word in ['false', 'fake', 'hoax', 'fabricated', 'morphed']):
            return 'false'
        elif any(word in title_lower for word in ['misleading', 'misrepresent', 'miscaptioned', 'out of context', 'partly']):
            return 'misleading'
        elif any(word in title_lower for word in ['true', 'correct', 'genuine']):
            return 'true'
        elif any(word in title_lower for word in ['unverified', 'unclear']):
            return 'unverified'
        
        # Look for verdict in content
        verdict_text = content.get_text().lower()
        if 'verdict:' in verdict_text or 'the truth:' in verdict_text:
            if 'false' in verdict_text or 'fake' in verdict_text:
                return 'false'
            elif 'misleading' in verdict_text:
                return 'misleading'
        
        # Default
        return 'false'
    
    def _extract_explanation(self, content) -> str:
        """Extract the fact-check explanation."""
        paragraphs = content.find_all('p')
        
        explanation_parts = []
        
        # Look for explanation sections
        for p in paragraphs[1:6]:
            text = self.clean_text(p.get_text())
            if text and len(text) > 30:
                explanation_parts.append(text)
        
        explanation = ' '.join(explanation_parts)
        return explanation[:1000]
    
    def _extract_date(self, soup) -> Optional[datetime]:
        """Extract published date."""
        try:
            # Meta tags
            date_meta = soup.find('meta', property='article:published_time')
            if date_meta:
                date_str = date_meta.get('content', '')
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Time element
            time_elem = soup.find('time')
            if time_elem:
                date_str = time_elem.get('datetime', '')
                if date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
        except Exception as e:
            print(f"⚠️  Error parsing date: {e}")
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        if not text:
            return 'en'
        
        ascii_count = sum(1 for c in text if ord(c) < 128)
        total = len(text)
        
        if total == 0:
            return 'en'
        
        return 'en' if (ascii_count / total) > 0.8 else 'hi'


def test_webqoof_scraper():
    """Test the WebQoof scraper."""
    print("🧪 Testing WebQoof Scraper\n")
    
    scraper = WebQoofScraper()
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


if __name__ == "__main__":
    test_webqoof_scraper()
