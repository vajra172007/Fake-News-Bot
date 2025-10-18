"""PIB India Fact Check scraper - scrapes from factcheck.pib.gov.in"""

import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.scrapers.fact_check_scrapers import BaseScraper


class PIBFactCheckScraper(BaseScraper):
    """Scraper for PIB India Fact Check Unit."""
    
    def __init__(self):
        super().__init__(
            name="PIB Fact Check",
            base_url="https://factcheck.pib.gov.in"
        )
        
    def scrape(self, max_pages: int = 5) -> List[Dict]:
        """
        Scrape fact-checks from PIB Fact Check.
        
        Args:
            max_pages: Number of pages to scrape
            
        Returns:
            List of fact-check dictionaries
        """
        print(f"\n🔍 Starting PIB Fact Check scraper...")
        print(f"📄 Scraping up to {max_pages} pages")
        
        all_fact_checks = []
        
        for page in range(0, max_pages):
            url = f"{self.base_url}/index.aspx?PageNo={page}"
            
            print(f"📄 Scraping page {page + 1}: {url}")
            
            soup = self.fetch_page(url)
            if not soup:
                print(f"❌ Failed to fetch page {page + 1}")
                continue
            
            # Find all fact-check cards
            fact_check_divs = soup.find_all('div', class_='col-md-4')
            
            if not fact_check_divs:
                print(f"⚠️  No fact-checks found on page {page + 1}")
                break
            
            print(f"   Found {len(fact_check_divs)} fact-checks")
            
            for div in fact_check_divs:
                try:
                    fact_check = self._extract_fact_check(div)
                    if fact_check:
                        all_fact_checks.append(fact_check)
                        
                        # Limit total articles
                        if len(all_fact_checks) >= self.max_articles:
                            print(f"✓ Reached max articles limit ({self.max_articles})")
                            return all_fact_checks
                    
                except Exception as e:
                    print(f"⚠️  Error extracting fact-check: {e}")
                    continue
            
            # Be nice to the server
            if page < max_pages - 1:
                import time
                time.sleep(self.delay)
        
        print(f"✓ PIB Fact Check scraping completed: {len(all_fact_checks)} fact-checks extracted")
        return all_fact_checks
    
    def _extract_fact_check(self, div) -> Optional[Dict]:
        """Extract fact-check data from a card element."""
        try:
            # Get the link
            link = div.find('a')
            if not link:
                return None
            
            article_url = self.base_url + "/" + link.get('href', '').lstrip('/')
            
            # Get image alt text (contains the claim)
            img = div.find('img')
            if not img:
                return None
            
            claim_text = img.get('alt', '')
            if not claim_text or 'Fake' in claim_text:
                claim_text = self.clean_text(claim_text)
            
            print(f"   📰 Processing PIB fact-check: {claim_text[:60]}...")
            
            # Fetch full article for details
            article_soup = self.fetch_page(article_url)
            if not article_soup:
                return None
            
            # Extract detailed information from article
            content = article_soup.find('div', class_='innercontent')
            if not content:
                content = article_soup.find('div', class_='content')
            
            # Extract claim and explanation
            claim = self._extract_claim(content, claim_text)
            explanation = self._extract_explanation(content)
            
            # PIB fact checks are always about false claims
            verdict = 'false'
            
            # Extract date
            published_date = self._extract_date(article_soup)
            
            # Language detection
            language = self._detect_language(claim + " " + explanation)
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'PIB Fact Check',
                'source_url': article_url,
                'original_url': None,
                'published_date': published_date,
                'language': language,
                'source_type': 'scraped',
                'gemini_generated': False
            }
            
        except Exception as e:
            print(f"⚠️  Error in _extract_fact_check: {e}")
            return None
    
    def _extract_claim(self, content, fallback_claim: str) -> str:
        """Extract the claim being fact-checked."""
        if not content:
            return fallback_claim[:200]
        
        # Look for "Claim:" or similar patterns
        paragraphs = content.find_all('p')
        
        for p in paragraphs[:3]:
            text = self.clean_text(p.get_text())
            
            if 'claim' in text.lower() or 'viral' in text.lower():
                # Extract the claim part
                text = re.sub(r'^(Claim:|The Claim:)\s*', '', text, flags=re.IGNORECASE)
                return text[:500]
        
        # Look for bold text (often contains the claim)
        bold = content.find('strong')
        if bold:
            bold_text = self.clean_text(bold.get_text())
            if bold_text and len(bold_text) > 20:
                return bold_text[:500]
        
        # Fallback
        return fallback_claim[:200]
    
    def _extract_explanation(self, content) -> str:
        """Extract the fact-check explanation."""
        if not content:
            return "This claim has been verified as false by PIB India Fact Check Unit."
        
        # Get all paragraphs
        paragraphs = content.find_all('p')
        
        explanation_parts = []
        
        # Look for "Fact:" or take paragraphs after claim
        found_fact = False
        for p in paragraphs:
            text = self.clean_text(p.get_text())
            
            if 'fact check' in text.lower() or 'fact:' in text.lower():
                found_fact = True
                text = re.sub(r'^(Fact:|Fact Check:)\s*', '', text, flags=re.IGNORECASE)
            
            if found_fact and text and len(text) > 20:
                explanation_parts.append(text)
            
            if len(explanation_parts) >= 3:
                break
        
        if not explanation_parts:
            # Take first few paragraphs
            for p in paragraphs[:4]:
                text = self.clean_text(p.get_text())
                if text and len(text) > 20:
                    explanation_parts.append(text)
        
        explanation = ' '.join(explanation_parts)
        return explanation[:1000] if explanation else "This claim has been verified as false by PIB India Fact Check Unit."
    
    def _extract_date(self, soup) -> Optional[datetime]:
        """Extract published date from article."""
        try:
            # Look for date patterns in text
            date_text = soup.find('span', class_='date')
            if not date_text:
                date_text = soup.find('div', class_='date')
            
            if date_text:
                date_str = self.clean_text(date_text.get_text())
                # Try to parse date (PIB uses formats like "25-Dec-2023")
                try:
                    return datetime.strptime(date_str, "%d-%b-%Y")
                except:
                    pass
            
        except Exception as e:
            print(f"⚠️  Error parsing date: {e}")
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        if not text:
            return 'en'
        
        # Count ASCII vs non-ASCII characters
        ascii_count = sum(1 for c in text if ord(c) < 128)
        total = len(text)
        
        if total == 0:
            return 'en'
        
        ascii_ratio = ascii_count / total
        
        # If mostly ASCII, it's English
        return 'en' if ascii_ratio > 0.8 else 'hi'


def test_pib_scraper():
    """Test the PIB Fact Check scraper."""
    print("🧪 Testing PIB Fact Check Scraper\n")
    
    scraper = PIBFactCheckScraper()
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
    test_pib_scraper()
