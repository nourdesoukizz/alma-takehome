#!/usr/bin/env python3
"""
Inspect the form to find all input field IDs
"""

import asyncio
from playwright.async_api import async_playwright

async def inspect_form():
    """Inspect the form and print all input field IDs"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("Navigating to form...")
            await page.goto("https://mendrika-alma.github.io/form-submission/", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            print("\n" + "="*60)
            print("FORM FIELD INSPECTION")
            print("="*60)
            
            # Find all input fields
            inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"], input[type="date"], input:not([type])')
            
            print(f"\nFound {len(inputs)} input fields:")
            print("-" * 40)
            
            for i, input_elem in enumerate(inputs, 1):
                field_id = await input_elem.get_attribute('id')
                field_name = await input_elem.get_attribute('name')
                field_placeholder = await input_elem.get_attribute('placeholder')
                field_type = await input_elem.get_attribute('type') or 'text'
                
                # Try to get label text
                label_text = ""
                try:
                    # Check for label with for attribute
                    if field_id:
                        label = await page.query_selector(f'label[for="{field_id}"]')
                        if label:
                            label_text = await label.inner_text()
                except:
                    pass
                
                # Get parent section to understand context
                parent_section = await page.evaluate('''(element) => {
                    let parent = element.closest('.form-section, .section, fieldset, div');
                    if (parent) {
                        let title = parent.querySelector('h2, h3, legend');
                        return title ? title.textContent : '';
                    }
                    return '';
                }''', input_elem)
                
                print(f"\nField #{i}:")
                print(f"  ID: {field_id or 'None'}")
                print(f"  Name: {field_name or 'None'}")
                print(f"  Type: {field_type}")
                print(f"  Placeholder: {field_placeholder or 'None'}")
                print(f"  Label: {label_text or 'None'}")
                print(f"  Section: {parent_section or 'Unknown'}")
            
            # Also look for select fields
            print("\n" + "="*60)
            print("SELECT FIELDS")
            print("="*60)
            
            selects = await page.query_selector_all('select')
            print(f"\nFound {len(selects)} select fields:")
            
            for i, select_elem in enumerate(selects, 1):
                field_id = await select_elem.get_attribute('id')
                field_name = await select_elem.get_attribute('name')
                
                print(f"\nSelect #{i}:")
                print(f"  ID: {field_id or 'None'}")
                print(f"  Name: {field_name or 'None'}")
            
            # Look specifically for Part 3 (Beneficiary) fields
            print("\n" + "="*60)
            print("PART 3 - BENEFICIARY SECTION ANALYSIS")
            print("="*60)
            
            # Try to find Part 3 section
            part3_sections = await page.query_selector_all('*:has-text("Part 3"), *:has-text("Beneficiary"), *:has-text("Passport Information")')
            
            for section in part3_sections:
                text = await section.inner_text()
                if "Part 3" in text or "Beneficiary" in text:
                    print(f"\nFound section: {text[:100]}...")
                    
                    # Find inputs within this section
                    section_inputs = await section.query_selector_all('input')
                    print(f"  Contains {len(section_inputs)} input fields")
                    
                    for inp in section_inputs[:5]:  # Show first 5
                        inp_id = await inp.get_attribute('id')
                        inp_name = await inp.get_attribute('name')
                        print(f"    - ID: {inp_id}, Name: {inp_name}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_form())