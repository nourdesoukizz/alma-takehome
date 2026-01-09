"""
Form Filler Module
Automates form filling using Playwright browser automation
"""

import asyncio
import json
from typing import Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
import logging
import sys
import os

# Add parent directory to path to import validators
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validators import FieldValidator

logger = logging.getLogger(__name__)

class FormFiller:
    """Fill web forms with extracted document data using Playwright"""
    
    def __init__(self, form_url: str = "https://mendrika-alma.github.io/form-submission/"):
        self.form_url = form_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def initialize(self, headless: bool = False):
        """Initialize Playwright browser with improved error handling
        
        Args:
            headless: If False (default for local), shows the browser window
        """
        try:
            logger.info(f"Initializing Playwright browser (headless={headless})...")
            
            # Clean up any existing browser instance first
            if hasattr(self, 'browser') and self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
                self.browser = None
            
            self.playwright = await async_playwright().start()
            
            # Check if running locally
            import os
            is_local = os.environ.get("ENVIRONMENT") == "local"
            
            # Try different browser options in order
            browser_options = []
            
            if is_local and not headless:
                # For local visible mode, prefer Firefox which is more stable
                browser_options = [
                    ("firefox", self.playwright.firefox, {
                        "headless": False, 
                        "slow_mo": 100,
                        "args": ['--width=1280', '--height=800']
                    }),
                    ("webkit", self.playwright.webkit, {
                        "headless": False, 
                        "slow_mo": 100
                    }),
                    ("chromium-headless", self.playwright.chromium, {
                        "headless": True, 
                        "args": ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                    }),
                ]
            else:
                # For headless mode
                browser_options = [
                    ("chromium-headless", self.playwright.chromium, {
                        "headless": True, 
                        "args": ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                    }),
                ]
            
            # Try each browser option
            for browser_name, browser_type, launch_args in browser_options:
                try:
                    logger.info(f"Trying {browser_name}...")
                    self.browser = await browser_type.launch(**launch_args)
                    logger.info(f"Successfully launched {browser_name}")
                    
                    # Create browser context and page with error handling
                    try:
                        context = await self.browser.new_context(
                            viewport={"width": 1280, "height": 800},
                            ignore_https_errors=True
                        )
                        self.page = await context.new_page()
                        
                        # Set default timeout
                        self.page.set_default_timeout(30000)
                        
                    except Exception as page_error:
                        logger.error(f"Failed to create page for {browser_name}: {page_error}")
                        await self.browser.close()
                        self.browser = None
                        continue
                    
                    # If we had to fall back to headless mode in local env, warn the user
                    if is_local and browser_name == "chromium-headless":
                        logger.warning("Running in headless mode due to browser compatibility issues. Screenshots will be captured instead.")
                    
                    logger.info(f"Browser initialized successfully (visible={not headless})")
                    return True
                    
                except Exception as e:
                    logger.warning(f"{browser_name} failed: {e}")
                    if self.browser:
                        try:
                            await self.browser.close()
                        except:
                            pass
                        self.browser = None
                    
                    if browser_name == browser_options[-1][0]:
                        # This was the last option
                        raise Exception(f"All browser options failed. Last error: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def navigate_to_form(self) -> bool:
        """Navigate to the form URL"""
        try:
            logger.info(f"Navigating to form: {self.form_url}")
            
            # Navigate with increased timeout for slower connections
            await self.page.goto(self.form_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for form container to be ready (the page uses div.form-container, not form tag)
            await self.page.wait_for_selector('.form-container', timeout=30000)
            
            # Additional wait for any dynamic content
            await self.page.wait_for_timeout(2000)
            
            logger.info("Successfully navigated to form")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to form: {str(e)}")
            
            # Try with alternative wait strategy
            try:
                logger.info("Attempting alternative navigation strategy...")
                await self.page.goto(self.form_url, wait_until="load", timeout=60000)
                await self.page.wait_for_timeout(5000)  # Wait for JS to load
                
                # Check if form container exists
                form_container = await self.page.query_selector('.form-container')
                if form_container:
                    logger.info("Form loaded with alternative strategy")
                    return True
            except Exception as retry_error:
                logger.error(f"Alternative strategy also failed: {str(retry_error)}")
            
            return False
    
    async def fill_form(self, data: Dict, validate: bool = True) -> Dict:
        """
        Fill the form with extracted data
        
        Args:
            data: Combined passport and G-28 extraction data
            validate: Whether to validate fields before filling
            
        Returns:
            Dict with success status, filled fields, and validation results
        """
        filled_fields = []
        errors = []
        validation_errors = {}
        validation_warnings = {}
        skipped_fields = []
        
        try:
            # Map extracted data to form fields
            field_mappings = self._create_field_mappings(data)
            
            # Validate fields if requested
            if validate:
                validator = FieldValidator(strict_mode=False)
                validation_result = validator.validate_all_fields(field_mappings)
                field_mappings = validation_result['data']  # Use cleaned data
                validation_errors = validation_result['errors']
                validation_warnings = validation_result['warnings']
                
                logger.info(f"Validation complete: {validation_result['total_errors']} errors, {validation_result['total_warnings']} warnings")
                
                # Log validation issues
                for field, error in validation_errors.items():
                    logger.error(f"Validation error for {field}: {error}")
                for field, warning in validation_warnings.items():
                    logger.warning(f"Validation warning for {field}: {warning}")
            
            logger.info(f"Attempting to fill {len(field_mappings)} fields")
            
            for field_id, value in field_mappings.items():
                if value:
                    # Skip field if it has a validation error in strict mode
                    if field_id in validation_errors and validate:
                        logger.warning(f"Skipping field {field_id} due to validation error: {validation_errors[field_id]}")
                        skipped_fields.append({
                            "field": field_id,
                            "reason": validation_errors[field_id],
                            "original_value": value
                        })
                        continue
                    
                    try:
                        # Try different selector strategies
                        selectors = [
                            f"#{field_id}",
                            f"[name='{field_id}']",
                            f"[id*='{field_id}']",
                            f"[name*='{field_id}']"
                        ]
                        
                        filled = False
                        for selector in selectors:
                            try:
                                # Check if element exists
                                element = await self.page.query_selector(selector)
                                if element:
                                    # Clear existing value
                                    await self.page.fill(selector, "")
                                    # Fill with new value
                                    await self.page.fill(selector, str(value))
                                    
                                    field_info = {
                                        "field": field_id,
                                        "value": value,
                                        "selector": selector
                                    }
                                    
                                    # Add validation status
                                    if field_id in validation_warnings:
                                        field_info["warning"] = validation_warnings[field_id]
                                    
                                    filled_fields.append(field_info)
                                    filled = True
                                    logger.info(f"Filled field {field_id} with value: {value}")
                                    break
                            except:
                                continue
                        
                        if not filled:
                            logger.warning(f"Could not find field: {field_id}")
                            
                    except Exception as e:
                        error_msg = f"Error filling field {field_id}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
            
            # Handle select/dropdown fields
            await self._fill_select_fields(data, filled_fields, errors)
            
            # Handle radio buttons
            await self._fill_radio_fields(data, filled_fields, errors)
            
            # Take screenshot of filled form with error handling
            try:
                if self.page and not self.page.is_closed():
                    screenshot_path = "filled_form.png"
                    await self.page.screenshot(path=screenshot_path, full_page=True, timeout=10000)
                    logger.info(f"Screenshot saved: {screenshot_path}")
                else:
                    screenshot_path = None
                    logger.warning("Cannot take screenshot - page is closed")
            except Exception as e:
                screenshot_path = None
                logger.warning(f"Could not take screenshot: {e}")
            
            return {
                "success": len(filled_fields) > 0,
                "filled_count": len(filled_fields),
                "filled_fields": filled_fields,
                "skipped_fields": skipped_fields,
                "validation_errors": validation_errors,
                "validation_warnings": validation_warnings,
                "errors": errors,
                "screenshot": screenshot_path
            }
            
        except Exception as e:
            logger.error(f"Form filling failed: {str(e)}")
            return {
                "success": False,
                "filled_count": 0,
                "filled_fields": [],
                "errors": [str(e)],
                "screenshot": None
            }
    
    def _create_field_mappings(self, data: Dict) -> Dict:
        """
        Map extracted data to form field IDs - Comprehensive mapping for all 31 fields
        
        Args:
            data: Extracted document data
            
        Returns:
            Dict mapping field IDs to values
        """
        mappings = {}
        
        # Extract both data sources
        passport_data = data.get("passport", {})
        g28_data = data.get("g28", {})
        
        # ===== PART 1: ATTORNEY/REPRESENTATIVE INFORMATION =====
        # Priority: G-28 data first, then passport as fallback
        
        # 1. Online Account Number (from G-28)
        if g28_data:
            eligibility = g28_data.get("eligibility", {})
            uscis_account = eligibility.get("uscis_account", "")
            if uscis_account:
                mappings["online-account"] = uscis_account
        
        # 2. Attorney/Representative Name (G-28 priority, passport fallback)
        if g28_data:
            attorney = g28_data.get("attorney_name", {})
            if attorney.get("last"):
                mappings["family-name"] = attorney.get("last", "")
            if attorney.get("first"):
                mappings["given-name"] = attorney.get("first", "")
            if attorney.get("middle"):
                mappings["middle-name"] = attorney.get("middle", "")
        
        # Use passport data as fallback for name fields if G-28 is empty
        if not mappings.get("family-name") and passport_data:
            mappings["family-name"] = passport_data.get("last_name", "")
        if not mappings.get("given-name") and passport_data:
            mappings["given-name"] = passport_data.get("first_name", "")
        if not mappings.get("middle-name") and passport_data:
            # Try to extract middle name from full name
            full_name = passport_data.get("full_name", "")
            if full_name:
                parts = full_name.split()
                if len(parts) >= 3:
                    mappings["middle-name"] = " ".join(parts[1:-1])  # Everything between first and last
        
        # 3. Address Information (from G-28)
        if g28_data:
            address = g28_data.get("address", {})
            
            # Street number and name
            street = address.get("street", "")
            if street:
                # Full street address goes in street-number field
                mappings["street-number"] = street
            
            # Apartment/Suite
            suite = address.get("suite", "")
            if suite:
                mappings["apt-number"] = suite
            
            # City, State, ZIP
            if address.get("city"):
                mappings["city"] = address.get("city", "")
            if address.get("state"):
                mappings["state"] = address.get("state", "")
            if address.get("zip"):
                mappings["zip"] = address.get("zip", "")
            
            # Country (from G-28 or passport)
            country = address.get("country", "")
            if country:
                mappings["country"] = country
            elif passport_data:
                # Use passport country as fallback
                mappings["country"] = passport_data.get("nationality", "") or passport_data.get("country_code", "")
        
        # 4. Contact Information (from G-28)
        if g28_data:
            contact = g28_data.get("contact", {})
            
            if contact.get("phone"):
                mappings["daytime-phone"] = contact.get("phone", "")
            if contact.get("mobile"):
                mappings["mobile-phone"] = contact.get("mobile", "")
            if contact.get("email"):
                mappings["email"] = contact.get("email", "")
            if contact.get("fax"):
                mappings["fax-number"] = contact.get("fax", "")
        
        # ===== PART 2: ELIGIBILITY/LICENSING INFORMATION =====
        if g28_data:
            eligibility = g28_data.get("eligibility", {})
            
            # Bar information
            if eligibility.get("bar_number"):
                mappings["bar-number"] = eligibility.get("bar_number", "")
            if eligibility.get("bar_state"):
                mappings["licensing-authority"] = eligibility.get("bar_state", "")
            
            # Law firm name
            firm_name = g28_data.get("firm_name", "")
            if firm_name:
                mappings["law-firm"] = firm_name
            
            # For accredited representatives (if type is accredited_representative)
            if eligibility.get("type") == "accredited_representative":
                if eligibility.get("organization"):
                    mappings["recognized-org"] = eligibility.get("organization", "")
                if eligibility.get("accreditation_date"):
                    mappings["accreditation-date"] = eligibility.get("accreditation_date", "")
        
        # Fields we cannot fill (not in extracted data):
        # - "associated-with-name" - Not available in documents
        # - "student-name" - Law student info not in documents
        
        # ===== PART 3: BENEFICIARY PASSPORT INFORMATION =====
        if passport_data:
            # Names
            if passport_data.get("last_name"):
                mappings["passport-surname"] = passport_data.get("last_name", "")
            if passport_data.get("first_name"):
                mappings["passport-given-names"] = passport_data.get("first_name", "")
            
            # Passport details
            if passport_data.get("passport_number"):
                mappings["passport-number"] = passport_data.get("passport_number", "")
            
            # Country and nationality
            country_code = passport_data.get("country_code", "")
            nationality = passport_data.get("nationality", "")
            
            if country_code or nationality:
                mappings["passport-country"] = country_code or nationality  # Country of Issue
                mappings["passport-nationality"] = nationality or country_code  # Nationality
            
            # Dates
            if passport_data.get("date_of_birth"):
                mappings["passport-dob"] = passport_data.get("date_of_birth", "")
            
            if passport_data.get("issue_date"):
                mappings["passport-issue-date"] = passport_data.get("issue_date", "")
            
            if passport_data.get("expiry_date"):
                mappings["passport-expiry-date"] = passport_data.get("expiry_date", "")
            
            # Place of birth (if available from OCR)
            if passport_data.get("place_of_birth"):
                mappings["passport-pob"] = passport_data.get("place_of_birth", "")
            
            # Gender/Sex
            if passport_data.get("sex"):
                mappings["passport-sex"] = passport_data.get("sex", "")
        
        # ===== PART 4: SIGNATURE FIELDS =====
        # These cannot be auto-filled and require manual entry:
        # - "client-signature-date"
        # - "attorney-signature-date"
        
        # Log what fields we're filling
        logger.info(f"Field mappings created: {len(mappings)} fields will be filled")
        logger.info(f"Fields that will remain empty: associated-with-name, student-name, client-signature-date, attorney-signature-date")
        
        # Remove empty values
        return {k: v for k, v in mappings.items() if v}
    
    async def _fill_select_fields(self, data: Dict, filled_fields: list, errors: list):
        """Fill select/dropdown fields"""
        try:
            # Find all select elements
            selects = await self.page.query_selector_all("select")
            
            for select in selects:
                select_id = await select.get_attribute("id") or await select.get_attribute("name")
                
                if select_id:
                    # Determine value based on field name
                    value = None
                    
                    if "country" in select_id.lower():
                        passport_data = data.get("passport", {})
                        value = passport_data.get("country_code") or passport_data.get("nationality")
                    elif "state" in select_id.lower():
                        g28_data = data.get("g28", {})
                        address = g28_data.get("address", {})
                        value = address.get("state")
                    elif "gender" in select_id.lower() or "sex" in select_id.lower():
                        passport_data = data.get("passport", {})
                        value = passport_data.get("sex")
                    
                    if value:
                        try:
                            await select.select_option(value=value, timeout=5000)
                            filled_fields.append({
                                "field": select_id,
                                "value": value,
                                "type": "select"
                            })
                            logger.info(f"Selected {value} in field {select_id}")
                        except:
                            # Try selecting by label
                            try:
                                await select.select_option(label=value, timeout=5000)
                                filled_fields.append({
                                    "field": select_id,
                                    "value": value,
                                    "type": "select"
                                })
                            except Exception as e:
                                logger.warning(f"Could not select value in {select_id}: {str(e)}")
                                
        except Exception as e:
            errors.append(f"Error filling select fields: {str(e)}")
    
    async def _fill_radio_fields(self, data: Dict, filled_fields: list, errors: list):
        """Fill radio button fields"""
        try:
            # Handle gender radio buttons
            passport_data = data.get("passport", {})
            gender = passport_data.get("sex", "").upper()
            
            if gender in ["M", "F"]:
                # Try to find and click gender radio button
                gender_selectors = [
                    f"input[type='radio'][value='{gender}']",
                    f"input[type='radio'][value='{gender.lower()}']",
                    f"input[type='radio'][value='{'Male' if gender == 'M' else 'Female'}']",
                    f"input[type='radio'][id*='{'male' if gender == 'M' else 'female'}']"
                ]
                
                for selector in gender_selectors:
                    try:
                        # Check if page is still connected
                        if self.page and not self.page.is_closed():
                            radio = await self.page.query_selector(selector)
                            if radio:
                                await radio.click(timeout=5000)
                                filled_fields.append({
                                    "field": "gender_radio",
                                    "value": gender,
                                    "type": "radio"
                                })
                                logger.info(f"Selected gender radio: {gender}")
                                break
                        else:
                            logger.warning("Page closed - skipping gender radio")
                            break
                    except Exception as e:
                        logger.debug(f"Could not select {selector}: {e}")
                        continue
                        
        except Exception as e:
            errors.append(f"Error filling radio fields: {str(e)}")
    
    async def cleanup(self, keep_open: bool = False):
        """Clean up browser resources with improved error handling
        
        Args:
            keep_open: If True, keeps the browser open (useful for local development)
        """
        try:
            import os
            is_local = os.environ.get("ENVIRONMENT") == "local"
            
            if is_local and keep_open:
                logger.info("Keeping browser open for inspection (close manually when done)")
                # Just stop playwright, but keep browser open
                if hasattr(self, 'playwright'):
                    # Don't stop playwright or browser stays open
                    pass
            else:
                if self.page:
                    try:
                        if not self.page.is_closed():
                            await self.page.close()
                    except Exception as e:
                        logger.debug(f"Error closing page: {e}")
                    finally:
                        self.page = None
                        
                if self.browser:
                    try:
                        if self.browser.is_connected():
                            await self.browser.close()
                    except Exception as e:
                        logger.debug(f"Error closing browser: {e}")
                    finally:
                        self.browser = None
                        
                if hasattr(self, 'playwright'):
                    try:
                        await self.playwright.stop()
                    except Exception as e:
                        logger.debug(f"Error stopping playwright: {e}")
                    finally:
                        self.playwright = None
                        
                logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


async def fill_form_with_data(data: Dict, form_url: Optional[str] = None, headless: bool = None) -> Dict:
    """
    Convenience function to fill form with extracted data
    
    Args:
        data: Combined extraction data from passport and G-28
        form_url: Optional custom form URL
        headless: Whether to run browser in headless mode (None = auto-detect based on environment)
        
    Returns:
        Dict with filling results
    """
    import os
    
    # Auto-detect headless mode based on environment
    if headless is None:
        is_local = os.environ.get("ENVIRONMENT") == "local"
        headless = not is_local  # Local = visible, others = headless
    
    filler = FormFiller(form_url) if form_url else FormFiller()
    
    try:
        # Initialize browser
        if not await filler.initialize(headless=headless):
            return {
                "success": False,
                "error": "Failed to initialize browser"
            }
        
        # Navigate to form
        if not await filler.navigate_to_form():
            return {
                "success": False,
                "error": "Failed to navigate to form"
            }
        
        # Fill the form
        result = await filler.fill_form(data)
        
        # Add note about browser visibility
        if not headless:
            result['browser_visible'] = True
            result['note'] = "Form filled in visible browser - you can interact with it"
        
        return result
        
    finally:
        # Keep browser open in local mode
        is_local = os.environ.get("ENVIRONMENT") == "local"
        await filler.cleanup(keep_open=is_local and not headless)