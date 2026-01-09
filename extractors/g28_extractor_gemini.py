"""
G-28 Form Data Extraction Module using Google Gemini Vision
Superior OCR and document understanding for G-28 forms
"""

import re
import json
import sys
import os
from typing import Dict, Optional
from pathlib import Path
import numpy as np
from PIL import Image
import pdf2image
import google.generativeai as genai

# Add parent directory to path to import validators
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validators import FieldValidator

class G28ExtractorGemini:
    """Extract data from G-28 forms using Gemini Vision API"""
    
    def __init__(self):
        self.confidence = 0.0
        self.extraction_method = None
        
        # Initialize Gemini client
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if gemini_api_key and gemini_api_key != 'your_gemini_api_key_here':
            try:
                # Configure with API key
                genai.configure(api_key=gemini_api_key)
                
                # Use gemini-2.5-flash for best vision capabilities
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                print(f"[G28] Gemini Vision API initialized with gemini-2.5-flash")
            except Exception as e:
                print(f"[G28] Failed to initialize Gemini: {str(e)}")
                self.gemini_model = None
        else:
            print("[G28] Warning: GEMINI_API_KEY not configured. Extraction may fail.")
            self.gemini_model = None
    
    def extract(self, file_path: str) -> Dict:
        """
        Main extraction method using Gemini Vision
        
        Args:
            file_path: Path to G-28 form image or PDF
            
        Returns:
            Dictionary with extracted G-28 data
        """
        try:
            print(f"[G28] Starting extraction for: {file_path}")
            
            # Extract with Gemini Vision
            if self.gemini_model:
                result = self.extract_with_gemini(file_path)
                if result:
                    print(f"[G28] Gemini extraction found {len([v for v in result.values() if v])} fields")
                    self.extraction_method = 'gemini'
                    return self.format_output(result)
            
            print(f"[G28] Extraction failed, returning empty result")
            return self.format_output({})
            
        except Exception as e:
            print(f"[G28] Extraction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.format_output({})
    
    def extract_with_gemini(self, file_path: str) -> Optional[Dict]:
        """
        Extract G-28 form data using Gemini Vision API
        
        Args:
            file_path: Path to G-28 form
            
        Returns:
            Dictionary with extracted data or None if extraction fails
        """
        try:
            # Load image or convert PDF to image
            if file_path.lower().endswith('.pdf'):
                # Convert PDF to image
                images = pdf2image.convert_from_path(file_path, dpi=300)
                if images:
                    image = images[0]  # Use first page
                else:
                    print("[G28] Failed to convert PDF to image")
                    return None
            else:
                # Load image directly
                image = Image.open(file_path)
            
            # Create extraction prompt
            prompt = """
            Analyze this G-28 form (Notice of Entry of Appearance as Attorney or Representative) and extract ALL information.
            
            Focus on these sections:
            
            1. ATTORNEY/REPRESENTATIVE INFORMATION:
               - Name (Last, First, Middle)
               - Firm/Organization name
               - Complete address (Street, Apt/Suite, City, State, ZIP)
               - Phone numbers (Daytime, Mobile, Fax)
               - Email address
            
            2. ELIGIBILITY/LICENSING:
               - Attorney bar number and state
               - Law student/graduate status
               - Accredited representative info
               - USCIS Online Account Number
            
            3. CLIENT INFORMATION (Part 2):
               - Client's name
               - Client's address
               - A-Number (if present)
            
            4. SIGNATURE SECTION:
               - Attorney/Representative signature date
               - Client consent signature date
            
            Extract and return a JSON object with this structure:
            {
                "attorney_name": {
                    "last": "last name",
                    "first": "first name",
                    "middle": "middle name"
                },
                "firm_name": "firm or organization name",
                "address": {
                    "street": "street address",
                    "apt_suite": "apartment or suite number",
                    "city": "city",
                    "state": "state abbreviation",
                    "zip": "ZIP code",
                    "country": "country if specified"
                },
                "contact": {
                    "phone": "daytime phone",
                    "mobile": "mobile number",
                    "email": "email address",
                    "fax": "fax number"
                },
                "eligibility": {
                    "type": "attorney/law_student/accredited",
                    "bar_number": "bar number if attorney",
                    "bar_state": "state of bar admission",
                    "uscis_account": "USCIS online account number"
                },
                "client": {
                    "name": "client full name",
                    "a_number": "alien registration number",
                    "address": "client address"
                }
            }
            
            Important:
            - Extract phone numbers without formatting (just digits)
            - State should be 2-letter abbreviation (e.g., CA, NY, TX)
            - Bar number should include all characters/digits
            - If a field is not found or empty, use null
            
            Return ONLY valid JSON, no other text.
            """
            
            # Generate content with Gemini
            response = self.gemini_model.generate_content([prompt, image])
            
            # Extract JSON from response
            response_text = response.text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Add confidence score
                result['confidence'] = 0.95  # High confidence for Gemini
                
                print(f"[G28-Gemini] Successfully extracted {len([v for v in self._flatten_dict(result).values() if v])} fields")
                return result
            
            print("[G28-Gemini] Failed to extract valid JSON from response")
            return None
            
        except Exception as e:
            print(f"[G28-Gemini] Extraction failed: {str(e)}")
            return None
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """
        Flatten nested dictionary for counting non-empty fields
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def format_output(self, data: Dict) -> Dict:
        """
        Format extraction output to standard structure
        
        Args:
            data: Raw extraction data
            
        Returns:
            Formatted output dictionary
        """
        # Prepare extracted data with default structure
        extracted_data = {
            'attorney_name': data.get('attorney_name', {}),
            'firm_name': data.get('firm_name', ''),
            'address': data.get('address', {}),
            'contact': data.get('contact', {}),
            'eligibility': data.get('eligibility', {}),
            'client': data.get('client', {})
        }
        
        # Validate extracted data
        validator = FieldValidator(strict_mode=False)
        
        # Flatten for validation
        flat_data = {}
        
        # Add attorney name fields
        if extracted_data.get('attorney_name'):
            flat_data['attorney_last_name'] = extracted_data['attorney_name'].get('last', '')
            flat_data['attorney_first_name'] = extracted_data['attorney_name'].get('first', '')
            flat_data['attorney_middle_name'] = extracted_data['attorney_name'].get('middle', '')
        
        # Add contact fields
        if extracted_data.get('contact'):
            flat_data['phone'] = extracted_data['contact'].get('phone', '')
            flat_data['mobile'] = extracted_data['contact'].get('mobile', '')
            flat_data['email'] = extracted_data['contact'].get('email', '')
            flat_data['fax'] = extracted_data['contact'].get('fax', '')
        
        # Add address fields
        if extracted_data.get('address'):
            flat_data['zip'] = extracted_data['address'].get('zip', '')
        
        # Add eligibility fields
        if extracted_data.get('eligibility'):
            flat_data['bar_number'] = extracted_data['eligibility'].get('bar_number', '')
        
        validation_result = validator.validate_all_fields(flat_data)
        
        return {
            'success': bool(data),
            'data': extracted_data,
            'validation': {
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'total_errors': validation_result['total_errors'],
                'total_warnings': validation_result['total_warnings']
            },
            'confidence': data.get('confidence', 0.0),
            'method': self.extraction_method or 'none'
        }