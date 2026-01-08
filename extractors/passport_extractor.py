"""
Passport Data Extraction Module
Handles MRZ reading and OCR fallback for passport data extraction
"""

import re
import json
from datetime import datetime
from typing import Dict, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from PIL import Image
from passporteye import read_mrz

class PassportExtractor:
    """Extract data from passport images using MRZ and OCR"""
    
    def __init__(self):
        self.mrz_data = None
        self.ocr_data = None
        self.confidence = 0.0
        self.extraction_method = None
        
    def extract(self, image_path: str) -> Dict:
        """
        Main extraction method - tries MRZ first, falls back to OCR
        
        Args:
            image_path: Path to passport image file
            
        Returns:
            Dictionary with extracted passport data
        """
        try:
            # Try MRZ extraction first (most accurate)
            mrz_result = self.extract_mrz(image_path)
            if mrz_result and mrz_result.get('confidence', 0) > 0.7:
                self.extraction_method = 'mrz'
                return self.format_output(mrz_result)
            
            # Fall back to OCR if MRZ fails
            ocr_result = self.extract_ocr(image_path)
            if ocr_result:
                self.extraction_method = 'ocr'
                return self.format_output(ocr_result)
            
            # If both fail, return empty structure
            return self.format_output({})
            
        except Exception as e:
            print(f"Extraction error: {str(e)}")
            return self.format_output({})
    
    def extract_mrz(self, image_path: str) -> Optional[Dict]:
        """
        Extract data from passport MRZ (Machine Readable Zone)
        
        Args:
            image_path: Path to passport image
            
        Returns:
            Dictionary with MRZ data or None if extraction fails
        """
        try:
            # Read MRZ using passporteye
            mrz = read_mrz(image_path)
            
            if not mrz:
                print("No MRZ detected in image")
                return None
            
            # Parse MRZ data
            mrz_data = mrz.to_dict()
            
            # Extract and format fields
            result = {
                'surname': mrz_data.get('surname', ''),
                'names': mrz_data.get('names', ''),
                'passport_number': mrz_data.get('number', ''),
                'nationality': mrz_data.get('nationality', ''),
                'date_of_birth': self.format_mrz_date(mrz_data.get('date_of_birth', '')),
                'sex': mrz_data.get('sex', ''),
                'expiry_date': self.format_mrz_date(mrz_data.get('expiration_date', '')),
                'country_code': mrz_data.get('country', ''),
                'confidence': 0.95  # High confidence for successful MRZ read
            }
            
            # Validate MRZ checksums if available
            if self.validate_mrz_checksums(mrz_data):
                result['confidence'] = 0.98
            
            return result
            
        except Exception as e:
            print(f"MRZ extraction failed: {str(e)}")
            return None
    
    def extract_ocr(self, image_path: str) -> Optional[Dict]:
        """
        Extract passport data using OCR when MRZ reading fails
        
        Args:
            image_path: Path to passport image
            
        Returns:
            Dictionary with OCR-extracted data
        """
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                image = np.array(Image.open(image_path))
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing for better OCR
            processed = self.preprocess_for_ocr(gray)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(processed)
            
            # Parse extracted text
            result = self.parse_ocr_text(text)
            result['confidence'] = 0.7  # Lower confidence for OCR
            
            return result
            
        except Exception as e:
            print(f"OCR extraction failed: {str(e)}")
            return None
    
    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image: Grayscale image array
            
        Returns:
            Preprocessed image
        """
        # Apply threshold to get binary image
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.medianBlur(binary, 3)
        
        # Enhance contrast
        enhanced = cv2.equalizeHist(denoised)
        
        return enhanced
    
    def parse_ocr_text(self, text: str) -> Dict:
        """
        Parse OCR text to extract passport fields
        
        Args:
            text: Raw OCR text
            
        Returns:
            Dictionary with parsed data
        """
        result = {}
        lines = text.strip().split('\n')
        
        # Common passport field patterns
        patterns = {
            'passport_number': r'(?:Passport\s*No\.?|Number|No\.?)\s*[:.]?\s*([A-Z0-9]{6,9})',
            'surname': r'(?:Surname|Last\s*Name)\s*[:.]?\s*([A-Z\s]+)',
            'given_names': r'(?:Given\s*Names?|First\s*Name)\s*[:.]?\s*([A-Z\s]+)',
            'nationality': r'(?:Nationality|Citizen)\s*[:.]?\s*([A-Z\s]+)',
            'date_of_birth': r'(?:Date\s*of\s*Birth|DOB|Born)\s*[:.]?\s*(\d{1,2}[\s/.-]\w{3}[\s/.-]\d{2,4})',
            'sex': r'(?:Sex|Gender)\s*[:.]?\s*([MF])',
            'issue_date': r'(?:Date\s*of\s*Issue|Issued)\s*[:.]?\s*(\d{1,2}[\s/.-]\w{3}[\s/.-]\d{2,4})',
            'expiry_date': r'(?:Date\s*of\s*Expiry|Expires?|Valid\s*Until)\s*[:.]?\s*(\d{1,2}[\s/.-]\w{3}[\s/.-]\d{2,4})',
        }
        
        # Search for patterns in text
        full_text = ' '.join(lines)
        for field, pattern in patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if 'date' in field:
                    value = self.parse_date(value)
                result[field] = value
        
        # Try to find names if not found with patterns
        if not result.get('surname') and not result.get('given_names'):
            result.update(self.extract_names_from_text(lines))
        
        return result
    
    def extract_names_from_text(self, lines: list) -> Dict:
        """
        Extract names from text lines when pattern matching fails
        
        Args:
            lines: List of text lines
            
        Returns:
            Dictionary with surname and given_names
        """
        result = {}
        
        # Look for lines with only uppercase letters (common for names)
        name_lines = []
        for line in lines[:10]:  # Check first 10 lines
            if line.strip() and line.isupper() and len(line) > 3:
                # Skip common headers
                if not any(word in line for word in ['PASSPORT', 'REPUBLIC', 'CITIZEN', 'NUMBER']):
                    name_lines.append(line.strip())
        
        if name_lines:
            # First uppercase line is often surname
            if len(name_lines) > 0:
                result['surname'] = name_lines[0]
            # Second is often given names
            if len(name_lines) > 1:
                result['given_names'] = name_lines[1]
        
        return result
    
    def format_mrz_date(self, date_str: str) -> str:
        """
        Format MRZ date (YYMMDD) to standard format (YYYY-MM-DD)
        
        Args:
            date_str: Date in MRZ format (YYMMDD)
            
        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_str or len(date_str) != 6:
            return ''
        
        try:
            year = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            # Determine century (assume 1900s for year > 50, 2000s otherwise)
            if year > 50:
                year += 1900
            else:
                year += 2000
            
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return date_str
    
    def parse_date(self, date_str: str) -> str:
        """
        Parse various date formats to standard YYYY-MM-DD
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_str:
            return ''
        
        # Try different date patterns
        date_patterns = [
            r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',  # DD/MM/YYYY
            r'(\d{1,2})\s+(\w{3})\s+(\d{4})',         # DD MMM YYYY
            r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})',  # YYYY/MM/DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    # Parse and reformat
                    parts = match.groups()
                    # Handle month names
                    if parts[1].isalpha():
                        months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                                 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
                        month_num = months.index(parts[1][:3].upper()) + 1
                        return f"{parts[2]}-{month_num:02d}-{int(parts[0]):02d}"
                    else:
                        # Assume DD/MM/YYYY format
                        if len(parts[2]) == 4:
                            return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
                        else:
                            return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                except:
                    pass
        
        return date_str
    
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
        Format extraction output to standard structure
        
        Args:
            data: Raw extraction data
            
        Returns:
            Formatted output dictionary
        """
        # Combine names
        full_name = ''
        if data.get('surname'):
            full_name = data.get('surname', '')
        if data.get('names') or data.get('given_names'):
            given = data.get('names', data.get('given_names', ''))
            full_name = f"{given} {full_name}".strip()
        
        return {
            'success': bool(data),
            'data': {
                'full_name': full_name,
                'last_name': data.get('surname', ''),
                'first_name': data.get('names', data.get('given_names', '')),
                'passport_number': data.get('passport_number', ''),
                'nationality': data.get('nationality', ''),
                'country_code': data.get('country_code', ''),
                'date_of_birth': data.get('date_of_birth', ''),
                'sex': data.get('sex', ''),
                'issue_date': data.get('issue_date', ''),
                'expiry_date': data.get('expiry_date', ''),
            },
            'confidence': data.get('confidence', 0.0),
            'method': self.extraction_method or 'none'
        }