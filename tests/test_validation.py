#!/usr/bin/env python3
"""
Test validation system with intentionally invalid data
"""

from validators import FieldValidator

def test_validation():
    """Test field validation with various invalid inputs"""
    
    print("=" * 60)
    print("Testing Field Validation System")
    print("=" * 60)
    
    # Create validator
    validator = FieldValidator(strict_mode=False)
    
    # Test data with intentional errors
    test_data = {
        # Names with numbers (invalid)
        'first_name': 'John123',
        'last_name': 'Smith456',
        
        # Invalid email
        'email': 'not-an-email',
        
        # Phone too short
        'phone': '123',
        
        # Invalid date format
        'date_of_birth': '32/13/2025',
        
        # Passport with special characters
        'passport_number': 'ABC-123!@#',
        
        # Valid fields
        'city': 'New York',
        'country': 'USA',
        
        # ZIP with letters
        'zip_code': 'ABC123',
        
        # Bar number with spaces
        'bar_number': 'NY 123 456',
    }
    
    print("\nTest Data:")
    for field, value in test_data.items():
        print(f"  {field}: {value}")
    
    # Validate all fields
    result = validator.validate_all_fields(test_data)
    
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    
    print(f"\nSuccess: {result['success']}")
    print(f"Total Errors: {result['total_errors']}")
    print(f"Total Warnings: {result['total_warnings']}")
    
    if result['errors']:
        print("\n❌ ERRORS:")
        for field, error in result['errors'].items():
            original = test_data.get(field)
            cleaned = result['data'].get(field)
            print(f"  • {field}:")
            print(f"    Original: {original}")
            print(f"    Error: {error}")
            print(f"    Cleaned: {cleaned}")
    
    if result['warnings']:
        print("\n⚠️  WARNINGS:")
        for field, warning in result['warnings'].items():
            original = test_data.get(field)
            cleaned = result['data'].get(field)
            print(f"  • {field}:")
            print(f"    Original: {original}")
            print(f"    Warning: {warning}")
            print(f"    Cleaned: {cleaned}")
    
    print("\n✅ CLEANED DATA:")
    for field, value in result['data'].items():
        if value != test_data.get(field):
            print(f"  {field}: {test_data.get(field)} → {value}")
    
    # Test specific validators
    print("\n" + "=" * 60)
    print("TESTING INDIVIDUAL VALIDATORS")
    print("=" * 60)
    
    # Test name validation
    print("\n1. Name Validation:")
    test_names = [
        "John",           # Valid
        "Mary-Jane",      # Valid with hyphen
        "O'Connor",       # Valid with apostrophe
        "John123",        # Invalid - has numbers
        "J@hn",          # Invalid - special chars
        "A",             # Too short
    ]
    
    for name in test_names:
        is_valid, cleaned, message = validator.validate_name(name)
        status = "✓" if is_valid else "✗"
        print(f"  {status} '{name}' → '{cleaned}' {f'({message})' if message else ''}")
    
    # Test email validation
    print("\n2. Email Validation:")
    test_emails = [
        "john@example.com",     # Valid
        "test.user@gmail.com",  # Valid
        "invalid-email",        # Invalid
        "missing@domain",       # Invalid
        "@nodomain.com",        # Invalid
    ]
    
    for email in test_emails:
        is_valid, cleaned, message = validator.validate_email(email)
        status = "✓" if is_valid else "✗"
        print(f"  {status} '{email}' → '{cleaned}' {f'({message})' if message else ''}")
    
    # Test phone validation
    print("\n3. Phone Validation:")
    test_phones = [
        "1234567890",       # Valid 10 digits
        "(123) 456-7890",   # Valid with formatting
        "123",              # Too short
        "abc123",           # Letters
        "12345678901234567", # Too long
    ]
    
    for phone in test_phones:
        is_valid, cleaned, message = validator.validate_phone(phone)
        status = "✓" if is_valid else "✗"
        print(f"  {status} '{phone}' → '{cleaned}' {f'({message})' if message else ''}")
    
    print("\n" + "=" * 60)
    print("Validation testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_validation()