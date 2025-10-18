"""Flask API for the fake news detection system."""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import threading
import datetime
import threading
import datetime
message_logs = []
log_lock = threading.Lock()


app = Flask(__name__)
CORS(app)

def log_message(event_type, data):
    with log_lock:
        message_logs.append({
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event': event_type,
            'data': data
        })
        # Keep only the last 100 logs
        if len(message_logs) > 100:
            message_logs.pop(0)

@app.route('/logs', methods=['GET'])
def get_logs():
    html = '<h2>WhatsApp/Twilio Message Logs</h2><pre>'
    for entry in message_logs[-50:]:
        html += f"[{entry['timestamp']}] {entry['event']}: {entry['data']}\n"
    html += '</pre>'
    return Response(html, mimetype='text/html')
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from typing import Dict
import requests
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# Import analyzers
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import analyzers with fallback for production deployment
try:
    from analyzers.text_analyzer import text_analyzer
    print("✓ Full text analyzer loaded")
except Exception as e:
    print(f"⚠️  Full text analyzer failed ({e}), using simplified version...")
    from analyzers.simplified_text_analyzer import simplified_text_analyzer as text_analyzer

from analyzers.image_analyzer import image_analyzer
from analyzers.url_analyzer import url_analyzer
from analyzers.gemini_analyzer import gemini_analyzer
from utils.response_generator import response_generator
from database.setup_db import db

load_dotenv()

# Twilio Configuration
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
twilio_client = None
if twilio_account_sid and twilio_auth_token:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)
    print("✓ Twilio client initialized")
else:
    print("⚠️  Twilio credentials not found. WhatsApp bot via Twilio will not work.")


app = Flask(__name__)
CORS(app)

# --- LOGGING INTERFACE ---
message_logs = []
log_lock = threading.Lock()

def log_message(event_type, data):
    with log_lock:
        message_logs.append({
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event': event_type,
            'data': data
        })
        # Keep only the last 100 logs
        if len(message_logs) > 100:
            message_logs.pop(0)

@app.route('/logs', methods=['GET'])
def get_logs():
    html = '<h2>WhatsApp/Twilio Message Logs</h2><pre>'
    for entry in message_logs[-50:]:
        html += f"[{entry['timestamp']}] {entry['event']}: {entry['data']}\n"
    html += '</pre>'
    return Response(html, mimetype='text/html')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Fake News Detection API',
        'version': '1.0.0'
    })


