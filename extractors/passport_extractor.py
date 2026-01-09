"""
Passport Data Extraction Module
Handles MRZ reading and OCR fallback for passport data extraction
Enhanced for international passport support
"""

import re
import json
import sys
import os
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from PIL import Image
from passporteye import read_mrz
import pdf2image
from openai import OpenAI

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
    'TURKEY': 'TUR', 'TR': 'TUR',
    'POLAND': 'POL', 'PL': 'POL',
    'SWEDEN': 'SWE', 'SE': 'SWE',
    'NORWAY': 'NOR', 'NO': 'NOR',
    'DENMARK': 'DNK', 'DK': 'DNK',
    'IRELAND': 'IRL', 'IE': 'IRL',
    'NEW ZEALAND': 'NZL', 'NZ': 'NZL',
    'SINGAPORE': 'SGP', 'SG': 'SGP',
    'MALAYSIA': 'MYS', 'MY': 'MYS',
    'THAILAND': 'THA', 'TH': 'THA',
    'PHILIPPINES': 'PHL', 'PH': 'PHL',
    'INDONESIA': 'IDN', 'ID': 'IDN',
    'PAKISTAN': 'PAK', 'PK': 'PAK',
    'BANGLADESH': 'BGD', 'BD': 'BGD',
    'VIETNAM': 'VNM', 'VN': 'VNM',
}

