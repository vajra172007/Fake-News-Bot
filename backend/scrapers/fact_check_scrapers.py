"""Base scraper class for fact-checking websites."""

import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()


class BaseScraper(ABC):
    """Abstract base class for fact-checker scrapers."""
    
    def __init__(self, name: str, base_url: str):
        """Initialize the scraper."""
        self.name = name
        self.base_url = base_url
        self.user_agent = os.getenv('USER_AGENT',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        self.delay = int(os.getenv('SCRAPER_DELAY', 2))
        self.max_articles = int(os.getenv('MAX_ARTICLES_PER_SCRAPE', 50))
        
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        # Override in subclass with specific date format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None
    
    @abstractmethod
    def scrape_article_list(self) -> List[str]:
        """Scrape list of article URLs."""
        pass
    
    @abstractmethod
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single article."""
        pass
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all articles."""
        print(f"\n🔍 Starting scraper: {self.name}")
        print(f"📡 Base URL: {self.base_url}")
        
        # Get article URLs
        article_urls = self.scrape_article_list()
        print(f"📄 Found {len(article_urls)} articles")
        
        # Limit number of articles
        article_urls = article_urls[:self.max_articles]
        
        # Scrape each article
        articles = []
        for i, url in enumerate(article_urls, 1):
            print(f"  [{i}/{len(article_urls)}] Scraping: {url}")
            article = self.scrape_article(url)
            if article:
                articles.append(article)
            
            # Be polite: delay between requests
            if i < len(article_urls):
                time.sleep(self.delay)
        
        print(f"✓ Successfully scraped {len(articles)} articles from {self.name}")
        return articles


class AltNewsScraper(BaseScraper):
    """Scraper for Alt News (https://www.altnews.in)."""
    
    def __init__(self):
        base_url = os.getenv('ALTNEWS_URL', 'https://www.altnews.in')
        super().__init__('Alt News', base_url)
    
    def scrape_article_list(self) -> List[str]:
        """Scrape list of fact-check articles."""
        urls = []
        
        # Try to scrape the fact-check category page
        category_url = f"{self.base_url}/category/fact-check/"
        soup = self.fetch_page(category_url)
        
        if not soup:
            return urls
        
        # Find article links (this selector may need adjustment based on actual site structure)
        for article in soup.find_all('article', class_='post'):
            link = article.find('a', href=True)
            if link and link['href']:
                urls.append(link['href'])
        
        return urls
    
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single Alt News article."""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        try:
            # Extract title
            title_tag = soup.find('h1', class_='entry-title') or soup.find('h1')
            title = self.clean_text(title_tag.get_text()) if title_tag else ""
            
            # Extract claim (usually in the beginning or in specific tags)
            claim = title  # Simplified
            
            # Extract verdict
            verdict = 'false'  # Default for Alt News fact-checks
            
            # Extract content
            content_div = soup.find('div', class_='entry-content') or soup.find('article')
            explanation = ""
            if content_div:
                # Get first few paragraphs
                paragraphs = content_div.find_all('p')[:3]
                explanation = ' '.join([self.clean_text(p.get_text()) for p in paragraphs])
            
            # Extract date
            date_tag = soup.find('time', class_='entry-date')
            date_str = date_tag.get('datetime', '') if date_tag else ""
            published_date = self.parse_date(date_str) if date_str else datetime.now()
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'altnews',
                'source_url': url,
                'published_date': published_date,
                'scraped_date': datetime.now()
            }
        except Exception as e:
            print(f"❌ Error parsing article {url}: {e}")
            return None


class BoomLiveScraper(BaseScraper):
    """Scraper for Boom Live (https://www.boomlive.in)."""
    
    def __init__(self):
        base_url = os.getenv('BOOMLIVE_URL', 'https://www.boomlive.in')
        super().__init__('Boom Live', base_url)
    
    def scrape_article_list(self) -> List[str]:
        """Scrape list of fact-check articles."""
        urls = []
        
        # Try to scrape the fact-check section
        fact_check_url = f"{self.base_url}/fact-check"
        soup = self.fetch_page(fact_check_url)
        
        if not soup:
            return urls
        
        # Find article links using the correct selectors for BoomLive
        # Try multiple selectors as BoomLive has different article containers
        selectors = [
            ('div', 'boom-item'),
            ('div', 'boom-item3'),
        ]
        
        for tag, class_name in selectors:
            for article in soup.find_all(tag, class_=class_name):
                # Look for links in the article - try multiple patterns
                link = (article.find('a', class_='img_link') or 
                       article.find('a', class_='heading_link') or 
                       article.find('a', href=True))
                
                if link and link.get('href'):
                    href = link['href']
                    # Ensure proper URL formation
                    if href.startswith('/'):
                        full_url = self.base_url + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Only add fact-check URLs
                    if '/fact-check/' in full_url:
                        urls.append(full_url)
        
        return urls
    
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single Boom Live article."""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        try:
            # Extract title
            title_tag = soup.find('h1') or soup.find('h1', class_='headline')
            title = self.clean_text(title_tag.get_text()) if title_tag else ""
            
            # Extract claim
            claim_tag = soup.find('div', class_='claim') or soup.find('strong')
            claim = self.clean_text(claim_tag.get_text()) if claim_tag else title
            
            # Extract verdict
            verdict = 'false'  # Default
            
            # Extract explanation
            content_div = soup.find('div', class_='article-content') or soup.find('article')
            explanation = ""
            if content_div:
                paragraphs = content_div.find_all('p')[:3]
                explanation = ' '.join([self.clean_text(p.get_text()) for p in paragraphs])
            
            # Extract date
            published_date = datetime.now()
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'boomlive',
                'source_url': url,
                'published_date': published_date,
                'scraped_date': datetime.now()
            }
        except Exception as e:
            print(f"❌ Error parsing article {url}: {e}")
            return None


class PIBFactCheckScraper(BaseScraper):
    """Scraper for PIB Fact Check (https://factcheck.pib.gov.in)."""
    
    def __init__(self):
        # Note: PIB doesn't seem to have a dedicated factcheck subdomain
        # Using main PIB website with press releases
        base_url = os.getenv('PIB_FACTCHECK_URL', 'https://www.pib.gov.in')
        super().__init__('PIB Fact Check', base_url)
    
    def scrape_article_list(self) -> List[str]:
        """Scrape list of fact-check articles."""
        urls = []
        
        # PIB doesn't have a dedicated factcheck section that's easily accessible
        # For now, return empty list to avoid 404 errors
        # This can be updated when a proper PIB factcheck URL is found
        print(f"⚠️  {self.name}: PIB factcheck URL needs to be configured properly")
        return urls
    
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single PIB Fact Check article."""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        try:
            # Extract title
            title_tag = soup.find('h1', class_='page-title') or soup.find('h1')
            title = self.clean_text(title_tag.get_text()) if title_tag else ""
            
            # PIB fact checks usually mark false claims
            claim = title
            verdict = 'false'
            
            # Extract content
            content_div = soup.find('div', class_='field-item')
            explanation = ""
            if content_div:
                paragraphs = content_div.find_all('p')[:3]
                explanation = ' '.join([self.clean_text(p.get_text()) for p in paragraphs])
            
            # Extract date
            date_tag = soup.find('span', class_='date-display-single')
            published_date = datetime.now()
            
            return {
                'claim': claim,
                'verdict': verdict,
                'explanation': explanation,
                'source': 'pib',
                'source_url': url,
                'published_date': published_date,
                'scraped_date': datetime.now()
            }
        except Exception as e:
            print(f"❌ Error parsing article {url}: {e}")
            return None


if __name__ == "__main__":
    print("Testing Scrapers...")
    print("=" * 60)
    
    # Test Alt News scraper
    print("\n1. Testing Alt News Scraper")
    altnews = AltNewsScraper()
    urls = altnews.scrape_article_list()
    print(f"   Found {len(urls)} article URLs")
    if urls:
        print(f"   Sample URL: {urls[0]}")
    
    # Test Boom Live scraper
    print("\n2. Testing Boom Live Scraper")
    boom = BoomLiveScraper()
    urls = boom.scrape_article_list()
    print(f"   Found {len(urls)} article URLs")
    if urls:
        print(f"   Sample URL: {urls[0]}")
    
    # Test PIB scraper
    print("\n3. Testing PIB Fact Check Scraper")
    pib = PIBFactCheckScraper()
    urls = pib.scrape_article_list()
    print(f"   Found {len(urls)} article URLs")
    if urls:
        print(f"   Sample URL: {urls[0]}")
    
    print("\n✓ Scraper tests complete")


class WebQoofScraper(BaseScraper):
    """Adapter for WebQoof scraper to work with BaseScraper interface."""
    
    def __init__(self):
        super().__init__(name="WebQoof", base_url="https://www.thequint.com")
        # Import and create the original scraper
        from sources.webqoof_scraper import WebQoofScraper as OriginalWebQoof
        self._scraper = OriginalWebQoof()
        self._fact_checks = []
        
    def scrape_article_list(self) -> List[str]:
        """Get fact-checks using the original scraper and return URLs."""
        # Use the original scraper to get all fact-checks
        self._fact_checks = self._scraper.scrape(max_pages=3)
        # Return the URLs for compatibility
        return [fc.get('source_url', '') for fc in self._fact_checks]
        
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Return the pre-scraped fact-check data."""
        # Find the fact-check that matches this URL
        for fc in self._fact_checks:
            if fc.get('source_url') == url:
                return fc
        return None


class VishvasNewsScraper(BaseScraper):
    """Adapter for Vishvas News scraper to work with BaseScraper interface."""
    
    def __init__(self, languages: List[str] = None):
        super().__init__(name="Vishvas News", base_url="https://www.vishvasnews.com")
        # Import and create the original scraper
        from sources.vishvas_scraper import VishvasNewsScraper as OriginalVishvas
        self._scraper = OriginalVishvas()
        self._fact_checks = []
        self._languages = languages or ["english"]
        
    def scrape_article_list(self) -> List[str]:
        """Get fact-checks using the original scraper and return URLs."""
        # Use the original scraper to get all fact-checks
        self._fact_checks = self._scraper.scrape(max_pages=3, languages=self._languages)
        # Return the URLs for compatibility
        return [fc.get('source_url', '') for fc in self._fact_checks]
        
    def scrape_article(self, url: str) -> Optional[Dict]:
        """Return the pre-scraped fact-check data."""
        # Find the fact-check that matches this URL
        for fc in self._fact_checks:
            if fc.get('source_url') == url:
                return fc
        return None