@app.route('/analyze/text', methods=['POST'])
def analyze_text():
    """Analyze text for fake news."""
    start_time = time.time()
    
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text = data['text']
    language = data.get('language', 'en')
    
    try:
        # Analyze text
        text_analysis = text_analyzer.analyze_text(text)
        detected_language = text_analysis['language']
        
        # Get database session
        session = db.get_session()
        
        # Query fact-checks from database
        from models.database import FactCheck
        fact_checks = session.query(FactCheck).filter(
            FactCheck.language.in_([detected_language, 'en'])
        ).all()
        
        # Convert to dict
        fact_checks_dict = [fc.to_dict() for fc in fact_checks]
        
        # Find matching claims
        matches = text_analyzer.find_matching_claims(text, fact_checks_dict)
        
        verdict = 'unverified'
        confidence = 0.0
        matched_fact_check = None
        gemini_result = None
        analysis_source = 'database'
        
        # HYBRID APPROACH: Try database first
        if matches:
            matched_fact_check, confidence = matches[0]
            verdict = matched_fact_check['verdict']
            analysis_source = 'database'
        
        # FALLBACK: Use Gemini if no database match or low confidence
        elif gemini_analyzer.enabled and os.getenv('GEMINI_ENABLED', 'True').lower() == 'true':
            print("📡 No database match - falling back to Gemini Flash AI...")
            gemini_result = gemini_analyzer.analyze_text_claim(text, detected_language)
            
            if gemini_result and gemini_result.get('confidence', 0) >= float(os.getenv('GEMINI_CONFIDENCE_THRESHOLD', '0.6')):
                verdict = gemini_result.get('verdict', 'unverified')
                confidence = gemini_result.get('confidence', 0.0)
                analysis_source = 'gemini'
                
                # Create a fact-check-like structure for response generation
                matched_fact_check = {
                    'id': None,  # Gemini results don't have database IDs
                    'claim': text[:200],
                    'verdict': verdict,
                    'explanation': gemini_result.get('explanation', ''),
                    'source': 'Gemini AI',
                    'source_url': None,
                    'reasoning': gemini_result.get('reasoning', ''),
                    'red_flags': gemini_result.get('red_flags', [])
                }
                
                # 🧠 GEMINI LEARNING SYSTEM: Save high-confidence results to database
                learning_threshold = float(os.getenv('GEMINI_LEARNING_THRESHOLD', '0.9'))
                if confidence >= learning_threshold and verdict != 'unverified':
                    print(f"🧠 Gemini Learning: Saving high-confidence result (confidence: {confidence:.2f})")
                    try:
                        from models.database import FactCheck
                        import json
                        
                        # Check if similar claim already exists
                        embedding = text_analyzer.compute_embedding(text)
                        
                        # Create new fact-check entry from Gemini result
                        new_fact_check = FactCheck(
                            claim=text[:500],
                            verdict=verdict,
                            explanation=gemini_result.get('explanation', ''),
                            source='Gemini AI',
                            source_url=None,
                            original_url=None,
                            published_date=None,
                            scraped_date=datetime.utcnow(),
                            language=detected_language,
                            keywords=None,
                            embedding=embedding,
                            source_type='gemini',
                            confidence_score=confidence,
                            gemini_generated=True,
                            red_flags=gemini_result.get('red_flags', [])
                        )
                        
                        session.add(new_fact_check)
                        session.commit()
                        
                        # Update matched_fact_check with the new ID
                        matched_fact_check['id'] = new_fact_check.id
                        
                        print(f"✅ Gemini result saved to database (ID: {new_fact_check.id})")
                        
                    except Exception as e:
                        print(f"⚠️  Failed to save Gemini result to database: {e}")
                        session.rollback()
        
        # Generate response
        if matched_fact_check:
            response_text = response_generator.format_fact_check_response(
                matched_fact_check, 
                language=detected_language,
                confidence=confidence
            )
        else:
            response_text = response_generator.get_verdict_response(
                verdict='unverified',
                language=detected_language
            )
        
        # Log query
        from models.database import UserQuery
        query_log = UserQuery(
            user_id='api_user',
            query_type='text',
            query_content=text[:500],
            verdict=verdict,
            confidence_score=confidence,
            language=detected_language,
            processing_time=time.time() - start_time,
            matched_fact_check_id=matched_fact_check['id'] if matched_fact_check else None
        )
        session.add(query_log)
        session.commit()
        
        session.close()
        
        return jsonify({
            'verdict': verdict,
            'confidence': confidence,
            'language': detected_language,
            'response': response_text,
            'matched_fact_check': matched_fact_check,
            'gemini_result': gemini_result if analysis_source == 'gemini' else None,
            'analysis_source': analysis_source,
            'processing_time': time.time() - start_time
        })
        
    except Exception as e:
        print(f"Error in analyze_text: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/analyze/image', methods=['POST'])
def analyze_image():
    """Analyze image for fake news."""
    start_time = time.time()
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    language = request.form.get('language', 'en')
    
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze image
        image_analysis = image_analyzer.analyze_image(image_path=filepath)
        
        if not image_analysis:
            return jsonify({'error': 'Failed to analyze image'}), 500
        
        # Get database session
        session = db.get_session()
        
        # Query image hashes from database
        from models.database import ImageHash
        image_hashes = session.query(ImageHash).all()
        image_hashes_dict = [ih.to_dict() for ih in image_hashes]
        
        # Find matching images
        query_hash = image_analysis['hashes']['phash']
        matches = image_analyzer.find_matching_images(query_hash, image_hashes_dict)
        
        verdict = 'unverified'
        matched_image = None
        
        if matches:
            matched_image, distance = matches[0]
            verdict = 'misleading'
            confidence = 1.0 - (distance / 10.0)  # Convert distance to confidence
        
        # If image has text, analyze it
        text_verdict = None
        gemini_image_result = None
        
        if image_analysis.get('has_text'):
            extracted_text = image_analysis['extracted_text']
            text_analysis = text_analyzer.analyze_text(extracted_text)
            
            from models.database import FactCheck
            fact_checks = session.query(FactCheck).all()
            fact_checks_dict = [fc.to_dict() for fc in fact_checks]
            
            text_matches = text_analyzer.find_matching_claims(extracted_text, fact_checks_dict)
            if text_matches:
                text_verdict = text_matches[0][0]['verdict']
                if text_verdict == 'false':
                    verdict = 'false'
        
        # Use Gemini for enhanced image analysis if no match found
        if not matches and gemini_analyzer.enabled and os.getenv('GEMINI_ENABLED', 'True').lower() == 'true':
            print("📡 Using Gemini Flash for image analysis...")
            claim_text = request.form.get('claim', '')
            gemini_image_result = gemini_analyzer.analyze_image_with_text(filepath, claim_text, language)
            
            if gemini_image_result and gemini_image_result.get('confidence', 0) >= float(os.getenv('GEMINI_CONFIDENCE_THRESHOLD', '0.6')):
                verdict = gemini_image_result.get('verdict', 'unverified')
                confidence = gemini_image_result.get('confidence', 0.0)
        
        # Generate response
        if matched_image:
            response_text = response_generator.format_image_match_response(
                matched_image,
                language=language,
                confidence=confidence
            )
        else:
            response_text = response_generator.get_verdict_response(
                verdict=verdict,
                language=language
            )
        
        # Clean up
        os.remove(filepath)
        
        # Log query
        from models.database import UserQuery
        query_log = UserQuery(
            user_id='api_user',
            query_type='image',
            query_content=query_hash,
            verdict=verdict,
            confidence_score=confidence if matches else 0.0,
            language=language,
            processing_time=time.time() - start_time
        )
        session.add(query_log)
        session.commit()
        
        session.close()
        
        return jsonify({
            'verdict': verdict,
            'confidence': confidence if matches or gemini_image_result else 0.0,
            'response': response_text,
            'image_analysis': {
                'has_text': image_analysis.get('has_text', False),
                'extracted_text': image_analysis.get('extracted_text', '')[:200]
            },
            'matched_image': matched_image,
            'gemini_analysis': gemini_image_result,
            'analysis_source': 'gemini' if gemini_image_result and not matches else 'database',
            'processing_time': time.time() - start_time
        })
        
    except Exception as e:
        print(f"Error in analyze_image: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/analyze/url', methods=['POST'])
def analyze_url():
    """Analyze URL for fake news."""
    start_time = time.time()
    
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    url = data['url']
    language = data.get('language', 'en')
    
    try:
        # Get database session
        session = db.get_session()
        
        # Query unreliable domains
        from models.database import UnreliableDomain
        unreliable_domains = session.query(UnreliableDomain).filter(
            UnreliableDomain.is_active == True
        ).all()
        unreliable_domains_dict = [ud.to_dict() for ud in unreliable_domains]
        
        # Analyze URL
        url_analysis = url_analyzer.analyze_url(url, unreliable_domains_dict)
        
        verdict = 'unverified'
        confidence = 0.0
        
        # Check domain reliability
        if url_analysis['domain_check']['is_unreliable']:
            verdict = 'false'
            confidence = 0.9
        
        # Analyze webpage content if available
        if url_analysis['webpage_data']:
            webpage_text = url_analysis['webpage_data']['text']
            text_analysis = text_analyzer.analyze_text(webpage_text)
            
            from models.database import FactCheck
            fact_checks = session.query(FactCheck).all()
            fact_checks_dict = [fc.to_dict() for fc in fact_checks]
            
            matches = text_analyzer.find_matching_claims(webpage_text, fact_checks_dict)
            
            if matches:
                matched_fact_check, match_confidence = matches[0]
                verdict = matched_fact_check['verdict']
                confidence = match_confidence
        
        # Generate response
        response_text = response_generator.get_verdict_response(
            verdict=verdict,
            language=language,
            confidence_score=confidence,
            explanation=url_analysis['domain_check'].get('reason', '')
        )
        
        # Log query
        from models.database import UserQuery
        query_log = UserQuery(
            user_id='api_user',
            query_type='url',
            query_content=url,
            verdict=verdict,
            confidence_score=confidence,
            language=language,
            processing_time=time.time() - start_time
        )
        session.add(query_log)
        session.commit()
        
        session.close()
        
        return jsonify({
            'verdict': verdict,
            'confidence': confidence,
            'response': response_text,
            'url_analysis': {
                'domain': url_analysis['domain'],
                'is_unreliable': url_analysis['domain_check']['is_unreliable'],
                'is_suspicious': url_analysis['url_analysis']['is_suspicious']
            },
            'processing_time': time.time() - start_time
        })
        
    except Exception as e:
        print(f"Error in analyze_url: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        session = db.get_session()
        
        from models.database import FactCheck, ImageHash, UnreliableDomain, UserQuery
        
        fact_checks_count = session.query(FactCheck).count()
        image_hashes_count = session.query(ImageHash).count()
        unreliable_domains_count = session.query(UnreliableDomain).filter(
            UnreliableDomain.is_active == True
        ).count()
        user_queries_count = session.query(UserQuery).count()
        
        session.close()
        
        return jsonify({
            'fact_checks': fact_checks_count,
            'image_hashes': image_hashes_count,
            'unreliable_domains': unreliable_domains_count,
            'total_queries': user_queries_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/twilio/whatsapp', methods=['POST'])
def twilio_whatsapp_webhook():
    """Webhook for receiving WhatsApp messages from Twilio."""
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    media_url = request.values.get('MediaUrl0')
    media_type = request.values.get('MediaContentType0')


    log_message('INCOMING', f"From: {from_number} | Body: {incoming_msg}")
    if media_url:
        log_message('INCOMING_MEDIA', f"From: {from_number} | Media: {media_url} ({media_type})")

    response = MessagingResponse()
    reply_text = ""

    try:
        session = db.get_session()
        from models.database import FactCheck, ImageHash, UnreliableDomain, UserQuery

        # Handle different message types
        if media_url and media_type and 'image' in media_type:
            # --- IMAGE ANALYSIS ---
            try:
                # Download the image WITH AUTHENTICATION
                image_response = requests.get(
                    media_url,
                    auth=(twilio_account_sid, twilio_auth_token),
                    stream=True
                )
                image_response.raise_for_status()
                
                # Use a more unique filename to avoid conflicts
                filename = secure_filename(f"{from_number}_{media_url.split('/')[-1]}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in image_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Analyze image
                image_analysis = image_analyzer.analyze_image(image_path=filepath)
                
                # Find matching images in DB
                query_hash = image_analysis['hashes']['phash']
                image_hashes = session.query(ImageHash).all()
                matches = image_analyzer.find_matching_images(query_hash, [ih.to_dict() for ih in image_hashes])

                if matches:
                    matched_image, distance = matches[0]
                    confidence = 1.0 - (distance / 10.0)
                    reply_text = response_generator.format_image_match_response(matched_image, language='en', confidence=confidence)
                else:
                    reply_text = response_generator.get_verdict_response(verdict='unverified', language='en')

                os.remove(filepath) # Clean up

            except Exception as e:
                print(f"Error analyzing image from Twilio: {e}")
                reply_text = "Sorry, I couldn't process the image you sent. Please try again."

        elif 'http://' in incoming_msg or 'https://' in incoming_msg:
            # --- URL ANALYSIS ---
            unreliable_domains = session.query(UnreliableDomain).filter(UnreliableDomain.is_active == True).all()
            url_analysis = url_analyzer.analyze_url(incoming_msg, [ud.to_dict() for ud in unreliable_domains])
            
            verdict = 'unverified'
            confidence = 0.0
            explanation = ''

            if url_analysis['domain_check']['is_unreliable']:
                verdict = 'false'
                confidence = 0.9
                explanation = url_analysis['domain_check'].get('reason', '')
            
            reply_text = response_generator.get_verdict_response(verdict=verdict, language='en', confidence_score=confidence, explanation=explanation)

        else:
            # --- TEXT ANALYSIS ---
            fact_checks = session.query(FactCheck).filter(FactCheck.language.in_(['en', 'ta'])).all()
            matches = text_analyzer.find_matching_claims(incoming_msg, [fc.to_dict() for fc in fact_checks])
            
            if matches:
                matched_fact_check, confidence = matches[0]
                reply_text = response_generator.format_fact_check_response(matched_fact_check, language='en', confidence=confidence)
            elif gemini_analyzer.enabled:
                print("📡 No database match - falling back to Gemini Flash AI...")
                gemini_result = gemini_analyzer.analyze_text_claim(incoming_msg, 'en')
                
                # Check if Gemini returned a valid result and meets confidence threshold
                if gemini_result and 'error' not in gemini_result and gemini_result.get('confidence', 0) >= float(os.getenv('GEMINI_CONFIDENCE_THRESHOLD', '0.6')):
                    matched_fact_check = {
                        'claim': incoming_msg[:200], 
                        'verdict': gemini_result.get('verdict', 'unverified'),
                        'explanation': gemini_result.get('explanation', ''), 
                        'source': 'Gemini AI',
                    }
                    reply_text = response_generator.format_fact_check_response(
                        matched_fact_check, language='en', confidence=gemini_result.get('confidence', 0.0)
                    )
                else:
                    # Handle cases where Gemini fails or returns low-confidence result
                    error_message = gemini_result.get('error', 'low_confidence') if gemini_result else 'analysis_failed'
                    print(f"⚠️  Gemini analysis could not be used. Reason: {error_message}")
                    
                    # Send a user-friendly message
                    if 'rate' in error_message or 'quota' in error_message:
                        reply_text = "Our AI analyzer is currently experiencing high traffic. Please try again in a few moments."
                    elif 'JSON' in error_message or 'malformed' in error_message:
                        reply_text = "Our AI analyzer returned a malformed response. We are working on a fix. Please try again."
                    else:
                        reply_text = response_generator.get_verdict_response(verdict='unverified', language='en')
            else:
                reply_text = response_generator.get_verdict_response(verdict='unverified', language='en')

        session.close()

    except Exception as e:
        print(f"Error processing Twilio message: {e}")
        reply_text = "Sorry, an error occurred while processing your request. Please try again later."

    log_message('OUTGOING', f"To: {from_number} | Reply: {reply_text}")
    response.message(reply_text)
    return str(response)


# Main entry point
if __name__ == "__main__":
    # Default to port 5001 if not specified
    port = int(os.environ.get("PORT", 5001))
    
    # Check for --port argument
    if '--port' in sys.argv:
        try:
            port_index = sys.argv.index('--port') + 1
            if port_index < len(sys.argv):
                port = int(sys.argv[port_index])
        except (ValueError, IndexError):
            print("Invalid port number specified. Using default.")

    print(f"🚀 Starting Fake News Detection API")
    print(f"📡 Server: http://0.0.0.0:{port}")
    print(f"🔍 Debug mode: {app.debug}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
        print("✓ API is ready to accept requests")
    except OSError as e:
        if e.errno == 98: # Address already in use
            print(f"❌ ERROR: Port {port} is already in use.")
            print("Please stop the other program or specify a different port using --port <number>")
        else:
            print(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)
