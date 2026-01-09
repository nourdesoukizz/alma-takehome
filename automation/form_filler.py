"""
Form Filler Module
Automates form filling using Playwright browser automation
"""

import asyncio
import json
from typing import Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
import logging

logger = logging.getLogger(__name__)

class FormFiller:
    """Fill web forms with extracted document data using Playwright"""
    
    def __init__(self, form_url: str = "https://mendrika-alma.github.io/form-submission/"):
        self.form_url = form_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def initialize(self, headless: bool = False):
        """Initialize Playwright browser
        
        Args:
            headless: If False (default for local), shows the browser window
        """
        try:
            logger.info(f"Initializing Playwright browser (headless={headless})...")
            self.playwright = await async_playwright().start()
            
            # Check if running locally
            import os
            is_local = os.environ.get("ENVIRONMENT") == "local"
            
            if is_local and not headless:
                # Local mode - simple browser launch with visible window
                logger.info("Launching visible browser for local development...")
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--start-maximized'],
                    slow_mo=100  # Slow down actions so you can see them
                )
            else:
                # Headless mode (for testing or if explicitly requested)
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
            
            # Create new page
            self.page = await self.browser.new_page()
            
            # Set viewport for consistent rendering
            await self.page.set_viewport_size({"width": 1280, "height": 800})
            
            logger.info(f"Browser initialized successfully (visible={not headless})")
            return True
            
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
    
    async def fill_form(self, data: Dict) -> Dict:
        """
        Fill the form with extracted data
        
        Args:
            data: Combined passport and G-28 extraction data
            
        Returns:
            Dict with success status and filled fields
        """
        filled_fields = []
        errors = []
        
        try:
            # Map extracted data to form fields
            field_mappings = self._create_field_mappings(data)
            
            logger.info(f"Attempting to fill {len(field_mappings)} fields")
            
            for field_id, value in field_mappings.items():
                if value:
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
                                    filled_fields.append({
                                        "field": field_id,
                                        "value": value,
                                        "selector": selector
                                    })
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
            
            # Take screenshot of filled form
            screenshot_path = "filled_form.png"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            return {
                "success": len(filled_fields) > 0,
                "filled_count": len(filled_fields),
                "filled_fields": filled_fields,
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
        Map extracted data to form field IDs
        
        Args:
            data: Extracted document data
            
        Returns:
            Dict mapping field IDs to values
        """
        mappings = {}
        
        # Extract passport data
        passport_data = data.get("passport", {})
        if passport_data:
            # Personal information - Map to actual form field IDs
            mappings["given-name"] = passport_data.get("first_name", "")
            mappings["family-name"] = passport_data.get("last_name", "")
            
            # Try to extract middle name from full name if available
            full_name = passport_data.get("full_name", "")
            if full_name:
                parts = full_name.split()
                if len(parts) == 3:
                    mappings["middle-name"] = parts[1]
                elif len(parts) == 2:
                    mappings["given-name"] = parts[0]
                    mappings["family-name"] = parts[1]
            
            # Document details
            mappings["passport-number"] = passport_data.get("passport_number", "")
            
            # Country from passport
            country = passport_data.get("country_code", "") or passport_data.get("nationality", "")
            if country:
                mappings["country"] = country
            
            # Dates
            mappings["date-of-birth"] = passport_data.get("date_of_birth", "")
            mappings["passport-expiry"] = passport_data.get("expiry_date", "")
            
            # Gender/Sex
            mappings["passport-sex"] = passport_data.get("sex", "")
        
        # Extract G-28 data
        g28_data = data.get("g28", {})
        if g28_data:
            # Attorney information - these might map to petitioner/client fields
            attorney = g28_data.get("attorney_name", {})
            if not mappings.get("given-name") and attorney.get("first"):
                mappings["given-name"] = attorney.get("first", "")
            if not mappings.get("family-name") and attorney.get("last"):
                mappings["family-name"] = attorney.get("last", "")
            if not mappings.get("middle-name") and attorney.get("middle"):
                mappings["middle-name"] = attorney.get("middle", "")
            
            # Address information
            address = g28_data.get("address", {})
            street = address.get("street", "")
            if street:
                # Try to extract street number from full street address
                parts = street.split(None, 1)
                if parts and parts[0].replace('-', '').isdigit():
                    mappings["street-number"] = parts[0]
                    if len(parts) > 1:
                        mappings["street-name"] = parts[1]
                else:
                    mappings["street-number"] = street
            
            # Suite/Apt information
            suite = address.get("suite", "")
            if suite:
                mappings["apt-number"] = suite
            
            mappings["city"] = address.get("city", "")
            mappings["state"] = address.get("state", "")
            mappings["zip"] = address.get("zip", "")
            
            # Contact information - use hyphenated field names
            contact = g28_data.get("contact", {})
            mappings["daytime-phone"] = contact.get("phone", "")
            mappings["mobile-phone"] = contact.get("mobile", "")
            mappings["email"] = contact.get("email", "")
            mappings["fax-number"] = contact.get("fax", "")
            
            # Bar/Eligibility information
            eligibility = g28_data.get("eligibility", {})
            mappings["bar-number"] = eligibility.get("bar_number", "")
            mappings["licensing-authority"] = eligibility.get("bar_state", "")
            
            # USCIS online account
            uscis_account = eligibility.get("uscis_account", "")
            if uscis_account:
                mappings["online-account"] = uscis_account
        
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
                            await select.select_option(value=value)
                            filled_fields.append({
                                "field": select_id,
                                "value": value,
                                "type": "select"
                            })
                            logger.info(f"Selected {value} in field {select_id}")
                        except:
                            # Try selecting by label
                            try:
                                await select.select_option(label=value)
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
                        radio = await self.page.query_selector(selector)
                        if radio:
                            await radio.click()
                            filled_fields.append({
                                "field": "gender_radio",
                                "value": gender,
                                "type": "radio"
                            })
                            logger.info(f"Selected gender radio: {gender}")
                            break
                    except:
                        continue
                        
        except Exception as e:
            errors.append(f"Error filling radio fields: {str(e)}")
    
    async def cleanup(self, keep_open: bool = False):
        """Clean up browser resources
        
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
                    await self.page.close()
                if self.browser:
                    await self.browser.close()
                if hasattr(self, 'playwright'):
                    await self.playwright.stop()
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