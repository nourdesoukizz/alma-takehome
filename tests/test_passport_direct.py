#!/usr/bin/env python3
"""
Test passport extraction directly
"""

import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from extractors.passport_extractor import PassportExtractor

def test_passport():
    """Test passport extraction on sample passport"""
    extractor = PassportExtractor()
    
    # Test with the sample passport
    result = extractor.extract('sample_docs/sample_passport.jpg')
    
    print("=" * 60)
    print("PASSPORT EXTRACTION TEST")
    print("=" * 60)
    
    if result['success']:
        print("\n✅ Extraction successful!")
        print(f"Method: {result['method']}")
        print(f"Confidence: {result['confidence']}")
        
        print("\nExtracted Data:")
        data = result['data']
        # Show all fields, even empty ones
        all_fields = [
            'full_name', 'first_name', 'middle_name', 'last_name',
            'passport_number', 'nationality', 'country_code',
            'date_of_birth', 'place_of_birth', 'sex',
            'issue_date', 'expiry_date'
        ]
        for key in all_fields:
            value = data.get(key, '')
            status = '✓' if value else '✗'
            print(f"  [{status}] {key}: {value if value else '(empty)'}")
        
        print("\nValidation:")
        validation = result['validation']
        if validation['errors']:
            print(f"  Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
    else:
        print("\n❌ Extraction failed!")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_passport()