#!/usr/bin/env python3
"""
Test passport extraction using Gemini Vision API
"""

import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if Gemini API key is configured
gemini_key = os.environ.get('GEMINI_API_KEY', '')
if not gemini_key or gemini_key == 'your_gemini_api_key_here':
    print("\n" + "=" * 60)
    print("⚠️  GEMINI API KEY NOT CONFIGURED")
    print("=" * 60)
    print("\nTo use Gemini Vision for better OCR accuracy:")
    print("1. Get your API key from: https://makersuite.google.com/app/apikey")
    print("2. Add it to .env file: GEMINI_API_KEY=your_actual_key")
    print("\nFalling back to standard OCR (less accurate for UAE passports)")
    print("=" * 60 + "\n")

from extractors.passport_extractor_gemini import PassportExtractorGemini

def test_passport(image_path: str = 'sample_docs/sample_passport.jpg'):
    """Test passport extraction with Gemini"""
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    extractor = PassportExtractorGemini()
    result = extractor.extract(image_path)
    
    print("=" * 60)
    print(f"PASSPORT EXTRACTION TEST: {os.path.basename(image_path)}")
    print("=" * 60)
    
    if result['success']:
        print(f"\n✅ Extraction successful!")
        print(f"Method: {result['method']}")
        print(f"Confidence: {result['confidence']}")
        
        print("\nExtracted Data:")
        data = result['data']
        
        # Show all fields
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
        
        # Check for common UAE passport misreads
        if 'ONG' in str(data.get('first_name', '')) or 'ONG' in str(data.get('last_name', '')):
            print("\n⚠️  Warning: Detected possible misread 'ONG' - common OCR error for Arabic names")
        
        if data.get('nationality') == 'UNI':
            print("\n⚠️  Warning: Nationality 'UNI' is likely a misread of 'United Arab Emirates'")
        
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
    import sys
    
    # Test with provided image path or default
    if len(sys.argv) > 1:
        test_passport(sys.argv[1])
    else:
        # Test with sample passport
        print("Testing with sample passport...")
        test_passport()
        
        # If UAE passport exists, test it too
        if os.path.exists('sample_docs/uae_passport.jpg'):
            print("\n\nTesting with UAE passport...")
            test_passport('sample_docs/uae_passport.jpg')