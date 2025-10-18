"""Multilingual response generator for fake news verdicts."""

from typing import Dict, Optional
from enum import Enum


class Verdict(Enum):
    """Verdict types for fake news detection."""
    FALSE = "false"
    MISLEADING = "misleading"
    UNVERIFIED = "unverified"
    TRUE = "true"


class ResponseGenerator:
    """Generate multilingual responses for users."""
    
    def __init__(self):
        """Initialize response templates."""
        self.templates = {
            'en': {
                'false': {
                    'emoji': '🔴',
                    'title': 'FALSE',
                    'verdict_text': 'This claim has been fact-checked and found to be FALSE.',
                    'advice': 'Please do not share this information.'
                },
                'misleading': {
                    'emoji': '🟡',
                    'title': 'MISLEADING',
                    'verdict_text': 'This content has been flagged as MISLEADING.',
                    'advice': 'The image or claim has been used out of context.'
                },
                'unverified': {
                    'emoji': '⚪',
                    'title': 'CANNOT VERIFY',
                    'verdict_text': 'We could not find a definitive answer in our fact-check database.',
                    'advice': 'This does not mean the claim is false, just that it has not been previously verified by our partner fact-checkers. Please be cautious.'
                },
                'true': {
                    'emoji': '🟢',
                    'title': 'TRUE',
                    'verdict_text': 'This claim has been verified as TRUE.',
                    'advice': 'This information appears to be accurate.'
                },
                'greeting': 'Hello! I can help you verify news, images, and links. Send me anything you want to check.',
                'processing': 'Analyzing... Please wait.',
                'error': 'Sorry, I encountered an error processing your request. Please try again.',
                'source_prefix': '\n\n📌 Source: ',
                'explanation_prefix': '\n\n💡 Explanation:\n',
                'original_context': '\n\n🔍 Original Context:\n'
            },
            'ta': {  # Tamil
                'false': {
                    'emoji': '🔴',
                    'title': 'பொய்',
                    'verdict_text': 'இந்த கூற்று சரிபார்க்கப்பட்டு பொய் என நிரூபிக்கப்பட்டுள்ளது.',
                    'advice': 'தயவுசெய்து இந்த தகவலை பகிராதீர்கள்.'
                },
                'misleading': {
                    'emoji': '🟡',
                    'title': 'தவறான தகவல்',
                    'verdict_text': 'இந்த உள்ளடக்கம் தவறான தகவல் என குறிக்கப்பட்டுள்ளது.',
                    'advice': 'படம் அல்லது கூற்று சூழலுக்கு வெளியே பயன்படுத்தப்பட்டுள்ளது.'
                },
                'unverified': {
                    'emoji': '⚪',
                    'title': 'சரிபார்க்க முடியவில்லை',
                    'verdict_text': 'எங்கள் தரவுத்தளத்தில் இந்த கூற்றை சரிபார்க்க முடியவில்லை.',
                    'advice': 'தயவுசெய்து எச்சரிக்கையாக இருங்கள் மற்றும் பகிர்வதற்கு முன் பல நம்பகமான ஆதாரங்களிலிருந்து சரிபார்க்கவும்.'
                },
                'true': {
                    'emoji': '🟢',
                    'title': 'உண்மை',
                    'verdict_text': 'இந்த கூற்று உண்மை என சரிபார்க்கப்பட்டுள்ளது.',
                    'advice': 'இந்த தகவல் துல்லியமானதாக தோன்றுகிறது.'
                },
                'greeting': 'வணக்கம்! செய்திகள், படங்கள் மற்றும் இணைப்புகளை சரிபார்க்க நான் உங்களுக்கு உதவ முடியும். நீங்கள் சரிபார்க்க விரும்பும் எதையும் எனக்கு அனுப்பவும்.',
                'processing': 'பகுப்பாய்வு செய்கிறது... காத்திருக்கவும்.',
                'error': 'மன்னிக்கவும், உங்கள் கோரிக்கையை செயல்படுத்துவதில் பிழை ஏற்பட்டது. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.',
                'source_prefix': '\n\n📌 ஆதாரம்: ',
                'explanation_prefix': '\n\n💡 விளக்கம்:\n',
                'original_context': '\n\n🔍 அசல் சூழல்:\n'
            }
        }
        
        print("✓ Response generator initialized (en, ta)")
    
    def get_verdict_response(self, 
                           verdict: str, 
                           language: str = 'en',
                           explanation: str = None,
                           source_url: str = None,
                           original_context: str = None,
                           confidence_score: float = None) -> str:
        """Generate a complete verdict response."""
        
        # Get language template (fallback to English)
        lang_template = self.templates.get(language, self.templates['en'])
        verdict_template = lang_template.get(verdict, lang_template['unverified'])
        
        # Build response
        response_parts = [
            f"{verdict_template['emoji']} *{verdict_template['title']}*",
            "",
            verdict_template['verdict_text']
        ]
        
        # Add explanation if provided
        if explanation:
            response_parts.append(lang_template['explanation_prefix'] + explanation)
        
        # Add original context for misleading content
        if original_context:
            response_parts.append(lang_template['original_context'] + original_context)
        
        # Add confidence score if available
        if confidence_score is not None:
            confidence_emoji = "🎯" if confidence_score > 0.8 else "📊"
            response_parts.append(f"\n{confidence_emoji} Confidence: {confidence_score:.0%}")
        
        # Add advice
        response_parts.append("\n⚠️ " + verdict_template['advice'])
        
        # Add source link if provided
        if source_url:
            response_parts.append(lang_template['source_prefix'] + source_url)
        
        return "\n".join(response_parts)
    
    def get_greeting(self, language: str = 'en') -> str:
        """Get greeting message."""
        lang_template = self.templates.get(language, self.templates['en'])
        return lang_template['greeting']
    
    def get_processing_message(self, language: str = 'en') -> str:
        """Get processing message."""
        lang_template = self.templates.get(language, self.templates['en'])
        return lang_template['processing']
    
    def get_error_message(self, language: str = 'en') -> str:
        """Get error message."""
        lang_template = self.templates.get(language, self.templates['en'])
        return lang_template['error']
    
    def format_fact_check_response(self, fact_check: Dict, language: str = 'en', confidence: float = None) -> str:
        """Format a fact-check result into a user response."""
        verdict = fact_check.get('verdict', 'unverified')
        explanation = fact_check.get('explanation', '')
        source_url = fact_check.get('source_url', '')
        
        return self.get_verdict_response(
            verdict=verdict,
            language=language,
            explanation=explanation,
            source_url=source_url,
            confidence_score=confidence
        )
    
    def format_image_match_response(self, image_match: Dict, language: str = 'en', confidence: float = None) -> str:
        """Format an image match result into a user response."""
        context = image_match.get('context', '')
        misleading_context = image_match.get('misleading_context', '')
        source_url = image_match.get('source_url', '')
        
        return self.get_verdict_response(
            verdict='misleading',
            language=language,
            explanation=misleading_context,
            original_context=context,
            source_url=source_url,
            confidence_score=confidence
        )
    
    def add_language(self, language_code: str, templates: Dict):
        """Add support for a new language."""
        self.templates[language_code] = templates
        print(f"✓ Added language support: {language_code}")


# Global instance
response_generator = ResponseGenerator()


if __name__ == "__main__":
    print("Testing Response Generator...")
    print("-" * 50)
    
    # Test English response
    print("\n=== English FALSE verdict ===")
    print(response_generator.get_verdict_response(
        verdict='false',
        language='en',
        explanation='This video is from 2019 and has been edited to make false claims.',
        source_url='https://www.altnews.in/example-article',
        confidence_score=0.92
    ))
    
    # Test Tamil response
    print("\n=== Tamil MISLEADING verdict ===")
    print(response_generator.get_verdict_response(
        verdict='misleading',
        language='ta',
        explanation='இந்த படம் 2020 இல் எடுக்கப்பட்டது மற்றும் தவறான சூழலில் பகிரப்பட்டுள்ளது.',
        original_context='இது உண்மையில் ஒரு திருவிழாவின் போது எடுக்கப்பட்ட புகைப்படம்.',
        source_url='https://www.boomlive.in/example',
        confidence_score=0.85
    ))
    
    # Test unverified response
    print("\n=== UNVERIFIED verdict ===")
    print(response_generator.get_verdict_response(
        verdict='unverified',
        language='en'
    ))
    
    print("\n✓ Response generator test complete")
