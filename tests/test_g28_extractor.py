"""
Unit tests for G-28 form extraction functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.g28_extractor_gemini import G28ExtractorGemini


class TestG28ExtractorGemini(unittest.TestCase):
    """Test G-28 form extraction with Gemini API"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the Gemini API key
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-api-key'}):
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    self.extractor = G28ExtractorGemini()
    
    @patch('extractors.g28_extractor_gemini.G28ExtractorGemini._extract_with_gemini')
    def test_extract_from_pdf_success(self, mock_gemini):
        """Test successful extraction from PDF"""
        # Mock Gemini response
        mock_gemini.return_value = {
            "attorney_name": {
                "first": "JOHN",
                "last": "SMITH",
                "middle": "A"
            },
            "firm_name": "SMITH & ASSOCIATES LAW FIRM",
            "address": {
                "street": "123 Main Street, Suite 100",
                "city": "New York",
                "state": "NY",
                "zip": "10001",
                "country": "USA"
            },
            "contact": {
                "phone": "(212) 555-1234",
                "fax": "(212) 555-5678",
                "email": "john.smith@lawfirm.com",
                "mobile": "(917) 555-9876"
            },
            "eligibility": {
                "type": "attorney",
                "bar_number": "123456",
                "bar_state": "NY",
                "uscis_account": "A123456789"
            }
        }
        
        # Test extraction
        result = self.extractor.extract_from_pdf("test_g28.pdf")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['attorney_name']['first'], 'JOHN')
        self.assertEqual(result['data']['firm_name'], 'SMITH & ASSOCIATES LAW FIRM')
        self.assertEqual(result['data']['address']['city'], 'New York')
        self.assertEqual(result['data']['contact']['phone'], '(212) 555-1234')
    
    def test_parse_attorney_name(self):
        """Test attorney name parsing"""
        # Test standard format
        name = "John A. Smith"
        result = self.extractor._parse_attorney_name(name)
        self.assertEqual(result['first'], 'John')
        self.assertEqual(result['middle'], 'A.')
        self.assertEqual(result['last'], 'Smith')
        
        # Test without middle name
        name = "Jane Doe"
        result = self.extractor._parse_attorney_name(name)
        self.assertEqual(result['first'], 'Jane')
        self.assertEqual(result['middle'], '')
        self.assertEqual(result['last'], 'Doe')
        
        # Test with multiple middle names
        name = "Robert James William Johnson"
        result = self.extractor._parse_attorney_name(name)
        self.assertEqual(result['first'], 'Robert')
        self.assertEqual(result['last'], 'Johnson')
        self.assertIn('James', result['middle'])
    
    def test_parse_address(self):
        """Test address parsing"""
        # Test complete address
        address_text = "123 Main Street, Suite 100, New York, NY 10001"
        result = self.extractor._parse_address(address_text)
        
        self.assertIn('street', result)
        self.assertIn('city', result)
        self.assertIn('state', result)
        self.assertIn('zip', result)
        
        # Test with apartment number
        address_text = "456 Park Ave, Apt 2B, Los Angeles, CA 90001"
        result = self.extractor._parse_address(address_text)
        
        self.assertIn('Apt 2B', result.get('suite', '') or result.get('street', ''))
        self.assertEqual(result['state'], 'CA')
    
    def test_phone_number_formatting(self):
        """Test phone number formatting"""
        # Test various formats
        test_cases = [
            ("2125551234", "(212) 555-1234"),
            ("212-555-1234", "(212) 555-1234"),
            ("(212) 555-1234", "(212) 555-1234"),
            ("+1 212 555 1234", "(212) 555-1234"),
            ("212.555.1234", "(212) 555-1234")
        ]
        
        for input_phone, expected in test_cases:
            result = self.extractor._format_phone(input_phone)
            self.assertEqual(result, expected, f"Failed for input: {input_phone}")
    
    def test_eligibility_type_detection(self):
        """Test detection of eligibility type"""
        # Test attorney
        data = {
            "eligibility": {
                "bar_number": "123456",
                "bar_state": "NY"
            }
        }
        elig_type = self.extractor._determine_eligibility_type(data)
        self.assertEqual(elig_type, "attorney")
        
        # Test accredited representative
        data = {
            "eligibility": {
                "organization": "Legal Aid Society",
                "accreditation_date": "2020-01-01"
            }
        }
        elig_type = self.extractor._determine_eligibility_type(data)
        self.assertEqual(elig_type, "accredited_representative")
    
    @patch('extractors.g28_extractor_gemini.G28ExtractorGemini._extract_with_gemini')
    def test_error_handling(self, mock_gemini):
        """Test error handling in extraction"""
        # Mock Gemini throwing exception
        mock_gemini.side_effect = Exception("API error")
        
        result = self.extractor.extract_from_pdf("test_g28.pdf")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('API error', result['error'])
    
    def test_data_validation(self):
        """Test extracted data validation"""
        # Test with valid data
        valid_data = {
            'attorney_name': {'first': 'John', 'last': 'Smith'},
            'address': {'city': 'New York', 'state': 'NY'},
            'contact': {'phone': '(212) 555-1234'}
        }
        
        self.assertTrue(self.extractor._validate_g28_data(valid_data))
        
        # Test with missing required field
        invalid_data = {
            'attorney_name': {'first': 'John'},  # Missing last name
            'address': {'city': 'New York', 'state': 'NY'}
        }
        
        self.assertFalse(self.extractor._validate_g28_data(invalid_data))
    
    def test_state_abbreviation(self):
        """Test state name to abbreviation conversion"""
        test_cases = [
            ("New York", "NY"),
            ("California", "CA"),
            ("Texas", "TX"),
            ("NY", "NY"),  # Already abbreviated
            ("ca", "CA"),  # Case insensitive
            ("FLORIDA", "FL")
        ]
        
        for input_state, expected in test_cases:
            result = self.extractor._get_state_abbreviation(input_state)
            self.assertEqual(result, expected, f"Failed for input: {input_state}")
    
    def test_email_validation(self):
        """Test email validation"""
        # Valid emails
        valid_emails = [
            "john@example.com",
            "john.doe@lawfirm.com",
            "attorney+test@law-firm.org"
        ]
        
        for email in valid_emails:
            self.assertTrue(self.extractor._validate_email(email))
        
        # Invalid emails
        invalid_emails = [
            "notanemail",
            "@example.com",
            "john@",
            "john doe@example.com"  # Space in email
        ]
        
        for email in invalid_emails:
            self.assertFalse(self.extractor._validate_email(email))
    
    @patch('extractors.g28_extractor_gemini.pdf2image.convert_from_path')
    @patch('extractors.g28_extractor_gemini.G28ExtractorGemini._extract_with_gemini')
    def test_pdf_conversion(self, mock_gemini, mock_convert):
        """Test PDF to image conversion"""
        # Mock PDF conversion
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        
        # Mock Gemini extraction
        mock_gemini.return_value = {
            "attorney_name": {"first": "John", "last": "Smith"}
        }
        
        result = self.extractor.extract_from_pdf("test.pdf")
        
        # Verify PDF conversion was called
        mock_convert.assert_called_once()
        self.assertTrue(result['success'])


if __name__ == '__main__':
    unittest.main()