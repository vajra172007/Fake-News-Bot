"""
Gemini Flash AI Analyzer for enhanced fake news detection.
Uses Google's Gemini 1.5 Flash for real-time reasoning and multimodal analysis.
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class GeminiAnalyzer:
    """Gemini Flash AI analyzer for enhanced fact-checking."""
    
    def __init__(self):
        """Initialize Gemini analyzer with fallback models."""
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("⚠️  GEMINI_API_KEY not found in .env - Gemini features disabled")
            self.enabled = False
            return
        
        try:
            # Configure Gemini
            genai.configure(api_key=self.api_key)
            
            # Model priority list with fallback
            self.models = [
                'gemini-2.5-pro',      # Best quality, limited rate
                'gemini-2.0-flash',     # Good quality, faster
            ]
            
            # Configure generation settings
            self.generation_config = {
                'temperature': 0.2,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
            
            # No safety filters for fact-checking
            self.safety_settings = None
            
            self.enabled = True
            print("✓ Gemini Flash analyzer initialized")
            
        except Exception as e:
            print(f"⚠️  Failed to initialize Gemini: {e}")
            self.enabled = False
    
    def _generate_with_fallback(self, prompt_content, generation_config=None, safety_settings=None):
        """Try generation with fallback to other models if rate limited."""
        if generation_config is None:
            generation_config = self.generation_config
        if safety_settings is None:
            safety_settings = self.safety_settings
            
        last_error = None
        
        for model_name in self.models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt_content,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Check if response was blocked
                if not response.candidates or not response.candidates[0].content.parts:
                    finish_reason = response.candidates[0].finish_reason if response.candidates else None
                    print(f"⚠️  {model_name} blocked response (finish_reason: {finish_reason})")
                    continue
                
                # Success - return response with model info
                return response, model_name
                
            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error
                if '429' in error_str or 'quota' in error_str.lower() or 'rate' in error_str.lower():
                    print(f"⚠️  {model_name} rate limited, trying next model...")
                    last_error = e
                    continue
                else:
                    # Other errors - raise immediately
                    raise e
        
        # All models failed
        if last_error:
            raise last_error
        else:
            raise Exception("All models blocked the response due to safety filters")
    
    def analyze_text_claim(self, claim: str, language: str = 'en') -> Dict[str, Any]:
        """
        Analyze a text claim using Gemini's reasoning capabilities.
        
        Args:
            claim: The claim to analyze
            language: Language code (en, ta, hi, etc.)
            
        Returns:
            Dictionary with verdict, confidence, explanation
        """
        if not self.enabled:
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'Gemini API not configured',
                'source': 'gemini',
                'error': 'API key not found'
            }
        
        response = None
        try:
            # Construct the prompt with neutral language
            prompt = f"""Analyze this statement: "{claim}"

Respond in valid JSON format:
{{"verdict": "true|false|misleading|unverified", "confidence": 0.9, "explanation": "brief explanation", "reasoning": "analysis"}}

Use: true (accurate), false (inaccurate), misleading (partially true), unverified (cannot determine).
Language: {"English" if language == "en" else "Tamil" if language == "ta" else "English"}"""
            
            # Generate response with fallback
            response, model_used = self._generate_with_fallback(prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # More robust JSON parsing
            json_str = response_text
            if '```' in json_str:
                match = re.search(r'```(json)?(.*)```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(2).strip()

            # Find the start and end of the JSON object
            start = json_str.find('{')
            end = json_str.rfind('}')
            
            if start != -1 and end > start:
                json_str = json_str[start:end+1]
            else:
                # If we can't find a valid JSON object, raise an error with the raw response
                raise json.JSONDecodeError("Incomplete or malformed JSON object", json_str, 0)

            result = json.loads(json_str)
            
            # Add metadata
            result['source'] = 'gemini'
            result['model'] = model_used
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse Gemini response as JSON: {e}")
            raw_response_text = "Not available"
            if response and hasattr(response, 'text'):
                raw_response_text = response.text
            
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'Could not analyze claim due to malformed AI response.',
                'source': 'gemini',
                'error': f'JSON parse error: {e}',
                'raw_response': raw_response_text
            }
        except Exception as e:
            print(f"⚠️  Gemini API error: {e}")
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'API error occurred',
                'source': 'gemini',
                'error': str(e)
            }
    
    def analyze_image_with_text(self, image_path: str, claim_text: str = "", language: str = 'en') -> Dict[str, Any]:
        """
        Analyze an image with optional text claim using Gemini's vision capabilities.
        
        Args:
            image_path: Path to the image file
            claim_text: Optional text claim about the image
            language: Language code
            
        Returns:
            Dictionary with analysis results
        """
        if not self.enabled:
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'Gemini API not configured',
                'source': 'gemini',
                'error': 'API key not found'
            }
        
        try:
            # Load image
            import PIL.Image
            image = PIL.Image.open(image_path)
            
            # Construct prompt
            if claim_text:
                prompt = f"""You are an expert at detecting fake news and manipulated images for India.