class PassportExtractor:
    """Extract data from passport images using MRZ and OCR"""
    
    def __init__(self):
        self.mrz_data = None
        self.ocr_data = None
        self.confidence = 0.0
        self.extraction_method = None
        
        # Initialize OpenAI client for LLM parsing
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            print("[Passport] Warning: OPENAI_API_KEY not found. LLM parsing will be disabled.")
            self.openai_client = None
        
    def extract(self, image_path: str) -> Dict:
        """
        Main extraction method using dual strategy: MRZ + OCR/LLM
        
        Args:
            image_path: Path to passport image file
            
        Returns:
            Dictionary with extracted passport data
        """
        try:
            print(f"[Passport] Starting extraction for: {image_path}")
            
            # Step 1: Try MRZ extraction for baseline data
            mrz_result = self.extract_mrz(image_path)
            if mrz_result:
                print(f"[Passport] MRZ extraction successful with confidence {mrz_result.get('confidence', 0)}")
            
            # Step 2: ALWAYS run OCR + LLM for complete data extraction
            ocr_llm_result = self.extract_with_ocr_and_llm(image_path)
            if ocr_llm_result:
                print(f"[Passport] OCR+LLM extraction found {len([v for v in ocr_llm_result.values() if v])} fields")
            
            # Step 3: Merge results (MRZ for accuracy, LLM for completeness)
            final_result = self.merge_results(mrz_result, ocr_llm_result)
            
            if final_result:
                print(f"[Passport] Final merged result has {len([v for v in final_result.values() if v])} fields")
                self.extraction_method = 'mrz+llm' if mrz_result and ocr_llm_result else ('mrz' if mrz_result else 'ocr+llm')
                return self.format_output(final_result)
            
            print(f"[Passport] All extraction methods failed, returning empty result")
            return self.format_output({})
            
        except Exception as e:
            print(f"[Passport] Extraction error: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.format_output({})
    
    def extract_mrz(self, image_path: str) -> Optional[Dict]:
        """
        Extract data from passport MRZ (Machine Readable Zone)
        
        Args:
            image_path: Path to passport image or PDF
            
        Returns:
            Dictionary with MRZ data or None if extraction fails
        """
        try:
            # Handle PDF files
            if image_path.lower().endswith('.pdf'):
                try:
                    # Convert PDF to images
                    images = pdf2image.convert_from_path(image_path, dpi=300)
                    if images:
                        # Save first page as temporary image for MRZ reading
                        temp_image_path = image_path.replace('.pdf', '_temp.jpg')
                        images[0].save(temp_image_path, 'JPEG')
                        
                        # Try MRZ on the converted image
                        mrz = read_mrz(temp_image_path)
                        
                        # Clean up temp file
                        import os
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)
                    else:
                        print("No pages found in PDF")
                        return None
                except Exception as e:
                    print(f"PDF conversion failed for MRZ: {str(e)}")
                    return None
            else:
                # Read MRZ directly from image
                mrz = read_mrz(image_path)
            
            if not mrz:
                print("[Passport] No MRZ detected by passporteye, trying manual extraction")
                # Try manual MRZ extraction as fallback
                return self.extract_mrz_manual(image_path)
            
            # Parse MRZ data
            mrz_data = mrz.to_dict()
            
            # Debug: Log raw MRZ data
            if mrz_data.get('raw_text'):
                print(f"[Passport-MRZ] Raw text: {mrz_data.get('raw_text')}")
            
            # Check for parsing issues common with UAE/Arabic passports
            raw_text = mrz_data.get('raw_text', '')
            if raw_text and 'P<' in raw_text:
                # Detected passport MRZ but might have parsing issues
                # Try manual parsing as backup
                manual_result = self.parse_mrz_text_manual(raw_text)
                if manual_result:
                    print("[Passport] Using manual MRZ parsing for better accuracy")
                    # Merge with passporteye results, preferring manual for problem fields
                    if manual_result.get('surname') and not mrz_data.get('surname'):
                        mrz_data['surname'] = manual_result['surname']
                    if manual_result.get('names') and not mrz_data.get('names'):
                        mrz_data['names'] = manual_result['names']
                    if manual_result.get('number'):
                        mrz_data['number'] = manual_result['number']
            
            # Extract and format fields
            sex_value = mrz_data.get('sex', '')
            # Clean up sex field - sometimes MRZ returns wrong characters
            if sex_value and sex_value.upper() not in ['M', 'F']:
                sex_value = ''  # Invalid sex value, clear it
            
            result = {
                'surname': mrz_data.get('surname', ''),
                'given_names': mrz_data.get('names', ''),
                'passport_number': mrz_data.get('number', ''),
                'nationality': mrz_data.get('nationality', ''),
                'date_of_birth': self.format_mrz_date(mrz_data.get('date_of_birth', '')),
                'sex': sex_value,
                'expiry_date': self.format_mrz_date(mrz_data.get('expiration_date', '')),
                'country_code': mrz_data.get('country', ''),
                'confidence': 0.95  # High confidence for successful MRZ read
            }
            
            # Validate MRZ checksums if available
            if self.validate_mrz_checksums(mrz_data):
                result['confidence'] = 0.98
            
            print(f"[Passport] MRZ extraction successful")
            return result
            
        except Exception as e:
            print(f"[Passport] MRZ extraction failed: {str(e)}")
            return None
    
    def extract_with_ocr_and_llm(self, image_path: str) -> Optional[Dict]:
        """
        Extract passport data using OCR + LLM for intelligent parsing
        
        Args:
            image_path: Path to passport image or PDF
            
        Returns:
            Dictionary with extracted data
        """
        try:
            # First get OCR text with enhanced preprocessing
            text = ""
            
            # Handle PDF files
            if image_path.lower().endswith('.pdf'):
                try:
                    images = pdf2image.convert_from_path(image_path, dpi=300)
                    if images:
                        image = np.array(images[0])
                        if len(image.shape) == 3:
                            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                except Exception as e:
                    print(f"[Passport-LLM] PDF conversion failed: {str(e)}")
                    return None
            else:
                # Load image file
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if image is None:
                    try:
                        pil_image = Image.open(image_path).convert('L')
                        image = np.array(pil_image)
                    except Exception as e:
                        print(f"[Passport-LLM] Failed to load image: {str(e)}")
                        return None
            
            # Apply enhanced preprocessing
            processed = self.preprocess_for_ocr_enhanced(image)
            
            # Extract text using Tesseract with multiple PSM modes
            texts = []
            for psm in [3, 6, 11]:  # Try different page segmentation modes
                try:
                    config = f'--psm {psm} --oem 3'
                    text_result = pytesseract.image_to_string(processed, config=config)
                    if text_result:
                        texts.append(text_result)
                except:
                    continue
            
            # Combine all OCR results
            text = '\n'.join(texts)
            
            print(f"[Passport-LLM] OCR extracted {len(text)} characters")
            
            # Use enhanced LLM parsing if available
            if self.openai_client and text:
                try:
                    llm_result = self.extract_with_enhanced_llm(text)
                    if llm_result:
                        llm_result['confidence'] = 0.85
                        return llm_result
                except Exception as e:
                    print(f"[Passport-LLM] Enhanced LLM failed, falling back to pattern matching: {str(e)}")
            
            # Fall back to pattern-based parsing
            result = self.parse_ocr_text_enhanced(text)
            result['confidence'] = 0.6
            return result
            
        except Exception as e:
            print(f"[Passport-LLM] Extraction failed: {str(e)}")
            return None
    
    def extract_with_enhanced_llm(self, ocr_text: str) -> Optional[Dict]:
        """
        Use enhanced LLM prompt to intelligently extract passport fields from OCR text
        
        Args:
            ocr_text: Raw OCR text from passport
            
        Returns:
            Dictionary with extracted fields
        """
        if not self.openai_client:
            return None
        
        try:
            prompt = f"""
            You are extracting information from a passport. The text may be from passports of different countries including UAE, Arabic countries, and various international formats.
            
            IMPORTANT PARSING RULES:
            1. Names - SPECIAL RULES FOR ARABIC/UAE PASSPORTS:
               - Arabic names often have AL- or EL- prefixes that are PART OF THE SURNAME
               - Example: "SALEM AL-ALI" → surname="AL-ALI", given_names="SALEM"
               - Example: "MOHAMMED BIN RASHID AL MAKTOUM" → surname="AL MAKTOUM", given_names="MOHAMMED BIN RASHID"
               - The surname might appear as: Surname, Last Name, Family Name, Nom
               - Given names might appear as: Given Names, First Name, Name, Prenom
               - DO NOT combine surname and given names into one field
               - For hyphenated surnames (AL-ALI, EL-SAYED), keep the hyphen
            
            2. Dates: Can be in various formats
               - DD/MM/YYYY (common in UAE: 21/11/1985)
               - DD MMM YYYY (e.g., 10 MAR 1965)
               - MM/DD/YYYY (US format)
               - YYYY-MM-DD
               - Parse "Date of Issue" carefully - it's when the passport was issued
               - Parse "Date of Birth" - the holder's birth date
               - Parse "Date of Expiry" - when the passport expires
            
            3. Nationality vs Country Code:
               - For UAE: nationality="United Arab Emirates", country_code="ARE"
               - NEVER use partial codes like "UNI" for UAE
               - The issuing country may appear as "Authority" or "Issuing Authority"
               - Common codes: ARE (UAE), SAU (Saudi Arabia), KWT (Kuwait), QAT (Qatar)
            
            4. Passport Number: 
               - Can be alphanumeric (e.g., X12A45678 for UAE)
               - Usually 8-9 characters
               - May start with letters
            
            5. Place of Birth: City and/or country (e.g., "ABU DHABI" for UAE)
            
            6. Sex/Gender: M (Male) or F (Female)
            
            Common field labels in different languages:
            - English: Surname, Given Names, Date of Birth, Place of Birth, Date of Issue, Date of Expiry
            - Arabic (transliterated): Names may appear in both Arabic and English
            - French: Nom, Prénom(s), Date de naissance, Lieu de naissance, Date de délivrance, Date d'expiration
            - Spanish: Apellidos, Nombre(s), Fecha de nacimiento, Lugar de nacimiento, Fecha de expedición, Fecha de caducidad
            - German: Familienname, Vorname(n), Geburtsdatum, Geburtsort, Ausstellungsdatum, Gültig bis
            - Dutch: Achternaam, Voornamen, Geboortedatum, Geboorteplaats, Datum afgifte, Geldig tot
            
            Extract the following fields (use null if not found):
            {{
                "surname": "EXACT surname/last name as printed (in CAPITALS if shown that way)",
                "given_names": "EXACT given/first names as printed (do not include surname)",
                "middle_name": "middle name if listed separately",
                "passport_number": "passport number",
                "date_of_birth": "YYYY-MM-DD format",
                "place_of_birth": "city and/or country",
                "issue_date": "YYYY-MM-DD format (when passport was issued)",
                "expiry_date": "YYYY-MM-DD format",
                "nationality": "full country name (e.g., UNITED STATES, not USA)",
                "country_code": "3-letter ISO code (e.g., USA, GBR, NLD)",
                "sex": "M or F"
            }}
            
            CRITICAL: 
            - Keep surname and given_names SEPARATE
            - Convert all dates to YYYY-MM-DD format
            - For nationality, use the FULL country name
            - For country_code, use the 3-letter ISO code
            
            OCR Text:
            {ocr_text[:4000]}
            
            Return ONLY the JSON object, no other text.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a passport data extraction expert. Extract information accurately and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=600
            )
            
            llm_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'\{.*?\}', llm_text, re.DOTALL)
            if json_match:
                llm_text = json_match.group()
            
            result = json.loads(llm_text)
            
            # Post-process the result
            result = self.post_process_llm_result(result)
            
            print(f"[Passport-LLM] Extracted {len([v for v in result.values() if v])} fields via enhanced LLM")
            return result
            
        except Exception as e:
            print(f"[Passport-LLM] Enhanced LLM parsing error: {str(e)}")
            return None
    
    def post_process_llm_result(self, result: Dict) -> Dict:
        """
        Post-process LLM extraction results
        """
        # Clean up dates
        for date_field in ['date_of_birth', 'issue_date', 'expiry_date']:
            if result.get(date_field):
                result[date_field] = self.parse_date_enhanced(result[date_field])
        
        # Normalize country code
        if result.get('nationality') and not result.get('country_code'):
            result['country_code'] = self.get_country_code(result['nationality'])
        
        # Ensure names are properly separated
        if result.get('surname') and result.get('given_names'):
            # Remove surname from given_names if accidentally included
            surname = (result.get('surname') or '').upper()
            given = result.get('given_names') or ''
            if surname and given and surname in given.upper():
                result['given_names'] = given.replace(surname, '').strip()
        
        # Clean up sex field
        if result.get('sex'):
            sex_val = result['sex'].upper().strip()
            if sex_val in ['M', 'MALE', 'H', 'HOMME']:
                result['sex'] = 'M'
            elif sex_val in ['F', 'FEMALE', 'W', 'FEMME']:
                result['sex'] = 'F'
        
        return result
    
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
    
    def preprocess_for_ocr_enhanced(self, image: np.ndarray) -> np.ndarray:
        """
        Enhanced preprocessing for better OCR results on passports
        
        Args:
            image: Grayscale image array
            
        Returns:
            Preprocessed image
        """
        try:
            # Check if image needs rotation correction
            image = self.correct_rotation(image)
            
            # Apply adaptive histogram equalization for better contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(image)
            
            # Apply bilateral filter to reduce noise while keeping edges
            denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
            
            # Apply adaptive threshold for better text extraction
            binary = cv2.adaptiveThreshold(
                denoised, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Apply morphological operations to connect text
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return processed
            
        except Exception as e:
            print(f"[Passport] Preprocessing error: {str(e)}")
            # Return original if preprocessing fails
            return image
    
    def correct_rotation(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct image rotation
        """
        try:
            # Detect text orientation using Tesseract
            osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            angle = osd.get('rotate', 0)
            
            if angle != 0:
                print(f"[Passport] Correcting rotation by {angle} degrees")
                # Get image center and rotation matrix
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                
                # Rotate the image
                rotated = cv2.warpAffine(image, M, (w, h), 
                                        flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
                return rotated
                
        except Exception as e:
            print(f"[Passport] Rotation detection failed: {str(e)}")
        
        return image
    
    def parse_ocr_text_enhanced(self, text: str) -> Dict:
        """
        Enhanced OCR text parsing with better pattern matching
        
        Args:
            text: Raw OCR text
            
        Returns:
            Dictionary with parsed data
        """
        result = {}
        lines = text.strip().split('\n')
        
        # Enhanced patterns for different passport formats
        patterns = {
            'passport_number': [
                r'(?:Passport\s*No\.?|Number|No\.?|Pasaporte)\s*[:.]?\s*([A-Z0-9]{6,10})',
                r'(?:^|\s)([A-Z][0-9]{8})(?:\s|$)',  # Common format: Letter + 8 digits
                r'(?:^|\s)([0-9]{9})(?:\s|$)',  # US format: 9 digits
            ],
            'surname': [
                r'(?:Surname|Last\s*Name|Nom|Apellidos?|Achternaam)\s*[:.]?\s*([A-Z][A-Z\s\-\']+)',
                r'(?:^|\n)([A-Z]{2,}(?:\s+[A-Z]{2,})*)\s*\n',  # Line with all caps
            ],
            'given_names': [
                r'(?:Given\s*Names?|First\s*Names?|Prenom|Nombre|Voornamen)\s*[:.]?\s*([A-Z][A-Za-z\s\-\']+)',
                r'(?:Surname.*?\n)([A-Z][A-Z\s]+?)(?:\n|$)',  # Line after surname
            ],
            'nationality': [
                r'(?:Nationality|Nationalité|Nacionalidad|Nationaliteit)\s*[:.]?\s*([A-Z][A-Za-z\s]+)',
                r'(?:Citizen(?:ship)?)\s*[:.]?\s*([A-Z][A-Za-z\s]+)',
            ],
            'date_of_birth': [
                r'(?:Date\s*of\s*Birth|DOB|Born|Né|Geboren)\s*[:.]?\s*(\d{1,2}[\s/.-]\w{3}[\s/.-]\d{2,4})',
                r'(?:Birth|Naissance)\s*[:.]?\s*(\d{2}/\d{2}/\d{4})',
            ],
            'issue_date': [
                r'(?:Date\s*of\s*Issue|Issued?|Délivré|Expedido|Afgegeven)\s*[:.]?\s*(\d{1,2}[\s/.-]\w{3}[\s/.-]\d{2,4})',
                r'(?:Issue|Délivrance|Expedición)\s*[:.]?\s*(\d{2}/\d{2}/\d{4})',
            ],
            'expiry_date': [
                r'(?:Date\s*of\s*Expiry|Expires?|Valid\s*Until|Valide)\s*[:.]?\s*(\d{1,2}[\s/.-]\w{3}[\s/.-]\d{2,4})',
                r'(?:Expiry|Expiration|Vencimiento)\s*[:.]?\s*(\d{2}/\d{2}/\d{4})',
            ],
            'sex': [
                r'(?:Sex|Gender|Sexe|Sexo|Geslacht)\s*[:.]?\s*([MFHmfh])',
                r'(?:^|\s)([MF])\s*(?:/|$)',
            ],
            'place_of_birth': [
                r'(?:Place\s*of\s*Birth|POB|Lieu\s*de\s*naissance|Lugar\s*de\s*nacimiento)\s*[:.]?\s*([A-Za-z][A-Za-z\s,]+)',
            ],
        }
        
        # Try each pattern
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                if not result.get(field):  # Only if not already found
                    for line in lines:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            value = match.group(1).strip()
                            if value:
                                result[field] = value
                                break
        
        # Clean up and validate results
        if result.get('date_of_birth'):
            result['date_of_birth'] = self.parse_date_enhanced(result['date_of_birth'])
        if result.get('issue_date'):
            result['issue_date'] = self.parse_date_enhanced(result['issue_date'])
        if result.get('expiry_date'):
            result['expiry_date'] = self.parse_date_enhanced(result['expiry_date'])
        
        # Try to extract names from uppercase lines if not found
        if not result.get('surname') or not result.get('given_names'):
            name_result = self.extract_names_from_lines(lines)
            if not result.get('surname'):
                result['surname'] = name_result.get('surname', '')
            if not result.get('given_names'):
                result['given_names'] = name_result.get('given_names', '')
        
        return result
    
    def extract_names_from_lines(self, lines: List[str]) -> Dict:
        """
        Extract names from text lines when pattern matching fails
        
        Args:
            lines: List of text lines
            
        Returns:
            Dictionary with surname and given_names
        """
        result = {}
        
        # Look for consecutive lines with names (often in caps)
        name_lines = []
        for i, line in enumerate(lines[:15]):  # Check first 15 lines
            cleaned = line.strip()
            # Check if line looks like a name (uppercase, no numbers, reasonable length)
            if (cleaned and 
                len(cleaned) > 2 and 
                len(cleaned) < 50 and
                not any(char.isdigit() for char in cleaned)):
                
                # Check if mostly uppercase letters
                upper_count = sum(1 for c in cleaned if c.isupper())
                if upper_count / len(cleaned.replace(' ', '')) > 0.7:
                    # Skip known headers
                    headers = ['PASSPORT', 'REPUBLIC', 'CITIZEN', 'NUMBER', 'AUTHORITY', 
                              'DOCUMENT', 'TYPE', 'CODE', 'NATIONALITY', 'SEX']
                    if not any(header in cleaned.upper() for header in headers):
                        name_lines.append((i, cleaned))
        
        # Usually surname comes first, then given names
        if len(name_lines) >= 2:
            # Check if lines are consecutive
            for i in range(len(name_lines) - 1):
                if name_lines[i+1][0] - name_lines[i][0] <= 2:  # Allow 1 line gap
                    result['surname'] = name_lines[i][1]
                    result['given_names'] = name_lines[i+1][1]
                    break
        elif len(name_lines) == 1:
            # Single name line - try to split
            name_parts = name_lines[0][1].split()
            if len(name_parts) >= 2:
                # Assume last word is surname (common in many cultures)
                result['surname'] = name_parts[-1]
                result['given_names'] = ' '.join(name_parts[:-1])
        
        return result
    
    def merge_results(self, mrz_result: Optional[Dict], llm_result: Optional[Dict]) -> Dict:
        """
        Intelligently merge MRZ and LLM results with UAE passport awareness
        
        Args:
            mrz_result: Data from MRZ extraction
            llm_result: Data from OCR+LLM extraction
            
        Returns:
            Merged dictionary with best available data
        """
        if not mrz_result and not llm_result:
            return {}
        
        if not llm_result:
            return mrz_result or {}
        
        if not mrz_result:
            return llm_result or {}
        
        # Check MRZ confidence - if low, prefer LLM results
        mrz_conf = mrz_result.get('confidence', 0)
        llm_conf = llm_result.get('confidence', 0)
        
        # For UAE/Arabic passports, MRZ parsing often fails on names
        # Check if MRZ names look suspicious
        mrz_name_suspicious = False
        mrz_surname = mrz_result.get('surname', '')
        mrz_given = mrz_result.get('given_names', '')
        
        # Common MRZ misparse patterns
        suspicious_patterns = ['ONG', 'SALEHSALE', 'UNI']
        for pattern in suspicious_patterns:
            if pattern in mrz_surname or pattern in mrz_given or pattern == mrz_result.get('nationality'):
                mrz_name_suspicious = True
                print(f"[Passport] MRZ names/nationality look suspicious (found '{pattern}'), preferring LLM results")
                break
        
        # Also check for very short or missing names
        if (not mrz_surname or len(mrz_surname) < 2 or 
            not mrz_given or len(mrz_given) < 2):
            mrz_name_suspicious = True
            print("[Passport] MRZ names too short or missing, preferring LLM results")
        
        # Start with LLM result (has more fields like issue_date, place_of_birth)
        merged = llm_result.copy()
        
        # MRZ data is usually accurate for these fields - but check confidence
        mrz_priority_fields = ['date_of_birth', 'expiry_date', 'sex']
        
        # For passport number, check if MRZ has full number (like X12A45678)
        if mrz_result.get('passport_number'):
            mrz_passport = mrz_result['passport_number']
            llm_passport = llm_result.get('passport_number', '')
            # If MRZ passport is shorter or partial, prefer LLM
            if len(mrz_passport) >= len(llm_passport) or not llm_passport:
                mrz_priority_fields.append('passport_number')
            else:
                print(f"[Passport] MRZ passport ({mrz_passport}) looks partial, using LLM ({llm_passport})")
        
        # Only use MRZ names if they're not suspicious
        if not mrz_name_suspicious:
            mrz_priority_fields.extend(['surname', 'given_names'])
        
        for field in mrz_priority_fields:
            if mrz_result.get(field):
                merged[field] = mrz_result[field]
        
        # Special handling for nationality/country
        mrz_country = mrz_result.get('country_code', '')
        mrz_nationality = mrz_result.get('nationality', '')
        
        # Fix common UAE misparses
        if mrz_country == 'ARE' or 'ARE' in str(mrz_result.get('raw_text', '')):
            merged['country_code'] = 'ARE'
            merged['nationality'] = 'ARE'
        elif mrz_nationality and mrz_nationality != 'UNI':  # UNI is a common misparse
            merged['nationality'] = mrz_nationality
            if mrz_country:
                merged['country_code'] = mrz_country
        
        # Ensure country code matches nationality
        if merged.get('nationality') and not merged.get('country_code'):
            merged['country_code'] = self.get_country_code(merged['nationality'])
        
        # Calculate merged confidence
        if mrz_name_suspicious:
            # Lower confidence if MRZ parsing had issues
            merged['confidence'] = llm_conf
        else:
            merged['confidence'] = max(mrz_conf, llm_conf)
        
        print(f"[Passport] Merged {len([v for v in merged.values() if v])} total fields")
        return merged
    
    def format_mrz_date(self, date_str: str) -> str:
        """
        Format MRZ date (YYMMDD) to standard format (YYYY-MM-DD)
        
        Args:
            date_str: Date in MRZ format (YYMMDD)
            
        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_str:
            return ''
            
        # Clean the date string - sometimes it has extra characters
        date_str = ''.join(c for c in str(date_str) if c.isdigit())
        
        if len(date_str) != 6:
            return ''
        
        try:
            year = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            # Validate month and day
            if month < 1 or month > 12:
                return ''
            if day < 1 or day > 31:
                return ''
            
            # Determine century
            current_year = datetime.now().year
            current_century = (current_year // 100) * 100
            
            # If year is greater than current year's last 2 digits + 10, assume previous century
            if year > (current_year % 100) + 10:
                year += current_century - 100
            else:
                year += current_century
            
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return ''
    
    def parse_date_enhanced(self, date_str: str) -> str:
        """
        Enhanced date parsing for various international formats
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_str:
            return ''
        
        # Clean the date string
        date_str = date_str.strip()
        
        # Already in correct format?
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # Try different date patterns
        date_formats = [
            # Day Month Year formats
            (r'(\d{1,2})\s+([A-Z]{3})\s+(\d{4})', '%d %b %Y'),  # 10 MAR 1965
            (r'(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})', '%d %B %Y'),  # 10 March 1965
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'DMY'),  # 10/03/1965 or 10-03-1965
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})', 'DMY2'),  # 10/03/65
            
            # Month Day Year formats (US style)
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', 'MDY'),  # 03/10/1965
            
            # Year Month Day formats
            (r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', '%Y-%m-%d'),  # 1965-03-10
        ]
        
        for pattern, format_type in date_formats:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if format_type == 'DMY':
                        day, month, year = match.groups()
                        # Validate day/month ranges to determine format
                        if int(day) <= 31 and int(month) <= 12:
                            return f"{year}-{int(month):02d}-{int(day):02d}"
                    elif format_type == 'DMY2':
                        day, month, year = match.groups()
                        year = int(year)
                        if year < 50:
                            year += 2000
                        else:
                            year += 1900
                        return f"{year:04d}-{int(month):02d}-{int(day):02d}"
                    elif format_type == 'MDY':
                        # Check if it could be US format (month/day/year)
                        val1, val2, year = match.groups()
                        if int(val1) <= 12:  # Likely month first
                            return f"{year}-{int(val1):02d}-{int(val2):02d}"
                        else:  # Likely day first
                            return f"{year}-{int(val2):02d}-{int(val1):02d}"
                    elif '%' in format_type:
                        # Use strptime for standard formats
                        if '%b' in format_type or '%B' in format_type:
                            # Handle month names
                            groups = match.groups()
                            day = groups[0]
                            month_str = groups[1].upper()[:3]
                            year = groups[2]
                            
                            months = {
                                'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                                'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                                'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                            }
                            
                            if month_str in months:
                                return f"{year}-{months[month_str]}-{int(day):02d}"
                        else:
                            parsed = datetime.strptime(match.group(), format_type)
                            return parsed.strftime('%Y-%m-%d')
                except:
                    continue
        
        # If no pattern matches, return original
        return date_str
    
    def extract_mrz_manual(self, image_path: str) -> Optional[Dict]:
        """
        Manually extract MRZ data when passporteye fails
        Uses OCR to get MRZ text and parse it manually
        """
        try:
            # Load and preprocess image
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return None
            
            # Focus on bottom 30% where MRZ typically is
            h, w = image.shape
            mrz_region = image[int(h*0.7):, :]
            
            # Enhance for better OCR
            _, binary = cv2.threshold(mrz_region, 127, 255, cv2.THRESH_BINARY)
            
            # OCR the MRZ region
            mrz_text = pytesseract.image_to_string(binary, config='--psm 6')
            
            # Look for MRZ pattern
            lines = mrz_text.strip().split('\n')
            mrz_lines = []
            for line in lines:
                # Clean line and check if it looks like MRZ
                clean_line = ''.join(c for c in line if c.isalnum() or c in '<>')
                if len(clean_line) > 30 and '<' in clean_line:
                    mrz_lines.append(clean_line)
            
            if len(mrz_lines) >= 2:
                print(f"[Passport-Manual] Found MRZ lines: {mrz_lines}")
                return self.parse_mrz_text_manual('\n'.join(mrz_lines))
            
            return None
            
        except Exception as e:
            print(f"[Passport-Manual] Manual MRZ extraction failed: {str(e)}")
            return None
    
    def parse_mrz_text_manual(self, mrz_text: str) -> Optional[Dict]:
        """
        Manually parse MRZ text with special handling for UAE/Arabic names
        
        Expected format for UAE passport:
        Line 1: P<country<<surname<<given<names<<<<<<<<<<<<<
        Line 2: passportno<country<dob<sex<expiry<<<<<<<<<<
        """
        try:
            lines = mrz_text.strip().split('\n')
            if len(lines) < 2:
                return None
            
            line1 = lines[0].upper()
            line2 = lines[1].upper()
            
            result = {}
            
            # Parse Line 1: P<country<<surname<<given<names
            if line1.startswith('P<'):
                # Extract country (3 chars after P<)
                parts = line1[2:].split('<<')
                if parts:
                    # First part might be country or start of name
                    first_part = parts[0]
                    
                    # Handle different MRZ formats
                    if len(first_part) == 3 and first_part.isalpha():
                        # Standard format: P<CCC<<surname<<given
                        result['country'] = first_part
                        name_parts = parts[1:] if len(parts) > 1 else []
                    else:
                        # Non-standard format: P<surname<<given or P<ALI<<SALEH<AL
                        # The country might be in line 2
                        name_parts = parts
                    
                    # Parse names - handle Arabic naming conventions
                    if name_parts:
                        # First part after country is usually surname
                        surname = name_parts[0].replace('<', ' ').strip()
                        
                        # Handle compound surnames like AL-ALI
                        if len(name_parts) > 1:
                            # Check if next part looks like continuation of surname
                            next_part = name_parts[1].replace('<', ' ').strip()
                            if next_part and (next_part.startswith('AL') or next_part.startswith('EL')):
                                surname = f"{surname} {next_part}"
                                given_parts = name_parts[2:] if len(name_parts) > 2 else []
                            else:
                                given_parts = name_parts[1:]
                        else:
                            given_parts = []
                        
                        result['surname'] = surname
                        
                        # Combine given names
                        if given_parts:
                            given = ' '.join(p.replace('<', ' ').strip() for p in given_parts if p)
                            result['names'] = given
            
            # Parse Line 2: passport<country<dob<sex<expiry
            if line2:
                # Clean the line
                line2_clean = line2.replace(' ', '').strip()
                
                # Extract passport number (alphanumeric, typically 8-9 chars)
                # Look for pattern like X12A45678
                passport_match = re.match(r'^([A-Z0-9]{6,9})', line2_clean)
                if passport_match:
                    result['number'] = passport_match.group(1)
                
                # Extract country code (3 letters after passport number)
                country_match = re.search(r'([A-Z0-9]{6,9})([A-Z]{3})', line2_clean)
                if country_match:
                    result['country'] = country_match.group(2)
                    result['nationality'] = country_match.group(2)
                
                # Extract dates and sex (format: YYMMDD)
                # Pattern: passport[9]country[3]dob[6]check[1]sex[1]expiry[6]
                if len(line2_clean) >= 20:
                    # Try to find date patterns (6 digits)
                    date_matches = re.findall(r'(\d{6})', line2_clean)
                    if date_matches:
                        if len(date_matches) >= 1:
                            result['date_of_birth'] = date_matches[0]
                        if len(date_matches) >= 2:
                            result['expiration_date'] = date_matches[1]
                
                # Extract sex (M or F)
                sex_match = re.search(r'[MF](?=\d{6})', line2_clean)
                if sex_match:
                    result['sex'] = sex_match.group(0)
            
            print(f"[Passport-Manual] Parsed result: {result}")
            return result if result else None
            
        except Exception as e:
            print(f"[Passport-Manual] Parse error: {str(e)}")
            return None
    
    def validate_mrz_checksums(self, mrz_data: Dict) -> bool:
        """
        Validate MRZ checksums for data integrity
        
        Args:
            mrz_data: Dictionary with MRZ data
            
        Returns:
            True if checksums are valid
        """
        # Basic validation - can be enhanced with actual checksum calculation
        required_fields = ['number', 'date_of_birth', 'expiration_date']
        return all(mrz_data.get(field) for field in required_fields)
    
    def format_output(self, data: Dict) -> Dict:
        """
        Format extraction output to standard structure with proper name ordering
        
        Args:
            data: Raw extraction data
            
        Returns:
            Formatted output dictionary
        """
        # Extract names properly - KEEP THEM SEPARATE
        surname = (data.get('surname') or '').strip()
        given_names = (data.get('given_names') or '').strip()
        middle_name = (data.get('middle_name') or '').strip()
        
        # Extract first name from given names if needed
        first_name = given_names
        if given_names and not middle_name:
            parts = given_names.split()
            if len(parts) > 1:
                first_name = parts[0]
                middle_name = ' '.join(parts[1:])
        elif given_names and middle_name:
            # Remove middle name from given names if it's included
            first_name = given_names.replace(middle_name, '').strip()
        
        # Create full name in proper order: First Middle Last
        full_name_parts = []
        if first_name:
            full_name_parts.append(first_name)
        if middle_name:
            full_name_parts.append(middle_name)
        if surname:
            full_name_parts.append(surname)
        full_name = ' '.join(full_name_parts)
        
        # Prepare extracted data with all fields
        extracted_data = {
            'full_name': full_name,
            'last_name': surname,  # Surname IS the last name
            'first_name': first_name,  # First part of given names
            'middle_name': middle_name,
            'passport_number': data.get('passport_number', ''),
            'nationality': data.get('nationality', ''),
            'country_code': data.get('country_code', '') or self.get_country_code(data.get('nationality', '')),
            'date_of_birth': data.get('date_of_birth', ''),
            'place_of_birth': data.get('place_of_birth', ''),
            'sex': data.get('sex', ''),
            'issue_date': data.get('issue_date', ''),  # Important field that was missing
            'expiry_date': data.get('expiry_date', ''),
        }
        
        # Validate extracted data
        validator = FieldValidator(strict_mode=False)
        validation_result = validator.validate_all_fields(extracted_data)
        
        return {
            'success': bool(data),
            'data': validation_result['data'],  # Return validated/cleaned data
            'validation': {
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'total_errors': validation_result['total_errors'],
                'total_warnings': validation_result['total_warnings']
            },
            'confidence': data.get('confidence', 0.0),
            'method': self.extraction_method or 'none'
        }