"""
Field Validators for Document Form Filler
Validates extracted data to ensure it meets field requirements
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FieldValidator:
    """Validates form field data"""
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator
        
        Args:
            strict_mode: If True, validation errors prevent form filling
                        If False, validation issues are warnings only
        """
        self.strict_mode = strict_mode
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_name(self, value: str, field_name: str = "name") -> Tuple[bool, str, Optional[str]]:
        """
        Validate name fields (first name, last name, etc.)
        
        Args:
            value: The name to validate
            field_name: Name of the field for error messages
            
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return False, value, f"{field_name} is required"
        
        # Remove extra spaces
        cleaned = ' '.join(value.split())
        
        # Check for numbers
        if any(char.isdigit() for char in cleaned):
            error = f"{field_name} should not contain numbers"
            self.validation_errors.append(error)
            # Try to remove numbers
            cleaned_no_numbers = ''.join(char for char in cleaned if not char.isdigit())
            return False, cleaned_no_numbers, error
        
        # Check for valid name characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[A-Za-z\s\-'\.]+$", cleaned):
            error = f"{field_name} contains invalid characters"
            self.validation_errors.append(error)
            # Clean invalid characters
            cleaned_chars = re.sub(r"[^A-Za-z\s\-'\.]", "", cleaned)
            return False, cleaned_chars, error
        
        # Check minimum length
        if len(cleaned) < 2:
            error = f"{field_name} is too short"
            self.validation_errors.append(error)
            return False, cleaned, error
        
        # Check maximum length
        if len(cleaned) > 50:
            warning = f"{field_name} is very long, might be truncated"
            self.validation_warnings.append(warning)
            return True, cleaned[:50], warning
        
        return True, cleaned, None
    
    def validate_email(self, value: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate email address
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return True, value, None  # Email might be optional
        
        # Basic email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        cleaned = value.strip().lower()
        
        if not re.match(email_pattern, cleaned):
            error = f"Invalid email format: {value}"
            self.validation_errors.append(error)
            return False, cleaned, error
        
        return True, cleaned, None
    
    def validate_phone(self, value: str, field_name: str = "phone") -> Tuple[bool, str, Optional[str]]:
        """
        Validate phone number
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return True, value, None  # Phone might be optional
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', value)
        
        # Check if it's empty after removing non-digits
        if not digits_only:
            error = f"{field_name} must contain numbers"
            self.validation_errors.append(error)
            return False, value, error
        
        # Check length (US phone: 10 digits, international can be longer)
        if len(digits_only) < 10:
            error = f"{field_name} is too short (minimum 10 digits)"
            self.validation_errors.append(error)
            return False, digits_only, error
        
        if len(digits_only) > 15:
            error = f"{field_name} is too long (maximum 15 digits)"
            self.validation_errors.append(error)
            return False, digits_only[:15], error
        
        # Format US phone numbers
        if len(digits_only) == 10:
            formatted = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
            return True, formatted, None
        elif len(digits_only) == 11 and digits_only[0] == '1':
            formatted = f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
            return True, formatted, None
        
        return True, digits_only, None
    
    def validate_date(self, value: str, field_name: str = "date") -> Tuple[bool, str, Optional[str]]:
        """
        Validate date format
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return True, value, None  # Date might be optional
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%B %d, %Y',
            '%d %B %Y'
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(value.strip(), fmt)
                # Convert to standard format (YYYY-MM-DD)
                formatted = date_obj.strftime('%Y-%m-%d')
                
                # Check if date is reasonable (not in future for birth dates, etc.)
                if field_name.lower() in ['date_of_birth', 'dob', 'birth_date']:
                    if date_obj > datetime.now():
                        error = f"{field_name} cannot be in the future"
                        self.validation_errors.append(error)
                        return False, formatted, error
                    
                    # Check if person would be over 120 years old
                    if (datetime.now() - date_obj).days > 120 * 365:
                        warning = f"{field_name} indicates age over 120 years"
                        self.validation_warnings.append(warning)
                        return True, formatted, warning
                
                return True, formatted, None
                
            except ValueError:
                continue
        
        error = f"Invalid date format for {field_name}: {value}"
        self.validation_errors.append(error)
        return False, value, error
    
    def validate_passport_number(self, value: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate passport number
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return False, value, "Passport number is required"
        
        # Remove spaces and convert to uppercase
        cleaned = value.strip().upper().replace(' ', '')
        
        # Check if alphanumeric only
        if not cleaned.isalnum():
            error = "Passport number should contain only letters and numbers"
            self.validation_errors.append(error)
            cleaned_alnum = ''.join(c for c in cleaned if c.isalnum())
            return False, cleaned_alnum, error
        
        # Check length (most passports are 6-9 characters)
        if len(cleaned) < 6:
            error = "Passport number is too short"
            self.validation_errors.append(error)
            return False, cleaned, error
        
        if len(cleaned) > 15:
            error = "Passport number is too long"
            self.validation_errors.append(error)
            return False, cleaned[:15], error
        
        return True, cleaned, None
    
    def validate_zip_code(self, value: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate ZIP/postal code
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return True, value, None  # ZIP might be optional
        
        # Remove spaces and hyphens
        cleaned = value.strip().replace(' ', '').replace('-', '')
        
        # US ZIP code (5 or 9 digits)
        if cleaned.isdigit():
            if len(cleaned) == 5:
                return True, cleaned, None
            elif len(cleaned) == 9:
                formatted = f"{cleaned[:5]}-{cleaned[5:]}"
                return True, formatted, None
            else:
                error = f"Invalid ZIP code length: {value}"
                self.validation_errors.append(error)
                return False, cleaned[:5] if len(cleaned) > 5 else cleaned, error
        
        # Canadian postal code (letter-number pattern)
        if len(cleaned) == 6 and re.match(r'^[A-Z]\d[A-Z]\d[A-Z]\d$', cleaned.upper()):
            formatted = f"{cleaned[:3].upper()} {cleaned[3:].upper()}"
            return True, formatted, None
        
        # Other formats - just ensure reasonable length
        if len(cleaned) > 10:
            warning = "ZIP/postal code is very long"
            self.validation_warnings.append(warning)
            return True, cleaned[:10], warning
        
        return True, cleaned, None
    
    def validate_bar_number(self, value: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate attorney bar number
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return True, value, None  # Bar number might be optional
        
        # Remove common separators
        cleaned = value.strip().upper().replace('-', '').replace(' ', '')
        
        # Most bar numbers are alphanumeric
        if not cleaned.isalnum():
            warning = "Bar number contains special characters"
            self.validation_warnings.append(warning)
            cleaned_alnum = ''.join(c for c in cleaned if c.isalnum())
            return True, cleaned_alnum, warning
        
        # Check reasonable length
        if len(cleaned) < 4:
            warning = "Bar number seems short"
            self.validation_warnings.append(warning)
            return True, cleaned, warning
        
        if len(cleaned) > 20:
            warning = "Bar number is very long"
            self.validation_warnings.append(warning)
            return True, cleaned[:20], warning
        
        return True, cleaned, None
    
    def validate_country_code(self, value: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate country code (2 or 3 letter ISO code)
        
        Returns:
            Tuple of (is_valid, cleaned_value, error_message)
        """
        if not value:
            return True, value, None
        
        cleaned = value.strip().upper()
        
        # Check if it's 2 or 3 letter code
        if len(cleaned) in [2, 3] and cleaned.isalpha():
            return True, cleaned, None
        
        # Try to extract country code from longer text
        if len(cleaned) > 3:
            # Look for common country names and convert to codes
            country_map = {
                'UNITED STATES': 'USA',
                'AMERICA': 'USA',
                'US': 'USA',
                'CANADA': 'CAN',
                'MEXICO': 'MEX',
                'INDIA': 'IND',
                'CHINA': 'CHN',
                'UNITED KINGDOM': 'GBR',
                'UK': 'GBR',
                'FRANCE': 'FRA',
                'GERMANY': 'DEU'
            }
            
            for country_name, code in country_map.items():
                if country_name in cleaned:
                    return True, code, None
            
            # If not found, take first 3 letters
            code = ''.join(c for c in cleaned if c.isalpha())[:3]
            warning = f"Country code extracted from: {value}"
            self.validation_warnings.append(warning)
            return True, code, warning
        
        return True, cleaned, None
    
    def validate_all_fields(self, data: Dict) -> Dict:
        """
        Validate all fields in the data dictionary
        
        Args:
            data: Dictionary of field names to values
            
        Returns:
            Dictionary with validation results and cleaned data
        """
        self.validation_errors = []
        self.validation_warnings = []
        validated_data = {}
        field_errors = {}
        field_warnings = {}
        
        for field_name, value in data.items():
            if not value:
                validated_data[field_name] = value
                continue
            
            # Determine field type and validate accordingly
            field_lower = field_name.lower()
            
            # Name fields
            if any(name_key in field_lower for name_key in ['name', 'surname', 'given', 'family']):
                is_valid, cleaned, message = self.validate_name(value, field_name)
                validated_data[field_name] = cleaned
                if message:
                    if not is_valid:
                        field_errors[field_name] = message
                    else:
                        field_warnings[field_name] = message
            
            # Email fields
            elif 'email' in field_lower:
                is_valid, cleaned, message = self.validate_email(value)
                validated_data[field_name] = cleaned
                if message and not is_valid:
                    field_errors[field_name] = message
            
            # Phone fields
            elif any(phone_key in field_lower for phone_key in ['phone', 'mobile', 'tel', 'fax']):
                is_valid, cleaned, message = self.validate_phone(value, field_name)
                validated_data[field_name] = cleaned
                if message and not is_valid:
                    field_errors[field_name] = message
            
            # Date fields
            elif any(date_key in field_lower for date_key in ['date', 'dob', 'birth', 'expiry']):
                is_valid, cleaned, message = self.validate_date(value, field_name)
                validated_data[field_name] = cleaned
                if message:
                    if not is_valid:
                        field_errors[field_name] = message
                    else:
                        field_warnings[field_name] = message
            
            # Passport number
            elif 'passport' in field_lower and 'number' in field_lower:
                is_valid, cleaned, message = self.validate_passport_number(value)
                validated_data[field_name] = cleaned
                if message and not is_valid:
                    field_errors[field_name] = message
            
            # ZIP code
            elif any(zip_key in field_lower for zip_key in ['zip', 'postal']):
                is_valid, cleaned, message = self.validate_zip_code(value)
                validated_data[field_name] = cleaned
                if message and not is_valid:
                    field_errors[field_name] = message
            
            # Bar number
            elif 'bar' in field_lower and 'number' in field_lower:
                is_valid, cleaned, message = self.validate_bar_number(value)
                validated_data[field_name] = cleaned
                if message:
                    field_warnings[field_name] = message
            
            # Country code
            elif 'country' in field_lower or 'nationality' in field_lower:
                is_valid, cleaned, message = self.validate_country_code(value)
                validated_data[field_name] = cleaned
                if message:
                    field_warnings[field_name] = message
            
            # Default - no specific validation
            else:
                validated_data[field_name] = value
        
        return {
            'success': len(field_errors) == 0 or not self.strict_mode,
            'data': validated_data,
            'errors': field_errors,
            'warnings': field_warnings,
            'total_errors': len(field_errors),
            'total_warnings': len(field_warnings)
        }