Claim: "{claim_text}"

Analyze this image in the context of the claim. Respond in JSON format:

{{
    "verdict": "true" or "false" or "misleading" or "unverified",
    "confidence": 0.0 to 1.0,
    "explanation": "Detailed explanation",
    "image_description": "What you see in the image",
    "manipulation_detected": true or false,
    "context_mismatch": true or false (does image match the claim?),
    "red_flags": ["list of issues"],
    "reasoning": "Your analysis process"
}}

Look for:
1. Signs of digital manipulation (inconsistent lighting, artifacts, cloning)
2. Context mismatch (old image passed as recent, wrong location, etc.)
3. Misleading framing (cropped to change meaning)
4. Visual inconsistencies

Respond ONLY with valid JSON.
"""
            else:
                prompt = """You are an expert at detecting fake news and manipulated images.

Analyze this image for signs of manipulation or misleading content. Respond in JSON format:

{{
    "verdict": "authentic" or "manipulated" or "suspicious" or "unverified",
    "confidence": 0.0 to 1.0,
    "explanation": "What makes this image suspicious or authentic",
    "image_description": "Detailed description of the image",
    "manipulation_detected": true or false,
    "red_flags": ["list of suspicious elements"],
    "reasoning": "Your analysis"
}}

Respond ONLY with valid JSON.
"""
            
            # Generate response with image and fallback
            response, model_used = self._generate_with_fallback([prompt, image])
            
            # Parse response
            response_text = response.text.strip()
            
            # Clean JSON
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                response_text = response_text[start:end]
            
            result = json.loads(response_text)
            result['source'] = 'gemini'
            result['model'] = model_used
            
            return result
            
        except Exception as e:
            print(f"⚠️  Gemini image analysis error: {e}")
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'Could not analyze image',
                'source': 'gemini',
                'error': str(e)
            }
    
    def analyze_url_content(self, url: str, article_text: str, language: str = 'en') -> Dict[str, Any]:
        """
        Analyze article content from a URL using Gemini.
        
        Args:
            url: The URL being analyzed
            article_text: Extracted article text
            language: Language code
            
        Returns:
            Dictionary with analysis results
        """
        if not self.enabled:
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'Gemini API not configured',
                'source': 'gemini',
                'error': 'API key not found'
            }
        
        try:
            prompt = f"""You are an expert fact-checker analyzing news articles for credibility.

URL: {url}

Article excerpt: "{article_text[:2000]}"

Analyze this article for credibility and misinformation. Respond in JSON format:

{{
    "verdict": "credible" or "misleading" or "false" or "suspicious" or "unverified",
    "confidence": 0.0 to 1.0,
    "explanation": "Why this article is credible or not",
    "sensational_language": true or false,
    "lack_of_sources": true or false,
    "logical_inconsistencies": ["list of issues"],
    "red_flags": ["suspicious elements"],
    "reasoning": "Your analysis"
}}

Look for:
1. Sensational/clickbait language
2. Lack of credible sources
3. Logical inconsistencies
4. One-sided perspective
5. Unverified claims presented as facts

Respond ONLY with valid JSON.
"""
            
            response, model_used = self._generate_with_fallback(prompt)
            
            # Parse response
            response_text = response.text.strip()
            
            # Clean JSON
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                response_text = response_text[start:end]
            
            result = json.loads(response_text)
            result['source'] = 'gemini'
            result['model'] = model_used
            
            return result
            
        except Exception as e:
            print(f"⚠️  Gemini URL analysis error: {e}")
            return {
                'verdict': 'unverified',
                'confidence': 0.0,
                'explanation': 'Could not analyze article',
                'source': 'gemini',
                'error': str(e)
            }


# Create singleton instance
gemini_analyzer = GeminiAnalyzer()
