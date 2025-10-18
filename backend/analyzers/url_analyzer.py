"""URL analysis module for web scraping and domain verification."""

import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()


class URLAnalyzer:
    """Analyze URLs and web content for fake news detection."""
    
    def __init__(self):
        """Initialize URL analyzer."""
        self.timeout = int(os.getenv('URL_TIMEOUT', 10))
        self.user_agent = os.getenv('USER_AGENT', 
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.max_scrape_depth = int(os.getenv('MAX_SCRAPE_DEPTH', 1))
        
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        print("✓ URL analyzer initialized")
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract all URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www.
            domain = domain.replace('www.', '')
            return domain
        except:
            return ""
    
    def fetch_webpage(self, url: str) -> Optional[Dict]:
        """Fetch and parse webpage content."""
        if not self.is_valid_url(url):
            return None
        
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=True)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title = title.get_text().strip() if title else ""
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '').strip() if meta_desc else ""
            
            # Extract main text content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract all links
            links = []
            for link in soup.find_all('a', href=True):
                links.append(link['href'])
            
            return {
                'url': url,
                'domain': self.extract_domain(url),
                'title': title,
                'description': description,
                'text': text[:5000],  # Limit text length
                'links': links[:50],  # Limit number of links
                'status_code': response.status_code
            }
            
        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout fetching URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching URL {url}: {e}")
            return None
    
    def check_domain_reliability(self, domain: str, unreliable_domains: List[Dict]) -> Dict:
        """Check if domain is in the unreliable list."""
        domain = domain.lower().replace('www.', '')
        
        for unreliable in unreliable_domains:
            unreliable_domain = unreliable.get('domain', '').lower()
            if domain == unreliable_domain or domain.endswith('.' + unreliable_domain):
                return {
                    'is_unreliable': True,
                    'category': unreliable.get('category', 'unknown'),
                    'reason': unreliable.get('reason', '')
                }
        
        return {
            'is_unreliable': False,
            'category': None,
            'reason': None
        }
    
    def analyze_url_structure(self, url: str) -> Dict:
        """Analyze URL structure for suspicious patterns."""
        suspicious_indicators = {
            'has_ip_address': bool(re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url)),
            'excessive_subdomains': len(urlparse(url).netloc.split('.')) > 4,
            'suspicious_tld': any(tld in url for tld in ['.tk', '.ml', '.ga', '.cf', '.gq']),
            'url_shortener': any(short in url for short in ['bit.ly', 'tinyurl', 't.co', 'goo.gl']),
            'has_suspicious_words': any(word in url.lower() for word in ['free', 'click', 'prize', 'winner'])
        }
        
        suspicion_score = sum(suspicious_indicators.values())
        
        return {
            'indicators': suspicious_indicators,
            'suspicion_score': suspicion_score,
            'is_suspicious': suspicion_score >= 2
        }
    
    def analyze_url(self, url: str, unreliable_domains: List[Dict] = None) -> Dict:
        """Complete analysis of a URL."""
        if not self.is_valid_url(url):
            return {
                'valid': False,
                'error': 'Invalid URL format'
            }
        
        domain = self.extract_domain(url)
        
        # Analyze URL structure
        url_analysis = self.analyze_url_structure(url)
        
        # Check domain reliability
        domain_check = {'is_unreliable': False}
        if unreliable_domains:
            domain_check = self.check_domain_reliability(domain, unreliable_domains)
        
        # Fetch webpage content
        webpage_data = self.fetch_webpage(url)
        
        return {
            'valid': True,
            'url': url,
            'domain': domain,
            'url_analysis': url_analysis,
            'domain_check': domain_check,
            'webpage_data': webpage_data,
            'is_accessible': webpage_data is not None
        }


# Global instance
url_analyzer = URLAnalyzer()


if __name__ == "__main__":
    print("Testing URL Analyzer...")
    print("-" * 50)
    
    test_url = "https://www.example.com/article/fake-news-sample"
    
    print(f"\nAnalyzing URL: {test_url}")
    
    # Test domain extraction
    domain = url_analyzer.extract_domain(test_url)
    print(f"Domain: {domain}")
    
    # Test URL structure analysis
    structure = url_analyzer.analyze_url_structure(test_url)
    print(f"\nURL Structure Analysis:")
    print(f"  Suspicion Score: {structure['suspicion_score']}")
    print(f"  Is Suspicious: {structure['is_suspicious']}")
    
    # Test URL extraction from text
    text = "Check this out: https://example.com and also https://test.com"
    urls = url_analyzer.extract_urls(text)
    print(f"\nExtracted URLs from text: {urls}")
    
    print("\n✓ URL analyzer test complete")
