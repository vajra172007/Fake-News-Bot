"""Vishvas News scraper - scrapes fact-checks from vishvasnews.com (English + Tamil)"""

import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.scrapers.fact_check_scrapers import BaseScraper


class VishvasNewsScraper(BaseScraper):
    """Scraper for Vishvas News (supports English and Tamil)."""
    
    def __init__(self):
        super().__init__(
            name="Vishvas News",
            base_url="https://www.vishvasnews.com"
        )
        
    def scrape(self, max_pages: int = 3, languages: List[str] = ['english', 'tamil']) -> List[Dict]:
        """
        Scrape fact-checks from Vishvas News in multiple languages.
        
        Args:
            max_pages: Number of pages to scrape per language
            languages: List of languages to scrape ('english', 'tamil', 'hindi')
            
        Returns:
            List of fact-check dictionaries
        """
        print(f"\n🔍 Starting Vishvas News scraper...")
        print(f"📄 Languages: {', '.join(languages)}")
        print(f"📄 Pages per language: {max_pages}")
        
        all_fact_checks = []
        
        for lang in languages:
            print(f"\n🌐 Scraping {lang.upper()} fact-checks...")
            
            lang_fact_checks = self._scrape_language(lang, max_pages)
            all_fact_checks.extend(lang_fact_checks)
            
            if len(all_fact_checks) >= self.max_articles:
                print(f"✓ Reached max articles limit ({self.max_articles})")
                break
        
        print(f"\n✓ Vishvas News scraping completed: {len(all_fact_checks)} fact-checks extracted")
        return all_fact_checks
    
    def _scrape_language(self, language: str, max_pages: int) -> List[Dict]:
        """Scrape fact-checks for a specific language."""
        fact_checks = []
        
        # Construct URL based on language
        if language == 'english':
            base_url = f"{self.base_url}/english/fact-check/"
            lang_code = 'en'
        elif language == 'tamil':
            base_url = f"{self.base_url}/tamil/fact-check/"
            lang_code = 'ta'
        elif language == 'hindi':
            base_url = f"{self.base_url}/fact-check/"
            lang_code = 'hi'
        else:
            return fact_checks
        
        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}page/{page}/"
            
            print(f"   📄 Page {page}: {url}")
            
            soup = self.fetch_page(url)
            if not soup:
                print(f"   ❌ Failed to fetch page {page}")
                continue
            
            # Find all article cards
            articles = soup.find_all('article')
            
            if not articles:
                print(f"   ⚠️  No articles found on page {page}")
                break
            
            print(f"   Found {len(articles)} articles")
            
            for article in articles:
                try:
                    fact_check = self._extract_article(article, lang_code)
                    if fact_check:
                        fact_checks.append(fact_check)
                        
                        if len(fact_checks) >= self.max_articles // len(['english', 'tamil']):
                            return fact_checks
                    
                except Exception as e:
                    print(f"   ⚠️  Error extracting article: {e}")
                    continue
            
            # Be nice to the server
            if page < max_pages:
                import time
                time.sleep(self.delay)
        
        return fact_checks
    
    def _extract_article(self, article, language_code: str) -> Optional[Dict]:
        """Extract fact-check data from an article element."""
        try:
            # Get article link
            title_elem = article.find('h2', class_='entry-title') or article.find('h3')
            if not title_elem:
                return None
            
            link = title_elem.find('a')
            if not link:
                return None
            
            article_url = link.get('href', '')
            title = self.clean_text(link.get_text())
            
            print(f"      📰 {title[:50]}...")
            
            # Fetch full article
            article_soup = self.fetch_page(article_url)
            if not article_soup:
                return None
            
            # Extract content
            content = article_soup.find('div', class_='entry-content')
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
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'Vishvas News',
                'source_url': article_url,
                'original_url': None,
                'published_date': published_date,
                'language': language_code,
                'source_type': 'scraped',
                'gemini_generated': False
            }
            
        except Exception as e:
            print(f"      ⚠️  Error in _extract_article: {e}")
            return None
    
    def _extract_claim(self, content, title: str) -> str:
        """Extract the claim being fact-checked."""
        # Vishvas News uses specific structure
        claim_section = content.find('h3', string=re.compile(r'(Claim|दावा|கூற்று)', re.IGNORECASE))
        
        if claim_section:
            # Get next paragraph after claim heading
            next_elem = claim_section.find_next_sibling('p')
            if next_elem:
                claim_text = self.clean_text(next_elem.get_text())
                if claim_text:
                    return claim_text[:500]
        
        # Look for claim indicators in paragraphs
        paragraphs = content.find_all('p', limit=5)
        
        for p in paragraphs:
            text = self.clean_text(p.get_text())
            
            if any(word in text.lower() for word in ['claim:', 'viral', 'दावा:', 'கூற்று:']):
                # Extract claim part
                for sep in ['claim:', 'दावा:', 'கூற்று:']:
                    if sep.lower() in text.lower():
                        parts = text.lower().split(sep.lower(), 1)
                        if len(parts) > 1:
                            claim = parts[1].strip()
                            return claim[:500]
        
        # Fallback to title
        return title[:200]
    
    def _extract_verdict(self, title: str, content) -> str:
        """Determine the verdict."""
        title_lower = title.lower()
        
        # English keywords
        if any(word in title_lower for word in ['false', 'fake', 'hoax', 'fabricated', 'morphed']):
            return 'false'
        elif any(word in title_lower for word in ['misleading', 'misrepresent', 'miscaptioned', 'out of context', 'partly']):
            return 'misleading'
        elif any(word in title_lower for word in ['true', 'correct', 'genuine']):
            return 'true'
        
        # Hindi keywords (झूठ = false, भ्रामक = misleading)
        if any(word in title_lower for word in ['झूठ', 'गलत', 'फर्जी']):
            return 'false'
        elif 'भ्रामक' in title_lower:
            return 'misleading'
        elif 'सही' in title_lower or 'सच' in title_lower:
            return 'true'
        
        # Tamil keywords (பொய் = false, தவறான = false/wrong)
        if any(word in title for word in ['பொய்', 'தவறான', 'போலி']):
            return 'false'
        elif 'தவறாக' in title:
            return 'misleading'
        elif 'உண்மை' in title:
            return 'true'
        
        # Look for verdict section in content
        verdict_section = content.find('h3', string=re.compile(r'(Fact Check|फैक्ट चेक|உண்மை சரிபார்ப்பு)', re.IGNORECASE))
        if verdict_section:
            next_text = verdict_section.find_next('p')
            if next_text:
                verdict_text = next_text.get_text().lower()
                if any(word in verdict_text for word in ['false', 'fake', 'झूठ', 'பொய்']):
                    return 'false'
                elif any(word in verdict_text for word in ['misleading', 'भ्रामक']):
                    return 'misleading'
                elif any(word in verdict_text for word in ['true', 'सही', 'உண்மை']):
                    return 'true'
        
        # Default
        return 'false'
    
    def _extract_explanation(self, content) -> str:
        """Extract the fact-check explanation."""
        # Look for fact check section
        fact_check_section = content.find('h3', string=re.compile(r'(Fact Check|फैक्ट चेक|உண்மை சரிபார்ப்பு)', re.IGNORECASE))
        
        explanation_parts = []
        
        if fact_check_section:
            # Get paragraphs after fact check heading
            current = fact_check_section.find_next_sibling()
            while current and len(explanation_parts) < 4:
                if current.name == 'p':
                    text = self.clean_text(current.get_text())
                    if text and len(text) > 30:
                        explanation_parts.append(text)
                current = current.find_next_sibling()
        
        if not explanation_parts:
            # Take paragraphs from middle of article
            paragraphs = content.find_all('p')
            for p in paragraphs[2:6]:
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
            time_elem = soup.find('time', class_='entry-date')
            if time_elem:
                date_str = time_elem.get('datetime', '')
                if date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
        except Exception as e:
            print(f"      ⚠️  Error parsing date: {e}")
        
        return None


def test_vishvas_scraper():
    """Test the Vishvas News scraper."""
    print("🧪 Testing Vishvas News Scraper\n")
    
    scraper = VishvasNewsScraper()
    
    # Test both English and Tamil
    fact_checks = scraper.scrape(max_pages=1, languages=['english', 'tamil'])
    
    print(f"\n📊 Results:")
    print(f"Total fact-checks: {len(fact_checks)}")
    
    # Show samples from different languages
    english_samples = [fc for fc in fact_checks if fc['language'] == 'en']
    tamil_samples = [fc for fc in fact_checks if fc['language'] == 'ta']
    
    if english_samples:
        print(f"\n📰 English Sample:")
        sample = english_samples[0]
        print(f"Claim: {sample['claim'][:100]}...")
        print(f"Verdict: {sample['verdict']}")
        print(f"Language: {sample['language']}")
    
    if tamil_samples:
        print(f"\n📰 Tamil Sample:")
        sample = tamil_samples[0]
        print(f"Claim: {sample['claim'][:100]}...")
        print(f"Verdict: {sample['verdict']}")
        print(f"Language: {sample['language']}")


if __name__ == "__main__":
    test_vishvas_scraper()
