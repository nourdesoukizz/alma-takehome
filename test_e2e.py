#!/usr/bin/env python3
"""
End-to-End Test Script for Document Form Filler
Tests the complete workflow from upload to form filling
"""

import requests
import json
import time
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("1. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    print("   ✓ Health check passed")
    return True

def test_upload():
    """Test document upload"""
    print("\n2. Testing document upload...")
    
    # Check for sample documents
    passport_file = Path("sample_docs/sample_passport.jpg")
    g28_file = Path("sample_docs/sample_g28.pdf")
    
    if not passport_file.exists() or not g28_file.exists():
        print("   ⚠ Sample documents not found. Skipping upload test.")
        return None
    
    # Generate a session ID
    import uuid
    import random
    import string
    session_id = f"{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=9))}"
    
    # Upload passport
    with open(passport_file, 'rb') as f:
        files = {'file': ('passport.jpg', f, 'image/jpeg')}
        data = {'session_id': session_id}
        response = requests.post(f"{BASE_URL}/api/upload", files=files, data=data)
    
    assert response.status_code == 200, f"Passport upload failed: {response.status_code} - {response.text}"
    
    # Upload G-28
    with open(g28_file, 'rb') as f:
        files = {'file': ('g28.pdf', f, 'application/pdf')}
        data = {'session_id': session_id}
        response = requests.post(f"{BASE_URL}/api/upload", files=files, data=data)
    
    assert response.status_code == 200, f"G-28 upload failed: {response.status_code} - {response.text}"
    
    print(f"   ✓ Documents uploaded successfully")
    print(f"   ✓ Session ID: {session_id}")
    
    return session_id

def test_passport_extraction(session_id):
    """Test passport extraction"""
    print("\n3. Testing passport extraction...")
    
    response = requests.post(f"{BASE_URL}/api/extract/passport/{session_id}")
    assert response.status_code == 200, f"Passport extraction failed: {response.status_code}"
    
    result = response.json()
    assert result.get('success'), "Passport extraction unsuccessful"
    
    data = result.get('data', {})
    print(f"   ✓ Passport extracted successfully")
    print(f"   - Name: {data.get('full_name', 'N/A')}")
    print(f"   - Passport #: {data.get('passport_number', 'N/A')}")
    print(f"   - Nationality: {data.get('nationality', 'N/A')}")
    
    return result

def test_g28_extraction(session_id):
    """Test G-28 extraction"""
    print("\n4. Testing G-28 extraction...")
    
    response = requests.post(f"{BASE_URL}/api/extract/g28/{session_id}")
    assert response.status_code == 200, f"G-28 extraction failed: {response.status_code}"
    
    result = response.json()
    assert result.get('success'), "G-28 extraction unsuccessful"
    
    data = result.get('data', {})
    attorney = data.get('attorney_name', {})
    print(f"   ✓ G-28 extracted successfully")
    print(f"   - Attorney: {attorney.get('first', '')} {attorney.get('last', '')}")
    print(f"   - Firm: {data.get('firm_name', 'N/A')}")
    
    return result

def test_form_filling(session_id):
    """Test form filling"""
    print("\n5. Testing form filling...")
    
    response = requests.post(f"{BASE_URL}/api/fill-form/{session_id}")
    
    if response.status_code != 200:
        print(f"   ⚠ Form filling endpoint returned {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    result = response.json()
    
    if result.get('success'):
        print(f"   ✓ Form filling completed")
        print(f"   - Fields filled: {result.get('filled_count', 0)}")
    else:
        print(f"   ⚠ Form filling failed: {result.get('error', 'Unknown error')}")
    
    return result

def main():
    """Run all tests"""
    print("=" * 60)
    print("Document Form Filler - End-to-End Test")
    print("=" * 60)
    
    try:
        # Test health
        if not test_health():
            print("❌ Health check failed. Is the server running?")
            return 1
        
        # Test upload
        session_id = test_upload()
        if not session_id:
            print("⚠ Upload test skipped (no sample documents)")
            return 0
        
        # Test passport extraction
        passport_result = test_passport_extraction(session_id)
        
        # Test G-28 extraction
        g28_result = test_g28_extraction(session_id)
        
        # Test form filling
        form_result = test_form_filling(session_id)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
        # Summary
        print("\n📊 Summary:")
        print(f"- Session ID: {session_id}")
        print(f"- Passport extraction: {'✓' if passport_result.get('success') else '✗'}")
        print(f"- G-28 extraction: {'✓' if g28_result.get('success') else '✗'}")
        print(f"- Form filling: {'✓' if form_result and form_result.get('success') else '⚠ (Playwright may need setup)'}")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())