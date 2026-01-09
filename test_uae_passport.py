#!/usr/bin/env python3
"""
Test UAE passport extraction with known values
"""

import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from extractors.passport_extractor import PassportExtractor

def test_uae_passport():
    """Test UAE passport extraction with expected values"""
    
    # Expected values from the UAE passport
    expected = {
        'name': 'SALEM AL-ALI',
        'passport_number': 'X12A45678',
        'nationality': 'ARE',
        'country_code': 'ARE',
        'date_of_birth': '21/11/1985',
        'place_of_birth': 'ABU DHABI',
        'sex': 'M',
        'issue_date': '15/03/2016',
        'expiry_date': '15/03/2021'
    }
    
    print("=" * 60)
    print("UAE PASSPORT EXTRACTION TEST")
    print("=" * 60)
    print("\nExpected values:")
    for key, value in expected.items():
        print(f"  {key}: {value}")
    
    # Check if UAE passport image exists
    uae_passport_path = 'sample_docs/uae_passport.jpg'
    if not os.path.exists(uae_passport_path):
        print(f"\n❌ UAE passport image not found at {uae_passport_path}")
        print("Please save the UAE passport image to this location and run the test again.")
        return
    
    # Test extraction
    extractor = PassportExtractor()
    result = extractor.extract(uae_passport_path)
    
    print("\n" + "=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)
    
    if result['success']:
        print(f"\n✅ Extraction successful!")
        print(f"Method: {result['method']}")
        print(f"Confidence: {result['confidence']}")
        
        print("\nExtracted Data:")
        data = result['data']
        
        # Check critical fields
        checks = {
            'Full Name': (data.get('full_name', ''), expected['name']),
            'Passport Number': (data.get('passport_number', ''), expected['passport_number']),
            'Nationality': (data.get('nationality', ''), expected['nationality']),
            'Country Code': (data.get('country_code', ''), expected['country_code']),
            'Date of Birth': (data.get('date_of_birth', ''), None),  # Date format may vary
            'Sex': (data.get('sex', ''), expected['sex']),
            'Issue Date': (data.get('issue_date', ''), None),  # Date format may vary
            'Expiry Date': (data.get('expiry_date', ''), None),  # Date format may vary
        }
        
        print("\nField Validation:")
        all_correct = True
        for field, (extracted, expected_val) in checks.items():
            if expected_val and extracted != expected_val:
                print(f"  ❌ {field}: '{extracted}' (expected: '{expected_val}')")
                all_correct = False
            else:
                status = '✓' if extracted else '✗'
                print(f"  [{status}] {field}: {extracted if extracted else '(empty)'}")
        
        # Show all fields
        print("\nAll Extracted Fields:")
        all_fields = [
            'full_name', 'first_name', 'middle_name', 'last_name',
            'passport_number', 'nationality', 'country_code',
            'date_of_birth', 'place_of_birth', 'sex',
            'issue_date', 'expiry_date'
        ]
        for key in all_fields:
            value = data.get(key, '')
            if value:
                print(f"  {key}: {value}")
        
        print("\nValidation:")
        validation = result['validation']
        if validation['errors']:
            print(f"  Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
        
        if all_correct:
            print("\n✅ All critical fields extracted correctly!")
        else:
            print("\n⚠️ Some fields need improvement")
            
    else:
        print("\n❌ Extraction failed!")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_uae_passport()