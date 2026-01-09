"""
Enhanced Passport Data Extraction Module using Google Gemini Vision
Superior OCR and document understanding for international passports
"""

import re
import json
import sys
import os
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
import numpy as np
from PIL import Image
from passporteye import read_mrz
import pdf2image
import google.generativeai as genai

# Add parent directory to path to import validators
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validators import FieldValidator

# ISO 3166-1 alpha-3 country codes mapping
COUNTRY_CODES = {
    # Common countries
    'UNITED STATES': 'USA', 'UNITED STATES OF AMERICA': 'USA', 'USA': 'USA', 'US': 'USA',
    'UNITED KINGDOM': 'GBR', 'GREAT BRITAIN': 'GBR', 'UK': 'GBR', 'GB': 'GBR',
    'CANADA': 'CAN', 'CA': 'CAN',
    'AUSTRALIA': 'AUS', 'AU': 'AUS',
    'NETHERLANDS': 'NLD', 'HOLLAND': 'NLD', 'NL': 'NLD',
    'GERMANY': 'DEU', 'DE': 'DEU',
    'FRANCE': 'FRA', 'FR': 'FRA',
    'ITALY': 'ITA', 'IT': 'ITA',
    'SPAIN': 'ESP', 'ES': 'ESP',
    'INDIA': 'IND', 'IN': 'IND',
    'CHINA': 'CHN', 'CN': 'CHN',
    'JAPAN': 'JPN', 'JP': 'JPN',
    'KOREA': 'KOR', 'SOUTH KOREA': 'KOR', 'KR': 'KOR',
    'MEXICO': 'MEX', 'MX': 'MEX',
    'BRAZIL': 'BRA', 'BR': 'BRA',
    'ARGENTINA': 'ARG', 'AR': 'ARG',
    'RUSSIA': 'RUS', 'RUSSIAN FEDERATION': 'RUS', 'RU': 'RUS',
    'SAUDI ARABIA': 'SAU', 'SA': 'SAU',
    'UNITED ARAB EMIRATES': 'ARE', 'UAE': 'ARE', 'AE': 'ARE',
    'EGYPT': 'EGY', 'EG': 'EGY',
    'SOUTH AFRICA': 'ZAF', 'ZA': 'ZAF',
    'NIGERIA': 'NGA', 'NG': 'NGA',
    'KENYA': 'KEN', 'KE': 'KEN',
    'MOROCCO': 'MAR', 'MA': 'MAR',
    'POLAND': 'POL', 'PL': 'POL',
    'SWEDEN': 'SWE', 'SE': 'SWE',
    'NORWAY': 'NOR', 'NO': 'NOR',
    'DENMARK': 'DNK', 'DK': 'DNK',
    'BELGIUM': 'BEL', 'BE': 'BEL',
    'SWITZERLAND': 'CHE', 'CH': 'CHE',
    'AUSTRIA': 'AUT', 'AT': 'AUT',
    'PORTUGAL': 'PRT', 'PT': 'PRT',
    'GREECE': 'GRC', 'GR': 'GRC',
    'TURKEY': 'TUR', 'TR': 'TUR',
    'ISRAEL': 'ISR', 'IL': 'ISR',
    'SINGAPORE': 'SGP', 'SG': 'SGP',
    'MALAYSIA': 'MYS', 'MY': 'MYS',
    'THAILAND': 'THA', 'TH': 'THA',
    'PHILIPPINES': 'PHL', 'PH': 'PHL',
    'INDONESIA': 'IDN', 'ID': 'IDN',
    'PAKISTAN': 'PAK', 'PK': 'PAK',
    'BANGLADESH': 'BGD', 'BD': 'BGD',
    'VIETNAM': 'VNM', 'VN': 'VNM',
    'KUWAIT': 'KWT', 'KW': 'KWT',
    'QATAR': 'QAT', 'QA': 'QAT',
    'BAHRAIN': 'BHR', 'BH': 'BHR',
    'OMAN': 'OMN', 'OM': 'OMN',
    'JORDAN': 'JOR', 'JO': 'JOR',
    'LEBANON': 'LBN', 'LB': 'LBN',
}

