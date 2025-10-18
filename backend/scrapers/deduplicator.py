"""Deduplication system to prevent duplicate fact-checks in database."""

import os
import sys
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer, util
import torch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from models.database import FactCheck
from database.setup_db import db


class Deduplicator:
    """Detect and prevent duplicate fact-checks using semantic similarity."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Cosine similarity threshold (0-1) for considering claims as duplicates
                                 0.85 = very similar, 0.90 = nearly identical
        """
        self.similarity_threshold = similarity_threshold
        print(f"📊 Loading sentence transformer model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"✓ Deduplicator initialized (threshold: {similarity_threshold})")
        
    def get_existing_claims(self, session) -> List[Dict]:
        """Fetch all existing claims from database with their embeddings."""
        claims = session.query(FactCheck).all()
        
        result = []
        for claim in claims:
            result.append({
                'id': claim.id,
                'claim': claim.claim,
                'embedding': claim.embedding,
                'source': claim.source,
                'verdict': claim.verdict
            })
        
        return result
    
    def compute_embedding(self, text: str) -> List[float]:
        """Compute sentence embedding for a text."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    def is_duplicate(self, new_claim: str, session) -> Optional[Dict]:
        """
        Check if a claim is duplicate of existing one.
        
        Args:
            new_claim: The claim text to check
            session: Database session
            
        Returns:
            Dict with duplicate info if found, None otherwise
        """
        # Get existing claims
        existing = self.get_existing_claims(session)
        
        if not existing:
            return None
        
        # Compute embedding for new claim
        new_embedding = self.compute_embedding(new_claim)
        new_tensor = torch.tensor([new_embedding])
        
        # Compare with all existing claims
        for existing_claim in existing:
            if existing_claim['embedding']:
                existing_tensor = torch.tensor([existing_claim['embedding']])
                similarity = util.cos_sim(new_tensor, existing_tensor).item()
                
                if similarity >= self.similarity_threshold:
                    return {
                        'is_duplicate': True,
                        'matched_claim_id': existing_claim['id'],
                        'matched_claim': existing_claim['claim'],
                        'similarity': similarity,
                        'existing_source': existing_claim['source'],
                        'existing_verdict': existing_claim['verdict']
                    }
        
        return None
    
    def filter_duplicates(self, new_claims: List[Dict], session) -> List[Dict]:
        """
        Filter out duplicate claims from a list of new claims.
        
        Args:
            new_claims: List of dicts with 'claim' key
            session: Database session
            
        Returns:
            List of unique claims (non-duplicates)
        """
        unique_claims = []
        duplicate_count = 0
        
        print(f"🔍 Checking {len(new_claims)} claims for duplicates...")
        
        for claim_data in new_claims:
            claim_text = claim_data.get('claim', '')
            
            if not claim_text:
                continue
            
            duplicate = self.is_duplicate(claim_text, session)
            
            if duplicate:
                duplicate_count += 1
                print(f"⚠️  Duplicate found: '{claim_text[:60]}...'")
                print(f"    → Similar to existing claim (ID: {duplicate['matched_claim_id']}, "
                      f"similarity: {duplicate['similarity']:.2f})")
            else:
                # Add embedding to claim data for storage
                claim_data['embedding'] = self.compute_embedding(claim_text)
                unique_claims.append(claim_data)
        
        print(f"✓ Filtered: {len(unique_claims)} unique, {duplicate_count} duplicates removed")
        
        return unique_claims
    
    def batch_check_duplicates(self, claims: List[str], session) -> Dict:
        """
        Check multiple claims at once and return detailed report.
        
        Args:
            claims: List of claim texts
            session: Database session
            
        Returns:
            Dict with 'unique', 'duplicates' keys
        """
        results = {
            'unique': [],
            'duplicates': []
        }
        
        for claim in claims:
            duplicate = self.is_duplicate(claim, session)
            
            if duplicate:
                results['duplicates'].append({
                    'claim': claim,
                    'matched_claim_id': duplicate['matched_claim_id'],
                    'similarity': duplicate['similarity']
                })
            else:
                results['unique'].append(claim)
        
        return results


def test_deduplicator():
    """Test the deduplicator with sample claims."""
    print("🧪 Testing Deduplicator...\n")
    
    dedup = Deduplicator(similarity_threshold=0.85)
    session = db.get_session()
    
    # Test claims
    test_claims = [
        "PM Modi announced free electricity for all citizens",
        "Prime Minister Modi has announced free electricity for everyone",  # Should be duplicate
        "Elon Musk bought Facebook for $500 billion",
        "The earth is flat according to new NASA research"
    ]
    
    print("\n📝 Testing claims:")
    for i, claim in enumerate(test_claims, 1):
        print(f"{i}. {claim}")
        duplicate = dedup.is_duplicate(claim, session)
        if duplicate:
            print(f"   ✗ DUPLICATE (similarity: {duplicate['similarity']:.2f})")
            print(f"     Matched: {duplicate['matched_claim'][:60]}...")
        else:
            print(f"   ✓ UNIQUE")
        print()
    
    session.close()


if __name__ == "__main__":
    test_deduplicator()
