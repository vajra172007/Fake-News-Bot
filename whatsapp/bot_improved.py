"""
WhatsApp Bot for Fake News Detection
Using whatsapp-web.js through Node.js subprocess
"""

import os
import sys
import json
import subprocess
import requests
from typing import Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


class WhatsAppFakeNewsBot:
    """
    WhatsApp bot that integrates with the Fake News Detection API.
    Uses Node.js whatsapp-web.js library for reliable WhatsApp automation.
    """
    
    def __init__(self):
        """Initialize the bot with API configuration."""
        self.api_url = f"http://{os.getenv('API_HOST', 'localhost')}:{os.getenv('API_PORT', 5000)}"
        self.node_script_path = os.path.join(os.path.dirname(__file__), 'whatsapp_bot.js')
        
        print("🤖 Initializing WhatsApp Fake News Detection Bot...")
        print(f"📡 API URL: {self.api_url}")
        
        # Test API connection
        self._test_api_connection()
    
    def _test_api_connection(self):
        """Test connection to the Fake News Detection API."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Connection: OK")
                print(f"✅ Fact Checks Available: {data.get('fact_checks_count', 'N/A')}")
                print(f"✅ Gemini AI: {'Enabled' if data.get('gemini_enabled') else 'Disabled'}")
            else:
                print(f"⚠️ API responded with status: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print(f"⚠️ Make sure the API server is running at {self.api_url}")
    
    def analyze_text(self, text: str, language: str = "en") -> Dict:
        """
        Analyze text using the Fake News Detection API.
        
        Args:
            text: Text to analyze
            language: Language code (en, ta, etc.)
            
        Returns:
            Analysis result dictionary
        """
        try:
            response = requests.post(
                f"{self.api_url}/analyze/text",
                json={"text": text, "language": language},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {
                "verdict": "error",
                "error": str(e),
                "message": "Failed to analyze message"
            }
    
    def format_response(self, analysis: Dict, language: str = "en") -> str:
        """
        Format API response into WhatsApp message.
        
        Args:
            analysis: Analysis result from API
            language: Language code for response
            
        Returns:
            Formatted WhatsApp message
        """
        if "error" in analysis:
            return f"❌ Error: {analysis.get('message', 'Unknown error')}"
        
        verdict = analysis.get('verdict', 'unverified').upper()
        confidence = analysis.get('confidence', 0.0)
        source = analysis.get('analysis_source', 'database')
        
        # Emoji mapping
        emoji_map = {
            "TRUE": "✅",
            "FALSE": "❌",
            "MISLEADING": "⚠️",
            "UNVERIFIED": "❓"
        }
        
        emoji = emoji_map.get(verdict, "❓")
        
        # Build response
        if language == "ta":
            response = f"{emoji} *முடிவு*: {verdict}\n"
            response += f"📊 *நம்பகத்தன்மை*: {confidence:.0%}\n"
            response += f"🔍 *ஆதாரம்*: {source.title()}\n\n"
        else:
            response = f"{emoji} *Verdict*: {verdict}\n"
            response += f"📊 *Confidence*: {confidence:.0%}\n"
            response += f"🔍 *Source*: {source.title()}\n\n"
        
        # Add explanation if available
        if 'explanation' in analysis and analysis['explanation']:
            explanation = analysis['explanation']
            if language == "ta":
                response += f"📝 *விளக்கம்*:\n{explanation}\n\n"
            else:
                response += f"📝 *Explanation*:\n{explanation}\n\n"
        
        # Add matched fact check if available
        if 'matched_fact_check' in analysis:
            match = analysis['matched_fact_check']
            if match and 'source_url' in match and match['source_url']:
                if language == "ta":
                    response += f"🔗 *மேலும் தகவல்*: {match['source_url']}"
                else:
                    response += f"🔗 *Source*: {match['source_url']}"
        
        # Add powered by message
        response += "\n\n_Powered by Fake News Detection Bot 🛡️_"
        
        return response
    
    def start(self):
        """
        Start the WhatsApp bot using Node.js subprocess.
        Requires whatsapp-web.js to be installed.
        """
        print("\n🚀 Starting WhatsApp Bot...")
        print("📱 Please scan the QR code when it appears...")
        
        try:
            # Run Node.js WhatsApp bot script
            subprocess.run(['node', self.node_script_path], check=True)
        except FileNotFoundError:
            print("❌ Node.js not found. Please install Node.js first.")
            print("Visit: https://nodejs.org/")
        except subprocess.CalledProcessError as e:
            print(f"❌ Bot crashed: {e}")
        except KeyboardInterrupt:
            print("\n⚠️ Bot stopped by user")


def main():
    """Main entry point."""
    print("=" * 60)
    print("🛡️ WhatsApp Fake News Detection Bot")
    print("=" * 60)
    
    bot = WhatsAppFakeNewsBot()
    bot.start()


if __name__ == "__main__":
    main()
