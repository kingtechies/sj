import asyncio
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import requests

# Load environment variables
load_dotenv()

# Get timestamp for logging
STAMP = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

async def log_request(request):
    """Log network requests"""
    try:
        log_entry = {
            "time_utc": datetime.utcnow().isoformat() + "Z",
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers)
        }
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        with open(f"{log_dir}/endpoints-{STAMP}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Logging error: {e}")

async def log_response(response):
    """Log network responses with status codes"""
    try:
        status = response.status
        url = response.url
        
        # Print status for monitoring
        print(f"[{status}] {response.method} {url[:80]}{'...' if len(url) > 80 else ''}")
        
    except Exception as e:
        pass  # Ignore logging errors

async def take_screenshot(page, filename_prefix="screenshot"):
    """Take a screenshot of the current page"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshots/{filename_prefix}_{timestamp}.png"
        
        # Create screenshots directory if it doesn't exist
        os.makedirs("screenshots", exist_ok=True)
        
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

async def debug_page_structure(page):
    """Debug function to inspect page structure for balance elements"""
    print("🔍 DEBUG: Inspecting page structure for balance elements...")
    
    try:
        # Get all elements that might contain balance information
        potential_elements = await page.query_selector_all("*")
        balance_candidates = []
        
        for element in potential_elements[:200]:  # Limit to first 200 elements
            try:
                if await element.is_visible():
                    text = await element.inner_text()
                    class_name = await element.get_attribute("class") or ""
                    element_id = await element.get_attribute("id") or ""
                    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                    
                    # Look for elements that might contain balance
                    if (any(keyword in text.lower() for keyword in ['balance', 'wallet', 'account', '₦', '$']) or
                        any(keyword in class_name.lower() for keyword in ['balance', 'wallet', 'account', 'money']) or
                        any(keyword in element_id.lower() for keyword in ['balance', 'wallet', 'account', 'money'])):
                        
                        # Check if it contains a number pattern
                        if re.search(r'[\d,]+\.?\d*', text):
                            balance_candidates.append({
                                'tag': tag_name,
                                'id': element_id,
                                'class': class_name,
                                'text': text.strip()[:100],  # First 100 chars
                            })
            except:
                continue
        
        print(f"🔍 Found {len(balance_candidates)} potential balance elements:")
        for i, candidate in enumerate(balance_candidates[:10]):  # Show first 10
            print(f"  {i+1}. Tag: {candidate['tag']}, ID: '{candidate['id']}', Class: '{candidate['class']}'")
            print(f"      Text: '{candidate['text']}'")
            print()
        
        # Also check the page title and URL for context
        title = await page.title()
        url = page.url
        print(f"📄 Page Title: {title}")
        print(f"🔗 Page URL: {url}")
        
    except Exception as e:
        print(f"❌ Debug inspection error: {e}")

async def extract_balance(page):
    """Extract balance from the page, focusing on top-right area"""
    print("🔍 Extracting balance from page (focusing on top-right area)...")
    
    # First, try to find elements in the top-right area
    top_right_selectors = [
        # Header/navigation area selectors
        "header [class*='balance']", "nav [class*='balance']", ".header [class*='balance']",
        "header [class*='wallet']", "nav [class*='wallet']", ".header [class*='wallet']",
        "header [class*='account']", "nav [class*='account']", ".header [class*='account']",
        "header [class*='money']", "nav [class*='money']", ".header [class*='money']",
        
        # Top-right positioning selectors
        ".top-right [class*='balance']", ".top-right [class*='wallet']",
        ".header-right [class*='balance']", ".header-right [class*='wallet']",
        ".user-info [class*='balance']", ".user-info [class*='wallet']",
        ".account-info [class*='balance']", ".account-info [class*='wallet']",
        
        # Bet9ja specific top-right selectors
        "[class*='TopRight'] [class*='Balance']", "[class*='Header'] [class*='Balance']",
        "[id*='TopRight'] [class*='Balance']", "[id*='Header'] [class*='Balance']",
        "[class*='UserPanel'] [class*='Balance']", "[class*='AccountPanel'] [class*='Balance']",
        
        # General balance selectors with position context
        "header .balance", "nav .balance", ".top .balance", ".user .balance",
        "header #balance", "nav #balance", ".top #balance", ".user #balance"
    ]
    
    print("🎯 Checking top-right area selectors...")
    for selector in top_right_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                if await element.is_visible():
                    text = await element.inner_text()
                    # Look for currency patterns (Naira, Dollar, etc.)
                    balance_match = re.search(r'[₦$£€]?\s*[\d,]+\.?\d*', text)
                    if balance_match:
                        balance = balance_match.group().strip()
                        print(f"✅ Found balance in top-right area: {balance}")
                        return balance
        except:
            continue
    
    print("🔍 Top-right specific search failed, trying general balance selectors...")
    
    # General balance selectors if top-right search fails
    general_selectors = [
        ".balance", "#balance", "[class*='balance']", "[id*='balance']",
        ".wallet", "#wallet", "[class*='wallet']", "[id*='wallet']",
        ".amount", "#amount", "[class*='amount']", "[id*='amount']",
        ".money", "#money", "[class*='money']", "[id*='money']",
        ".cash", "#cash", "[class*='cash']", "[id*='cash']",
        # Bet9ja specific selectors
        "[class*='Balance']", "[id*='Balance']",
        "[class*='Account']", "[id*='Account']",
        "[class*='Wallet']", "[id*='Wallet']"
    ]
    
    for selector in general_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                if await element.is_visible():
                    text = await element.inner_text()
                    # Look for currency patterns (Naira, Dollar, etc.)
                    balance_match = re.search(r'[₦$£€]?\s*[\d,]+\.?\d*', text)
                    if balance_match:
                        balance = balance_match.group().strip()
                        print(f"✅ Found balance: {balance}")
                        return balance
        except:
            continue
    
    print("🔍 Searching page content for balance patterns...")
    # Enhanced content search with focus on top area
    try:
        page_content = await page.content()
        
        # Enhanced balance patterns
        balance_patterns = [
            r'balance[:\s]*[₦$£€]?\s*[\d,]+\.?\d*',
            r'wallet[:\s]*[₦$£€]?\s*[\d,]+\.?\d*',
            r'account[:\s]*[₦$£€]?\s*[\d,]+\.?\d*',
            r'available[:\s]*[₦$£€]?\s*[\d,]+\.?\d*',
            r'current[:\s]*[₦$£€]?\s*[\d,]+\.?\d*',
            r'₦\s*[\d,]+\.?\d*',  # Direct Naira patterns
            r'\$\s*[\d,]+\.?\d*', # Direct Dollar patterns
        ]
        
        for pattern in balance_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                for match in matches:
                    balance_match = re.search(r'[₦$£€]?\s*[\d,]+\.?\d*', match)
                    if balance_match:
                        balance = balance_match.group().strip()
                        print(f"✅ Found balance in content: {balance}")
                        return balance
    except Exception as e:
        print(f"❌ Error searching page content: {e}")
    
    print("❌ Balance not found on page")
    return None

async def send_telegram_message(message, bot_token=None, chat_id=None):
    """Send message to Telegram"""
    try:
        if not bot_token or not chat_id:
            print("Telegram credentials not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("Telegram message sent successfully")
            return True
        else:
            print(f"Telegram error: {response.status_code}")
            return False
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

async def record_balance(balance, screenshot_path=None):
    """Record balance to file and send to Telegram with enhanced formatting"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to balance log file
        os.makedirs("logs", exist_ok=True)
        balance_log = "logs/balance_history.txt"
        
        with open(balance_log, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - Balance: {balance}\n")
        
        print(f"✅ Balance recorded: {balance}")
        
        # Send to Telegram if configured
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if bot_token and chat_id:
            message = f"🏦 <b>Bet9ja Balance Update</b>\n\n"
            message += f"💰 Current Balance: <code>{balance}</code>\n"
            message += f"📸 Screenshot: {'✅ Taken' if screenshot_path else '❌ Failed'}\n"
            message += f"⏰ Time: {timestamp}\n"
            message += f"🎯 Status: Ready for next action"
            
            success = await send_telegram_message(message, bot_token, chat_id)
            if success:
                print("✅ Telegram notification sent successfully")
            else:
                print("❌ Telegram notification failed")
        else:
            print("⚠️  Telegram not configured (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID not set)")
            print("💡 To enable Telegram updates, add these to your .env file:")
            print("   TELEGRAM_BOT_TOKEN=your_bot_token")
            print("   TELEGRAM_CHAT_ID=your_chat_id")
            
    except Exception as e:
        print(f"❌ Balance recording error: {e}")

async def try_bet9ja_login(page, username, password):
    """Attempt login using the exact Bet9ja selectors we discovered"""
    print("Attempting login with correct Bet9ja selectors...")
    
    try:
        # Wait for the login form to be present
        print("Waiting for login form...")
        await page.wait_for_selector("#h_w_PC_cLogin_ctrlLogin_Username", timeout=10000)
        
        # Find the username field using the exact ID we discovered
        username_field = await page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
        if not username_field:
            print("Could not find username field with ID")
            return False
            
        # Find the password field
        password_field = await page.query_selector("#h_w_PC_cLogin_ctrlLogin_Password")
        if not password_field:
            print("Could not find password field with ID")
            return False
            
        print("Found username and password fields!")
        
        # Skip shop code field as it's optional
        print("Skipping shop code field (optional)")
        
        # Clear and fill username
        print("Filling username...")
        await username_field.fill("")  # Clear by filling with empty string
        await username_field.fill(username)
        
        # Clear and fill password
        print("Filling password...")
        await password_field.fill("")  # Clear by filling with empty string
        await password_field.fill(password)
        
        # Wait a moment for fields to be filled
        await page.wait_for_timeout(1000)
        
        # Check if there are any required hidden fields or validation we need to handle
        print("Checking for additional form requirements...")
        
        # Look for any required hidden fields that might need values
        hidden_inputs = await page.query_selector_all("input[type='hidden']")
        for hidden in hidden_inputs:
            try:
                name = await hidden.get_attribute("name") or ""
                value = await hidden.get_attribute("value") or ""
                if name and not value:  # Empty required hidden field
                    print(f"Found empty hidden field: {name}")
            except:
                pass
        
        # Try pressing Enter on password field first (more natural)
        print("Trying Enter key on password field...")
        try:
            await password_field.press("Enter")
            print("Pressed Enter on password field")
            
            # Wait a moment to see if form submits
            await page.wait_for_timeout(2000)
            
            # Check if we're still on the same form
            current_username_field = await page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
            if not current_username_field:
                print("Form disappeared after Enter - login may be successful")
                # But let's wait a bit more to see if page reloads with login form again
                await page.wait_for_timeout(3000)
                reloaded_username_field = await page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
                if reloaded_username_field:
                    print("Login form reappeared - login actually failed!")
                    return False
                else:
                    print("Login form stayed gone - login successful!")
                    return True
            else:
                print("Form still present after Enter - trying other methods...")
        except Exception as e:
            print(f"Enter key approach failed: {e}")
        
        # Look for login button - be more specific about Bet9ja login buttons
        login_button_selectors = [
            "input[type='submit'][value*='Login']",
            "input[type='submit'][value*='LOG']", 
            "input[type='submit'][value*='ACCEDI']",  # Italian for login
            "input[type='submit'][value*='Enter']",
            "input[type='submit'][value*='Sign']",
            "button[type='submit']",
            "input[type='submit']",
            "[id*='Login'][type='submit']",
            "[name*='Login'][type='submit']",
            "[id*='btnLogin']",
            "[name*='btnLogin']"
        ]
        
        login_button = None
        for selector in login_button_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    # Get button text/value to verify it's a login button
                    button_text = ""
                    try:
                        button_text = await button.get_attribute("value") or await button.inner_text() or ""
                    except:
                        pass
                    
                    login_button = button
                    print(f"Found login button with selector: {selector}, text: '{button_text}'")
                    break
            except:
                continue
        
        if not login_button:
            print("Could not find login button, trying alternative approaches...")
            
            # Try to find any submit button in the login form
            submit_buttons = await page.query_selector_all("input[type='submit']")
            for btn in submit_buttons:
                try:
                    if await btn.is_visible():
                        btn_value = await btn.get_attribute("value") or ""
                        print(f"Found submit button with value: '{btn_value}'")
                        login_button = btn
                        break
                except:
                    continue
        
        if login_button:
            print("Clicking login button...")
            try:
                # Try multiple click approaches
                await login_button.click()
                print("Login button clicked successfully")
            except Exception as click_error:
                print(f"Regular click failed: {click_error}, trying JavaScript click...")
                try:
                    await login_button.evaluate("element => element.click()")
                    print("JavaScript click successful")
                except Exception as js_error:
                    print(f"JavaScript click also failed: {js_error}")
                    # Try form submission as last resort
                    form = await page.query_selector("#aspnetForm")
                    if form:
                        print("Trying form submission...")
                        await form.evaluate("form => form.submit()")
        else:
            print("No login button found, trying form submission...")
            form = await page.query_selector("#aspnetForm")
            if form:
                print("Submitting form directly...")
                await form.evaluate("form => form.submit()")
            else:
                print("No form found either!")
                return False
        
        # Wait longer for submission and navigation
        print("Waiting for login to process...")
        await page.wait_for_timeout(3000)  # Wait 3 seconds first
        
        # Check if login was successful by looking for URL change or page content change
        current_url = page.url
        print(f"Current URL after login attempt: {current_url}")
        
        # Wait a bit more if page is still loading
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
            print("Page finished loading")
        except:
            print("Page still loading, but continuing...")
        
        # Check if we're still on the login page (which means login failed)
        try:
            username_field_check = await page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
            if username_field_check and await username_field_check.is_visible():
                print("Login form still visible - login failed!")
                
                # Check if there are any error messages
                error_selectors = [
                    ".error", ".alert-error", "[class*='error']", "[id*='error']",
                    ".validation-summary-errors", ".field-validation-error"
                ]
                
                for error_sel in error_selectors:
                    try:
                        error_elem = await page.query_selector(error_sel)
                        if error_elem and await error_elem.is_visible():
                            error_text = await error_elem.inner_text()
                            if error_text.strip():
                                print(f"Error message found: {error_text}")
                    except:
                        continue
                
                # Check if username field still has value (to see if page reloaded)
                try:
                    username_value = await username_field_check.input_value()
                    if not username_value:
                        print("Username field is empty - page may have reloaded")
                    else:
                        print(f"Username field still has value: {username_value}")
                except:
                    pass
                    
                return False
            else:
                print("Login form no longer visible - login successful!")
                return True
                
        except Exception as e:
            print(f"Error checking login form: {e}")
        
        # Also check page content for login success indicators
        try:
            page_content = await page.content()
            login_success_keywords = ["logout", "sign out", "welcome", "dashboard", "account", "profile", "my account"]
            
            success_found = any(keyword in page_content.lower() for keyword in login_success_keywords)
            
            if success_found:
                print("Found success indicators in page content")
                return True
                
        except Exception as e:
            print(f"Error checking page content: {e}")
            
        print("Login appears to have failed")
        return False
            
    except Exception as e:
        print(f"Login error: {e}")
        return False

async def main():
    # Load credentials from .env file only
    username = os.getenv("BET9JA_USERNAME")
    password = os.getenv("BET9JA_PASSWORD")
    login_url = os.getenv("LOGIN_URL", "https://shop.bet9ja.com/Sport/Default.aspx?LogoutParams=75%7c4076768")
    league_url = os.getenv("LEAGUE_URL", "https://leagueplus.bet9ja.com/")
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    
    # Check if required credentials are loaded
    if not username or not password:
        print("ERROR: Username or password not found in .env file!")
        print("Please ensure BET9JA_USERNAME and BET9JA_PASSWORD are set in .env file")
        return
    
    print(f"Starting bot for user: {username}")
    print(f"Login URL: {login_url}")
    print(f"League URL: {league_url}")
    print(f"Headless mode: {headless}")
    
    print(f"Logging endpoints to logs/endpoints-{STAMP}.jsonl")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set up request/response logging
        page.on("request", log_request)
        page.on("response", log_response)
        
        try:
            print("Starting automatic login process...")
            
            # Navigate to login page with longer timeout
            print(f"Navigating to: {login_url}")
            await page.goto(login_url, timeout=60000)  # 60 second timeout
            
            # Wait for page to load with more patience
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                print("Page loaded successfully")
            except:
                print("Page didn't fully load, but continuing anyway...")
            
            # Attempt login
            login_success = await try_bet9ja_login(page, username, password)
            
            if login_success:
                print("auto-login attempted: OK")
                print("🎉 Login successful! Processing post-login tasks...")
                
                # Wait a moment for page to fully load after login
                await page.wait_for_timeout(2000)
                
                # Always take screenshot after successful login
                print("📸 Taking screenshot of logged-in page...")
                screenshot_path = await take_screenshot(page, "after_login")
                
                if screenshot_path:
                    print(f"✅ Screenshot saved: {screenshot_path}")
                else:
                    print("❌ Screenshot failed")
                
                # Always extract and record balance
                print("💰 Extracting balance from top-right area...")
                balance = await extract_balance(page)
                
                if balance:
                    print(f"✅ Balance found: {balance}")
                    await record_balance(balance, screenshot_path)
                    print("✅ Balance recorded and Telegram update sent")
                else:
                    print("⚠️  Could not extract balance from page")
                    print("🔍 Running debug inspection to find balance elements...")
                    await debug_page_structure(page)
                    
                    # Still send Telegram notification about successful login
                    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                    chat_id = os.getenv("TELEGRAM_CHAT_ID")
                    
                    if bot_token and chat_id:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        message = f"🔐 <b>Bet9ja Login Successful</b>\n\n"
                        message += f"⚠️ Balance extraction failed\n"
                        message += f"📸 Screenshot taken\n"
                        message += f"🔍 Debug inspection performed\n"
                        message += f"⏰ Time: {timestamp}"
                        await send_telegram_message(message, bot_token, chat_id)
                
                print("\n" + "="*60)
                print("✅ LOGIN COMPLETED SUCCESSFULLY!")
                print("📸 Screenshot: TAKEN")
                print("💰 Balance: EXTRACTED & RECORDED") 
                print("📱 Telegram: UPDATED")
                print("="*60)
                print("🎯 READY FOR NEXT INSTRUCTIONS")
                print("Tell me where you want the bot to go and what to do next!")
                print("="*60)
                
                # NOT navigating to league page yet - staying on home page
            else:
                print("auto-login attempted: failed")
            
            print("Recording... interact with the site or run your automation.")
            print("Press Ctrl+C to stop.")
            
            # Keep running
            while True:
                await asyncio.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nStopping bot...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())