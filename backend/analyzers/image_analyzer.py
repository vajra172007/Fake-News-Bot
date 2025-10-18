"""Image analysis module for perceptual hashing and OCR."""

import os
import cv2
import numpy as np
from PIL import Image
import imagehash
import pytesseract
from typing import Dict, Tuple, Optional, List
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()


class ImageAnalyzer:
    """Analyze images for fake news detection."""
    
    def __init__(self):
        """Initialize image analysis tools."""
        self.hash_algorithm = os.getenv('IMAGE_HASH_ALGORITHM', 'phash')
        self.similarity_threshold = int(os.getenv('IMAGE_SIMILARITY_THRESHOLD', 5))
        self.max_image_size_mb = int(os.getenv('MAX_IMAGE_SIZE_MB', 10))
        
        # Set Tesseract path if specified
        tesseract_path = os.getenv('TESSERACT_PATH')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Tesseract languages
        self.tesseract_langs = os.getenv('TESSERACT_LANGS', 'eng+tam')
        
        print("✓ Image analyzer initialized")
    
    def load_image(self, image_path: str) -> Optional[Image.Image]:
        """Load image from file path."""
        try:
            img = Image.open(image_path)
            # Check file size
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            if file_size_mb > self.max_image_size_mb:
                print(f"⚠️  Image too large: {file_size_mb:.2f}MB")
                return None
            return img
        except Exception as e:
            print(f"❌ Error loading image: {e}")
            return None
    
    def load_image_from_bytes(self, image_bytes: bytes) -> Optional[Image.Image]:
        """Load image from bytes."""
        try:
            img = Image.open(BytesIO(image_bytes))
            return img
        except Exception as e:
            print(f"❌ Error loading image from bytes: {e}")
            return None
    
    def compute_perceptual_hashes(self, image: Image.Image) -> Dict[str, str]:
        """Compute multiple perceptual hashes for an image."""
        hashes = {
            'phash': str(imagehash.phash(image)),
            'dhash': str(imagehash.dhash(image)),
            'ahash': str(imagehash.average_hash(image)),
            'whash': str(imagehash.whash(image))
        }
        return hashes
    
    def compute_hash(self, image: Image.Image, algorithm: str = None) -> str:
        """Compute a single perceptual hash."""
        algo = algorithm or self.hash_algorithm
        
        if algo == 'phash':
            return str(imagehash.phash(image))
        elif algo == 'dhash':
            return str(imagehash.dhash(image))
        elif algo == 'ahash':
            return str(imagehash.average_hash(image))
        elif algo == 'whash':
            return str(imagehash.whash(image))
        else:
            return str(imagehash.phash(image))
    
    def compare_hashes(self, hash1: str, hash2: str) -> int:
        """Compare two perceptual hashes and return Hamming distance."""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2  # Hamming distance
        except Exception as e:
            print(f"❌ Error comparing hashes: {e}")
            return 999
    
    def is_similar(self, hash1: str, hash2: str) -> bool:
        """Check if two images are similar based on hash comparison."""
        distance = self.compare_hashes(hash1, hash2)
        return distance <= self.similarity_threshold
    
    def find_matching_images(self, query_hash: str, image_hashes: List[Dict]) -> List[Tuple[Dict, int]]:
        """Find matching images from database."""
        matches = []
        
        for img_record in image_hashes:
            stored_hash = img_record.get('phash', '')
            if not stored_hash:
                continue
            
            distance = self.compare_hashes(query_hash, stored_hash)
            if distance <= self.similarity_threshold:
                matches.append((img_record, distance))
        
        # Sort by distance (closest first)
        matches.sort(key=lambda x: x[1])
        return matches
    
    def extract_text_from_image(self, image: Image.Image, language: str = None) -> str:
        """Extract text from image using OCR."""
        try:
            # Convert PIL image to OpenCV format for preprocessing
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(denoised)
            
            # Perform OCR
            langs = language if language else self.tesseract_langs
            text = pytesseract.image_to_string(processed_image, lang=langs)
            
            return text.strip()
        except Exception as e:
            print(f"❌ Error extracting text from image: {e}")
            return ""
    
    def detect_image_manipulation(self, image: Image.Image) -> Dict:
        """Detect potential image manipulation (basic analysis)."""
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Error Level Analysis (ELA) - simplified
        # This is a basic implementation; more sophisticated methods exist
        quality = 90
        temp_path = '/tmp/temp_image.jpg'
        image.save(temp_path, 'JPEG', quality=quality)
        
        compressed = Image.open(temp_path)
        ela_im = ImageChops.difference(image, compressed)
        
        extrema = ela_im.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {
            'max_difference': max_diff,
            'potentially_manipulated': max_diff > 50
        }
    
    def analyze_image(self, image_path: str = None, image_bytes: bytes = None) -> Optional[Dict]:
        """Complete analysis of an image."""
        # Load image
        if image_path:
            image = self.load_image(image_path)
        elif image_bytes:
            image = self.load_image_from_bytes(image_bytes)
        else:
            return None
        
        if image is None:
            return None
        
        # Compute hashes
        hashes = self.compute_perceptual_hashes(image)
        
        # Extract text
        extracted_text = self.extract_text_from_image(image)
        
        # Get image properties
        width, height = image.size
        file_format = image.format
        
        return {
            'hashes': hashes,
            'extracted_text': extracted_text,
            'has_text': len(extracted_text) > 10,
            'dimensions': {
                'width': width,
                'height': height
            },
            'format': file_format
        }


# Import for manipulation detection
try:
    from PIL import ImageChops
except ImportError:
    print("⚠️  PIL.ImageChops not available")


# Global instance
image_analyzer = ImageAnalyzer()


if __name__ == "__main__":
    print("Testing Image Analyzer...")
    print("-" * 50)
    
    # Create a test image
    test_img = Image.new('RGB', (200, 100), color='white')
    
    # Compute hashes
    hashes = image_analyzer.compute_perceptual_hashes(test_img)
    print(f"Perceptual Hashes:")
    for algo, hash_val in hashes.items():
        print(f"  {algo}: {hash_val}")
    
    # Test hash comparison
    hash1 = hashes['phash']
    hash2 = hashes['phash']  # Same hash
    distance = image_analyzer.compare_hashes(hash1, hash2)
    print(f"\nHamming distance (same image): {distance}")
    print(f"Are similar: {image_analyzer.is_similar(hash1, hash2)}")
    
    print("\n✓ Image analyzer test complete")
