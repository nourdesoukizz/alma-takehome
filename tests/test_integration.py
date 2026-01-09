"""
Integration tests for the document extraction and form filling system
"""

import unittest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.passport_extractor_gemini import PassportExtractorGemini
from extractors.g28_extractor_gemini import G28ExtractorGemini
from automation.form_filler import FormFiller


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""
    
    def setUp(self):
        """Set up test environment"""
        self.sample_passport = "sample_docs/sample_passport.jpg"
        self.sample_g28 = "sample_docs/sample_g28.pdf"
        
    def test_passport_extractor_initializes(self):
        """Test passport extractor initialization"""
        try:
            extractor = PassportExtractorGemini()
            self.assertIsNotNone(extractor)
            self.assertTrue(hasattr(extractor, 'extract_from_image'))
        except Exception as e:
            self.fail(f"Failed to initialize passport extractor: {e}")
    
    def test_g28_extractor_initializes(self):
        """Test G-28 extractor initialization"""
        try:
            extractor = G28ExtractorGemini()
            self.assertIsNotNone(extractor)
            self.assertTrue(hasattr(extractor, 'extract_from_pdf'))
        except Exception as e:
            self.fail(f"Failed to initialize G-28 extractor: {e}")
    
    def test_form_filler_initializes(self):
        """Test form filler initialization"""
        try:
            filler = FormFiller()
            self.assertIsNotNone(filler)
            self.assertTrue(hasattr(filler, 'fill_form'))
            self.assertTrue(hasattr(filler, 'navigate_to_form'))
        except Exception as e:
            self.fail(f"Failed to initialize form filler: {e}")
    
    def test_sample_documents_exist(self):
        """Test that sample documents are present"""
        self.assertTrue(os.path.exists(self.sample_passport), 
                       f"Sample passport not found at {self.sample_passport}")
        self.assertTrue(os.path.exists(self.sample_g28), 
                       f"Sample G-28 not found at {self.sample_g28}")
    
    def test_passport_extraction_structure(self):
        """Test passport extraction returns expected structure"""
        if not os.path.exists(self.sample_passport):
            self.skipTest("Sample passport not available")
        
        try:
            extractor = PassportExtractorGemini()
            result = extractor.extract_from_image(self.sample_passport)
            
            # Check result structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            
            if result.get('success'):
                self.assertIn('data', result)
                data = result['data']
                
                # Check for key passport fields
                expected_fields = ['first_name', 'last_name', 'passport_number']
                for field in expected_fields:
                    self.assertIn(field, data, f"Missing field: {field}")
        except Exception as e:
            # If API key issues, skip the test
            if "API" in str(e) or "key" in str(e):
                self.skipTest(f"API key issue: {e}")
            else:
                self.fail(f"Extraction failed: {e}")
    
    def test_g28_extraction_structure(self):
        """Test G-28 extraction returns expected structure"""
        if not os.path.exists(self.sample_g28):
            self.skipTest("Sample G-28 not available")
        
        try:
            extractor = G28ExtractorGemini()
            result = extractor.extract_from_pdf(self.sample_g28)
            
            # Check result structure
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            
            if result.get('success'):
                self.assertIn('data', result)
                data = result['data']
                
                # Check for key G-28 fields
                expected_sections = ['attorney_name', 'address', 'contact']
                for section in expected_sections:
                    self.assertIn(section, data, f"Missing section: {section}")
        except Exception as e:
            # If API key issues, skip the test
            if "API" in str(e) or "key" in str(e):
                self.skipTest(f"API key issue: {e}")
            else:
                self.fail(f"Extraction failed: {e}")
    
    def test_field_mappings(self):
        """Test form field mappings are created correctly"""
        filler = FormFiller()
        
        # Test data structure
        test_data = {
            "passport": {
                "first_name": "JOHN",
                "last_name": "DOE",
                "passport_number": "123456789",
                "date_of_birth": "1990-01-01",
                "nationality": "United States"
            },
            "g28": {
                "attorney_name": {
                    "first": "JANE",
                    "last": "SMITH",
                    "middle": "A"
                },
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "state": "NY",
                    "zip": "10001"
                },
                "contact": {
                    "phone": "(212) 555-1234",
                    "email": "jane@law.com"
                }
            }
        }
        
        # Create field mappings
        mappings = filler._create_field_mappings(test_data)
        
        # Verify mappings
        self.assertIsInstance(mappings, dict)
        self.assertGreater(len(mappings), 0)
        
        # Check passport fields are mapped
        self.assertIn("passport-surname", mappings)
        self.assertEqual(mappings["passport-surname"], "DOE")
        
        # Check G-28 fields are mapped
        self.assertIn("family-name", mappings)
        self.assertEqual(mappings["family-name"], "SMITH")
    
    def test_performance_improvements(self):
        """Test that performance optimizations are in place"""
        import automation.form_filler as ff
        
        # Read the form_filler.py content
        with open('automation/form_filler.py', 'r') as f:
            content = f.read()
        
        # Check that hardcoded waits have been removed/reduced
        self.assertNotIn('wait_for_timeout(5000)', content, 
                        "Found 5-second hardcoded wait - should use proper wait conditions")
        
        # Check for proper wait strategies
        self.assertIn("state='visible'", content, 
                     "Should use visibility wait conditions")
        self.assertIn('wait_for_selector', content,
                     "Should use element wait conditions")
    
    def test_country_code_conversion(self):
        """Test ISO country code conversion works"""
        extractor = PassportExtractorGemini()
        
        # Test conversion
        self.assertEqual(extractor._convert_country_code('USA'), 'United States of America')
        self.assertEqual(extractor._convert_country_code('ARE'), 'United Arab Emirates')
        
        # Test unknown code returns as-is
        self.assertEqual(extractor._convert_country_code('XYZ'), 'XYZ')


if __name__ == '__main__':
    unittest.main()