# Reverse mapping: ISO code to full country name
ISO_TO_COUNTRY = {
    'USA': 'United States',
    'GBR': 'United Kingdom', 
    'CAN': 'Canada',
    'AUS': 'Australia',
    'NLD': 'Netherlands',
    'DEU': 'Germany',
    'FRA': 'France',
    'ITA': 'Italy',
    'ESP': 'Spain',
    'IND': 'India',
    'CHN': 'China',
    'JPN': 'Japan',
    'KOR': 'South Korea',
    'MEX': 'Mexico',
    'BRA': 'Brazil',
    'ARG': 'Argentina',
    'RUS': 'Russia',
    'SAU': 'Saudi Arabia',
    'ARE': 'United Arab Emirates',
    'EGY': 'Egypt',
    'ZAF': 'South Africa',
    'NGA': 'Nigeria',
    'KEN': 'Kenya',
    'MAR': 'Morocco',
    'POL': 'Poland',
    'UKR': 'Ukraine',
    'SWE': 'Sweden',
    'NOR': 'Norway',
    'DNK': 'Denmark',
    'FIN': 'Finland',
    'ISL': 'Iceland',
    'IRL': 'Ireland',
    'PRT': 'Portugal',
    'GRC': 'Greece',
    'TUR': 'Turkey',
    'ISR': 'Israel',
    'THA': 'Thailand',
    'SGP': 'Singapore',
    'MYS': 'Malaysia',
    'IDN': 'Indonesia',
    'PHL': 'Philippines',
    'VNM': 'Vietnam',
    'BGD': 'Bangladesh',
    'PAK': 'Pakistan',
    'AFG': 'Afghanistan',
    'IRN': 'Iran',
    'IRQ': 'Iraq',
    'SYR': 'Syria',
    'YEM': 'Yemen',
    'KWT': 'Kuwait',
    'QAT': 'Qatar',
    'BHR': 'Bahrain',
    'OMN': 'Oman',
    'JOR': 'Jordan',
    'LBN': 'Lebanon'
}

