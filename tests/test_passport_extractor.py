"""
Unit tests for passport extraction functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.passport_extractor_gemini import PassportExtractorGemini


class TestPassportExtractorGemini(unittest.TestCase):
    """Test passport extraction with Gemini API"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the Gemini API key
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-api-key'}):
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    self.extractor = PassportExtractorGemini()
    
    def test_iso_country_conversion(self):
        """Test ISO country code to full name conversion"""
        # Test valid conversions
        self.assertEqual(self.extractor._convert_country_code('USA'), 'United States of America')
        self.assertEqual(self.extractor._convert_country_code('ARE'), 'United Arab Emirates')
        self.assertEqual(self.extractor._convert_country_code('GBR'), 'United Kingdom')
        self.assertEqual(self.extractor._convert_country_code('FRA'), 'France')
        
        # Test case insensitivity
        self.assertEqual(self.extractor._convert_country_code('usa'), 'United States of America')
        self.assertEqual(self.extractor._convert_country_code('are'), 'United Arab Emirates')
        
        # Test unknown codes (should return as-is)
        self.assertEqual(self.extractor._convert_country_code('XYZ'), 'XYZ')
        self.assertEqual(self.extractor._convert_country_code(''), '')
    
    @patch('extractors.passport_extractor_gemini.PassportExtractorGemini._extract_with_gemini')
    def test_extract_from_image_success(self, mock_gemini):
        """Test successful extraction from image"""
        # Mock Gemini response
        mock_gemini.return_value = {
            "first_name": "JOHN",
            "last_name": "DOE",
            "full_name": "JOHN DOE",
            "date_of_birth": "1990-01-01",
            "passport_number": "123456789",
            "country_code": "USA",
            "nationality": "United States of America",
            "issue_date": "2020-01-01",
            "expiry_date": "2030-01-01",
            "sex": "M",
            "place_of_birth": "New York"
        }
        
        # Test extraction
        result = self.extractor.extract_from_image("test_image.jpg")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['first_name'], 'JOHN')
        self.assertEqual(result['data']['last_name'], 'DOE')
        self.assertEqual(result['data']['passport_number'], '123456789')
        self.assertEqual(result['data']['nationality'], 'United States of America')
        self.assertEqual(result['method'], 'gemini_ocr')
    
    @patch('extractors.passport_extractor_gemini.PassportExtractorGemini._extract_with_gemini')
    @patch('extractors.passport_extractor_gemini.PassportExtractorGemini._extract_mrz')
    def test_mrz_fallback(self, mock_mrz, mock_gemini):
        """Test MRZ fallback when Gemini fails to extract critical fields"""
        # Mock Gemini response missing passport number
        mock_gemini.return_value = {
            "first_name": "JOHN",
            "last_name": "DOE",
            "full_name": "JOHN DOE",
            "date_of_birth": "1990-01-01",
            # Missing passport_number
            "country_code": "USA",
            "nationality": "United States of America"
        }
        
        # Mock MRZ extraction success
        mock_mrz.return_value = {
            'success': True,
            'data': {
                'passport_number': 'P123456789',
                'country_code': 'USA',
                'date_of_birth': '900101',
                'expiry_date': '300101'
            }
        }
        
        result = self.extractor.extract_from_image("test_image.jpg")
        
        # Should use MRZ fallback
        self.assertTrue(result['success'])
        self.assertEqual(result['method'], 'mrz_fallback')
        self.assertEqual(result['data']['passport_number'], 'P123456789')
    
    def test_parse_mrz_date(self):
        """Test MRZ date parsing"""
        # Test valid dates
        self.assertEqual(self.extractor._parse_mrz_date('900101'), '1990-01-01')
        self.assertEqual(self.extractor._parse_mrz_date('200615'), '2020-06-15')
        self.assertEqual(self.extractor._parse_mrz_date('991231'), '1999-12-31')
        
        # Test dates after 2000
        self.assertEqual(self.extractor._parse_mrz_date('010101'), '2001-01-01')
        self.assertEqual(self.extractor._parse_mrz_date('251231'), '2025-12-31')
        
        # Test invalid dates
        self.assertIsNone(self.extractor._parse_mrz_date(''))
        self.assertIsNone(self.extractor._parse_mrz_date('123'))
        self.assertIsNone(self.extractor._parse_mrz_date('invalid'))
    
    def test_parse_arabic_name(self):
        """Test Arabic/UAE name parsing"""
        # Test typical UAE name format
        arabic_name = "محمد أحمد عبدالله الشامسي"
        result = self.extractor._parse_name(arabic_name)
        
        # Should handle Arabic names gracefully
        self.assertIn('first_name', result)
        self.assertIn('last_name', result)
        self.assertIn('full_name', result)
        
        # Test English transliteration
        english_name = "MOHAMMED AHMED ABDULLAH AL SHAMSI"
        result = self.extractor._parse_name(english_name)
        
        self.assertEqual(result['first_name'], 'MOHAMMED')
        self.assertEqual(result['last_name'], 'AL SHAMSI')
        self.assertTrue('AHMED ABDULLAH' in result['full_name'])
    
    @patch('extractors.passport_extractor_gemini.PassportExtractorGemini._extract_with_gemini')
    def test_error_handling(self, mock_gemini):
        """Test error handling in extraction"""
        # Mock Gemini throwing exception
        mock_gemini.side_effect = Exception("API error")
        
        result = self.extractor.extract_from_image("test_image.jpg")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('API error', result['error'])
    
    def test_data_validation(self):
        """Test extracted data validation"""
        # Test with valid data
        valid_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'passport_number': 'P123456',
            'date_of_birth': '1990-01-01'
        }
        
        # Should have required fields
        self.assertTrue(self.extractor._validate_passport_data(valid_data))
        
        # Test with missing required field
        invalid_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            # Missing passport_number
            'date_of_birth': '1990-01-01'
        }
        
        self.assertFalse(self.extractor._validate_passport_data(invalid_data))
    
    def test_date_format_standardization(self):
        """Test date format standardization"""
        # Test various input formats
        test_cases = [
            ('01/01/1990', '1990-01-01'),
            ('1990-01-01', '1990-01-01'),
            ('01-01-1990', '1990-01-01'),
            ('Jan 1, 1990', '1990-01-01'),
            ('1 January 1990', '1990-01-01')
        ]
        
        for input_date, expected in test_cases:
            result = self.extractor._standardize_date(input_date)
            self.assertEqual(result, expected, f"Failed for input: {input_date}")


if __name__ == '__main__':
    unittest.main()