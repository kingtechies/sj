"""
DIRECT BETTING BOT - PLACES ACTUAL BETS
Uses exact working login code from manager.py
WILL PLACE BETS IMMEDIATELY
"""

import asyncio
import os
import re
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

class DirectBettingBot:
    def __init__(self):
        # EXACT credentials from .env like manager.py
        self.username = os.getenv("BET9JA_USERNAME")
        self.password = os.getenv("BET9JA_PASSWORD")
        self.login_url = os.getenv("LOGIN_URL", "https://shop.bet9ja.com/Sport/Default.aspx?LogoutParams=75%7c4076768")
        self.league_url = os.getenv("LEAGUE_URL", "https://leagueplus.bet9ja.com/")
        self.default_stake = float(os.getenv("DEFAULT_STAKE", "250"))
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.bets_placed = 0
        self.target_bets = 2
        
        print("🎯 DIRECT BETTING BOT - WILL PLACE BETS")
        print(f"Username: {self.username}")
        print(f"Target Bets: {self.target_bets}")
        print(f"Stake: ₦{self.default_stake}")
        print("="*50)
    
    async def log_message(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
    
    async def initialize_browser(self):
        """Initialize browser - EXACT same as manager.py"""
        try:
            await self.log_message("🚀 Initializing browser...")
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # VISIBLE for betting
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            
            await self.log_message("✅ Browser initialized successfully")
            return True
            
        except Exception as e:
            await self.log_message(f"❌ Browser initialization error: {e}", "ERROR")
            return False
    
    async def login_to_bet9ja(self):
        """EXACT SAME login code from manager.py"""
        try:
            await self.log_message("🔐 Starting login process...")
            
            # Navigate to login page
            await self.page.goto(self.login_url, timeout=60000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            # Wait for login form - EXACT SELECTORS from manager.py
            await self.page.wait_for_selector("#h_w_PC_cLogin_ctrlLogin_Username", timeout=10000)
            
            # Fill credentials - EXACT SAME as manager.py
            await self.page.fill("#h_w_PC_cLogin_ctrlLogin_Username", self.username)
            await self.page.fill("#h_w_PC_cLogin_ctrlLogin_Password", self.password)
            
            # Submit form - EXACT SAME as manager.py
            await self.page.press("#h_w_PC_cLogin_ctrlLogin_Password", "Enter")
            await self.page.wait_for_timeout(3000)
            
            # Check if login successful - EXACT SAME logic as manager.py
            try:
                username_field = await self.page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
                if username_field and await username_field.is_visible():
                    await self.log_message("❌ Login failed - form still visible", "ERROR")
                    return False
                else:
                    await self.log_message("✅ Login successful")
                    return True
            except:
                await self.log_message("✅ Login successful (assumed)")
                return True
                
        except Exception as e:
            await self.log_message(f"❌ Login error: {e}", "ERROR")
            return False
    
    async def navigate_to_league_plus(self):
        """Navigate to League Plus for betting"""
        try:
            await self.log_message("🏟️ Navigating to League Plus...")
            await self.page.goto(self.league_url, timeout=60000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            await self.log_message("✅ Reached League Plus")
            return True
        except Exception as e:
            await self.log_message(f"❌ League Plus navigation error: {e}", "ERROR")
            return False
    
    async def find_and_place_bet(self):
        """AGGRESSIVELY find and place a bet"""
        try:
            await self.log_message("🎯 SEARCHING FOR BETS TO PLACE...")
            
            # Wait for page to load
            await self.page.wait_for_timeout(5000)
            
            # Strategy 1: Look for any clickable odds
            await self.log_message("🔍 Looking for clickable odds...")
            
            # Common bet selectors
            bet_selectors = [
                "[class*='odd']", "[class*='Odd']",
                "[class*='bet']", "[class*='Bet']", 
                "[data-odd]", "[data-odds]",
                "button[class*='odd']", "button[class*='bet']",
                "a[class*='odd']", "a[class*='bet']",
                ".odds", ".odd", ".bet-button",
                "[onclick*='bet']", "[onclick*='odd']"
            ]
            
            for selector in bet_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    await self.log_message(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements[:10]:  # Check first 10
                        try:
                            if await element.is_visible():
                                text = await element.inner_text()
                                # Look for odds pattern
                                if re.search(r'\d+\.\d+', text) or any(word in text.lower() for word in ['win', '1', '2', 'x', 'over', 'under']):
                                    await self.log_message(f"🎯 FOUND POTENTIAL BET: {text}")
                                    
                                    # CLICK THE BET
                                    await element.click()
                                    await self.page.wait_for_timeout(2000)
                                    
                                    # Try to place the bet
                                    if await self.try_place_bet():
                                        return True
                                    
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
            
            # Strategy 2: Click anything that looks like a bet
            await self.log_message("🔍 Looking for any clickable elements...")
            
            all_clickable = await self.page.query_selector_all("button, a, [onclick], [class*='click']")
            await self.log_message(f"Found {len(all_clickable)} clickable elements")
            
            for element in all_clickable[:20]:  # Try first 20
                try:
                    if await element.is_visible():
                        text = await element.inner_text()
                        if any(word in text.lower() for word in ['1.', '2.', 'win', 'bet', 'odds']):
                            await self.log_message(f"🎯 TRYING TO CLICK: {text}")
                            await element.click()
                            await self.page.wait_for_timeout(1000)
                            
                            if await self.try_place_bet():
                                return True
                                
                except:
                    continue
            
            await self.log_message("❌ NO BETS FOUND TO PLACE", "ERROR")
            return False
            
        except Exception as e:
            await self.log_message(f"❌ Bet finding error: {e}", "ERROR")
            return False
    
    async def try_place_bet(self):
        """Try to complete bet placement"""
        try:
            await self.log_message("💰 ATTEMPTING TO PLACE BET...")
            
            # Look for stake input
            stake_selectors = [
                "input[placeholder*='stake']", "input[placeholder*='amount']",
                "input[name*='stake']", "input[name*='amount']",
                "input[id*='stake']", "input[id*='amount']",
                "input[type='number']", "input[type='text']"
            ]
            
            stake_input = None
            for selector in stake_selectors:
                try:
                    stake_input = await self.page.query_selector(selector)
                    if stake_input and await stake_input.is_visible():
                        break
                except:
                    continue
            
            if stake_input:
                await self.log_message("💰 Found stake input, entering amount...")
                await stake_input.clear()
                await stake_input.fill(str(int(self.default_stake)))
                await self.page.wait_for_timeout(1000)
            
            # Look for place bet button
            bet_button_selectors = [
                "button[class*='place']", "button[class*='bet']",
                "input[value*='place']", "input[value*='bet']",
                "[onclick*='place']", "[onclick*='bet']",
                "button:has-text('Place')", "button:has-text('Bet')",
                "input[type='submit']", "button[type='submit']"
            ]
            
            for selector in bet_button_selectors:
                try:
                    button = await self.page.query_selector(selector)
                    if button and await button.is_visible():
                        await self.log_message("🚀 PLACING BET NOW!")
                        await button.click()
                        await self.page.wait_for_timeout(3000)
                        
                        # Check for success
                        page_content = await self.page.content()
                        if any(word in page_content.lower() for word in ['success', 'placed', 'confirmed', 'accepted']):
                            self.bets_placed += 1
                            await self.log_message(f"✅ BET #{self.bets_placed} PLACED SUCCESSFULLY!")
                            return True
                        
                except:
                    continue
            
            await self.log_message("❌ Could not complete bet placement")
            return False
            
        except Exception as e:
            await self.log_message(f"❌ Bet placement error: {e}", "ERROR")
            return False
    
    async def place_multiple_bets(self):
        """Place multiple bets until target reached"""
        while self.bets_placed < self.target_bets:
            await self.log_message(f"🎯 PLACING BET {self.bets_placed + 1}/{self.target_bets}")
            
            if await self.find_and_place_bet():
                await self.log_message(f"✅ SUCCESS! Bet {self.bets_placed} placed")
                if self.bets_placed >= self.target_bets:
                    await self.log_message(f"🎉 TARGET REACHED! {self.bets_placed} BETS PLACED!")
                    return True
            else:
                await self.log_message("❌ Failed to place bet, retrying...")
            
            # Wait before next attempt
            await self.page.wait_for_timeout(5000)
            
            # Try refreshing page
            try:
                await self.page.reload()
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                pass
        
        return self.bets_placed >= self.target_bets
    
    async def run_betting_bot(self):
        """Main betting bot execution"""
        try:
            await self.log_message("🚀 STARTING DIRECT BETTING BOT")
            
            # Initialize browser
            if not await self.initialize_browser():
                return False
            
            # Login using EXACT manager.py code
            if not await self.login_to_bet9ja():
                await self.log_message("❌ LOGIN FAILED", "ERROR")
                return False
            
            # Navigate to League Plus
            if not await self.navigate_to_league_plus():
                await self.log_message("❌ LEAGUE PLUS NAVIGATION FAILED", "ERROR")
                return False
            
            # Place bets
            success = await self.place_multiple_bets()
            
            if success:
                await self.log_message(f"🎉 MISSION ACCOMPLISHED! {self.bets_placed} BETS PLACED!")
            else:
                await self.log_message("❌ FAILED TO REACH TARGET", "ERROR")
            
            # Keep browser open to see results
            await self.log_message("🔍 Keeping browser open for 30 seconds to verify...")
            await self.page.wait_for_timeout(30000)
            
            return success
            
        except Exception as e:
            await self.log_message(f"❌ FATAL ERROR: {e}", "ERROR")
            return False
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

async def main():
    """Main execution"""
    bot = DirectBettingBot()
    
    if not bot.username or not bot.password:
        print("❌ ERROR: Missing credentials in .env file!")
        return
    
    print("🎯 DIRECT BETTING BOT")
    print("WILL PLACE ACTUAL BETS!")
    print("="*30)
    
    await bot.run_betting_bot()

if __name__ == "__main__":
    asyncio.run(main())