class PassportExtractorGemini:
    """Extract data from passport images using Gemini Vision API"""
    
    def __init__(self):
        self.mrz_data = None
        self.ocr_data = None
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
                print(f"[Passport] Gemini Vision API initialized with gemini-2.5-flash")
            except Exception as e:
                print(f"[Passport] Failed to initialize Gemini: {str(e)}")
                self.gemini_model = None
        else:
            print("[Passport] Warning: GEMINI_API_KEY not configured. Using fallback OCR.")
            self.gemini_model = None
    
    def extract(self, image_path: str) -> Dict:
        """
        Main extraction method using Gemini Vision as primary OCR
        
        Args:
            image_path: Path to passport image file
            
        Returns:
            Dictionary with extracted passport data
        """
        try:
            print(f"[Passport] Starting extraction for: {image_path}")
            
            # Step 1: Try Gemini Vision extraction (best accuracy)
            gemini_result = None
            if self.gemini_model:
                gemini_result = self.extract_with_gemini(image_path)
                if gemini_result:
                    print(f"[Passport] Gemini extraction found {len([v for v in gemini_result.values() if v])} fields")
            
            # Step 2: Try MRZ extraction as backup/validation
            mrz_result = self.extract_mrz(image_path)
            if mrz_result:
                print(f"[Passport] MRZ extraction found {len([v for v in mrz_result.values() if v])} fields")
            
            # Step 3: Merge results (Gemini for accuracy, MRZ for validation)
            final_result = self.merge_results(gemini_result, mrz_result)
            
            if final_result:
                print(f"[Passport] Final result has {len([v for v in final_result.values() if v])} fields")
                self.extraction_method = 'gemini+mrz' if gemini_result and mrz_result else ('gemini' if gemini_result else 'mrz')
                return self.format_output(final_result)
            
            print(f"[Passport] All extraction methods failed, returning empty result")
            return self.format_output({})
            
        except Exception as e:
            print(f"[Passport] Extraction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.format_output({})
    
    def extract_with_gemini(self, image_path: str) -> Optional[Dict]:
        """
        Extract passport data using Gemini Vision API
        
        Args:
            image_path: Path to passport image
            
        Returns:
            Dictionary with extracted data or None if extraction fails
        """
        try:
            # Load image
            image = Image.open(image_path)
            
            # Create extraction prompt
            prompt = """
            Analyze this passport image and extract ALL information. This could be a passport from any country including UAE, Saudi Arabia, or other Arabic countries.
            
            CRITICAL RULES FOR ARABIC/UAE PASSPORTS:
            1. Names with AL- or EL- prefixes: These are PART OF THE SURNAME
               - "SALEM AL-ALI" → surname="AL-ALI", given_names="SALEM"
               - "MOHAMMED BIN RASHID AL MAKTOUM" → surname="AL MAKTOUM", given_names="MOHAMMED BIN RASHID"
            
            2. DO NOT misread Arabic names as random letters like "ONG" or "SALEHSALE"
            
            3. Passport numbers can start with letters (e.g., X12A45678)
            
            4. For UAE: country_code="ARE", nationality="United Arab Emirates" (NOT just "ARE")
            
            5. Read BOTH the visual fields AND the MRZ (Machine Readable Zone) at the bottom
            
            Extract and return a JSON object with these fields:
            {
                "surname": "family/last name (include AL-/EL- if present)",
                "given_names": "first and middle names (exclude surname)",
                "passport_number": "complete passport number",
                "nationality": "3-letter code or full name",
                "country_code": "3-letter ISO code (ARE for UAE)",
                "date_of_birth": "YYYY-MM-DD format",
                "place_of_birth": "city/location",
                "sex": "M or F",
                "issue_date": "YYYY-MM-DD format",
                "expiry_date": "YYYY-MM-DD format"
            }
            
            Also extract the MRZ lines at the bottom if visible:
            - Line 1: P<country<<surname<<given<names
            - Line 2: passport<country<dob<sex<expiry
            
            Return ONLY valid JSON, no other text.
            """
            
            # Generate content with Gemini
            response = self.gemini_model.generate_content([prompt, image])
            
            # Extract JSON from response
            response_text = response.text
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Post-process dates
                result = self.post_process_gemini_result(result)
                
                print(f"[Passport-Gemini] Successfully extracted {len([v for v in result.values() if v])} fields")
                result['confidence'] = 0.95  # High confidence for Gemini
                return result
            
            print("[Passport-Gemini] Failed to extract valid JSON from response")
            return None
            
        except Exception as e:
            print(f"[Passport-Gemini] Extraction failed: {str(e)}")
            return None
    
    def post_process_gemini_result(self, result: Dict) -> Dict:
        """
        Post-process Gemini extraction results
        
        Args:
            result: Raw extraction from Gemini
            
        Returns:
            Processed result dictionary
        """
        # Ensure country code for UAE
        if result.get('nationality'):
            nationality_upper = str(result['nationality']).upper()
            if 'EMIRATES' in nationality_upper or 'UAE' in nationality_upper:
                result['country_code'] = 'ARE'
                result['nationality'] = 'United Arab Emirates'
            elif nationality_upper == 'ARE':
                result['country_code'] = 'ARE'
                result['nationality'] = 'United Arab Emirates'
        
        # Process dates to YYYY-MM-DD format
        date_fields = ['date_of_birth', 'issue_date', 'expiry_date']
        for field in date_fields:
            if result.get(field):
                result[field] = self.parse_date_flexible(result[field])
        
        # Validate sex field
        if result.get('sex'):
            sex_val = result['sex'].upper().strip()
            if sex_val in ['M', 'MALE']:
                result['sex'] = 'M'
            elif sex_val in ['F', 'FEMALE']:
                result['sex'] = 'F'
        
        return result
    
    def parse_date_flexible(self, date_str: str) -> str:
        """
        Parse date from various formats to YYYY-MM-DD
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_str:
            return ''
        
        date_str = str(date_str).strip()
        
        # Already in correct format?
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # Try different date patterns
        date_patterns = [
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY'),  # DD/MM/YYYY or DD-MM-YYYY
            (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', 'YMD'),  # YYYY-MM-DD
            (r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', 'DMonY'),  # 15 MAR 2016
        ]
        
        for pattern, format_type in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if format_type == 'DMY':
                        day, month, year = match.groups()
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    elif format_type == 'YMD':
                        year, month, day = match.groups()
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    elif format_type == 'DMonY':
                        day, month_str, year = match.groups()
                        months = {
                            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                        }
                        month = months.get(month_str.upper()[:3], '01')
                        return f"{year}-{month}-{int(day):02d}"
                except:
                    continue
        
        return date_str  # Return as-is if no pattern matches
    
    def extract_mrz(self, image_path: str) -> Optional[Dict]:
        """
        Extract data from passport MRZ (Machine Readable Zone)
        
        Args:
            image_path: Path to passport image
            
        Returns:
            Dictionary with MRZ data or None if extraction fails
        """
        try:
            # Try passporteye MRZ reading
            mrz = read_mrz(image_path)
            
            if not mrz:
                print("[Passport] No MRZ detected")
                return None
            
            # Parse MRZ data
            mrz_data = mrz.to_dict()
            
            result = {
                'surname': mrz_data.get('surname', ''),
                'given_names': mrz_data.get('names', ''),
                'passport_number': mrz_data.get('number', ''),
                'nationality': mrz_data.get('nationality', ''),
                'date_of_birth': self.format_mrz_date(mrz_data.get('date_of_birth', '')),
                'sex': mrz_data.get('sex', ''),
                'expiry_date': self.format_mrz_date(mrz_data.get('expiration_date', '')),
                'country_code': mrz_data.get('country', ''),
                'confidence': 0.85
            }
            
            print(f"[Passport-MRZ] Extraction successful")
            return result
            
        except Exception as e:
            print(f"[Passport-MRZ] Extraction failed: {str(e)}")
            return None
    
    def format_mrz_date(self, date_str: str) -> str:
        """
        Format MRZ date (YYMMDD) to standard format (YYYY-MM-DD)
        """
        if not date_str or len(str(date_str)) != 6:
            return ''
        
        try:
            year = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            # Validate month and day
            if month < 1 or month > 12 or day < 1 or day > 31:
                return ''
            
            # Determine century
            current_year = datetime.now().year
            if year > (current_year % 100) + 10:
                year += 1900
            else:
                year += 2000
            
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return ''
    
    def merge_results(self, gemini_result: Optional[Dict], mrz_result: Optional[Dict]) -> Dict:
        """
        Merge Gemini and MRZ results intelligently
        
        Args:
            gemini_result: Result from Gemini Vision extraction
            mrz_result: Result from MRZ extraction
            
        Returns:
            Merged result dictionary
        """
        if not gemini_result and not mrz_result:
            return {}
        
        if not mrz_result:
            return gemini_result or {}
        
        if not gemini_result:
            return mrz_result or {}
        
        # Start with Gemini result (more accurate OCR)
        merged = gemini_result.copy()
        
        # Use MRZ for validation of critical fields
        # But only override if Gemini's version looks suspicious
        if mrz_result.get('passport_number'):
            # Check if Gemini passport number is incomplete
            if not merged.get('passport_number') or len(merged.get('passport_number', '')) < len(mrz_result['passport_number']):
                merged['passport_number'] = mrz_result['passport_number']
        
        # For dates, prefer non-empty values
        date_fields = ['date_of_birth', 'expiry_date']
        for field in date_fields:
            if not merged.get(field) and mrz_result.get(field):
                merged[field] = mrz_result[field]
        
        # Ensure country code consistency
        if merged.get('nationality') == 'ARE' or merged.get('country_code') == 'ARE':
            merged['country_code'] = 'ARE'
            merged['nationality'] = 'United Arab Emirates'
        
        # Set confidence based on agreement
        gemini_conf = gemini_result.get('confidence', 0)
        mrz_conf = mrz_result.get('confidence', 0)
        merged['confidence'] = max(gemini_conf, mrz_conf)
        
        return merged
    
    def format_output(self, data: Dict) -> Dict:
        """
        Format extraction output to standard structure
        
        Args:
            data: Raw extraction data
            
        Returns:
            Formatted output dictionary
        """
        # Extract names properly
        surname = (data.get('surname') or '').strip()
        given_names = (data.get('given_names') or '').strip()
        
        # Extract first name from given names if needed
        first_name = given_names
        middle_name = ''
        if given_names:
            parts = given_names.split()
            if len(parts) > 1:
                first_name = parts[0]
                middle_name = ' '.join(parts[1:])
        
        # Create full name in proper order
        full_name_parts = []
        if first_name:
            full_name_parts.append(first_name)
        if middle_name:
            full_name_parts.append(middle_name)
        if surname:
            full_name_parts.append(surname)
        full_name = ' '.join(full_name_parts)
        
        # Convert ISO code to full country name for nationality
        nationality = data.get('nationality', '')
        if nationality and len(nationality) == 3 and nationality.upper() in ISO_TO_COUNTRY:
            nationality = ISO_TO_COUNTRY[nationality.upper()]
        
        # Prepare extracted data
        extracted_data = {
            'full_name': full_name,
            'last_name': surname,
            'first_name': first_name,
            'middle_name': middle_name,
            'passport_number': data.get('passport_number', ''),
            'nationality': nationality,
            'country_code': data.get('country_code', ''),
            'date_of_birth': data.get('date_of_birth', ''),
            'place_of_birth': data.get('place_of_birth', ''),
            'sex': data.get('sex', ''),
            'issue_date': data.get('issue_date', ''),
            'expiry_date': data.get('expiry_date', ''),
        }
        
        # Validate extracted data
        validator = FieldValidator(strict_mode=False)
        validation_result = validator.validate_all_fields(extracted_data)
        
        return {
            'success': bool(data),
            'data': validation_result['data'],
            'validation': {
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'total_errors': validation_result['total_errors'],
                'total_warnings': validation_result['total_warnings']
            },
            'confidence': data.get('confidence', 0.0),
            'method': self.extraction_method or 'none'
        }
    
    def get_country_code(self, country_name: str) -> str:
        """
        Get ISO 3-letter country code from country name
        """
        if not country_name:
            return ''
        
        country_upper = country_name.upper().strip()
        
        # Check if it's already a 3-letter code
        if len(country_upper) == 3 and country_upper.isalpha():
            return country_upper
        
        # Look up in mapping
        return COUNTRY_CODES.get(country_upper, '')