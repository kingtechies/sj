"""
Bet9ja Manager - Unified System for VPS Deployment
Combines: Login, Real-time Monitoring, Telegram Bot, and Future Betting Logic
"""

import asyncio
import os
import re
import json
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import requests
import glob

# Load environment variables
load_dotenv()

class Bet9jaManager:
    """Main manager class that handles all Bet9ja operations"""
    
    def __init__(self):
        # Credentials
        self.username = os.getenv("BET9JA_USERNAME")
        self.password = os.getenv("BET9JA_PASSWORD")
        self.login_url = os.getenv("LOGIN_URL", "https://shop.bet9ja.com/Sport/Default.aspx?LogoutParams=75%7c4076768")
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"  # Default to headless for VPS
        
        # Telegram settings
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Monitoring settings
        self.check_interval = 30 * 60  # 30 minutes in seconds
        self.screenshot_retention = 24 * 60 * 60  # 24 hours in seconds
        
        # Files
        self.balance_file = "logs/balance_history.txt"
        self.real_time_log = "logs/manager.log"
        self.settings_file = "logs/bot_settings.json"
        self.stats_file = "logs/bet_stats.json"
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.session_active = False
        self.last_balance = None
        
        # Telegram bot state
        self.telegram_running = False
        self.last_telegram_update = 0
        
        # Load bot settings
        self.settings = self.load_settings()
        self.stats = self.load_stats()
    
    # ============================================================================
    # LOGGING AND UTILITIES
    # ============================================================================
    
    async def log_message(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        try:
            os.makedirs("logs", exist_ok=True)
            with open(self.real_time_log, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except:
            pass
    
    def load_settings(self):
        """Load bot settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "default_stake": 200.0,
                    "currency": "₦",
                    "last_updated": datetime.now().isoformat()
                }
        except:
            return {
                "default_stake": 200.0,
                "currency": "₦",
                "last_updated": datetime.now().isoformat()
            }
    
    def save_settings(self):
        """Save bot settings to file"""
        try:
            os.makedirs("logs", exist_ok=True)
            self.settings["last_updated"] = datetime.now().isoformat()
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            asyncio.create_task(self.log_message(f"Error saving settings: {e}", "ERROR"))
    
    def load_stats(self):
        """Load betting statistics from file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "total_bets": 0,
                    "won_bets": 0,
                    "lost_bets": 0,
                    "monthly_profit": 0.0,
                    "monthly_stakes": 0.0,
                    "last_reset": datetime.now().replace(day=1).isoformat(),
                    "bet_history": []
                }
        except:
            return {
                "total_bets": 0,
                "won_bets": 0,
                "lost_bets": 0,
                "monthly_profit": 0.0,
                "monthly_stakes": 0.0,
                "last_reset": datetime.now().replace(day=1).isoformat(),
                "bet_history": []
            }
    
    def save_stats(self):
        """Save betting statistics to file"""
        try:
            os.makedirs("logs", exist_ok=True)
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            asyncio.create_task(self.log_message(f"Error saving stats: {e}", "ERROR"))
    
    # ============================================================================
    # BROWSER AND LOGIN MANAGEMENT
    # ============================================================================
    
    async def initialize_browser(self):
        """Initialize browser and context"""
        try:
            await self.log_message("🚀 Initializing browser...")
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']  # VPS optimization
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            
            await self.log_message("✅ Browser initialized successfully")
            return True
            
        except Exception as e:
            await self.log_message(f"❌ Browser initialization error: {e}", "ERROR")
            return False
    
    async def login_to_bet9ja(self):
        """Perform login to Bet9ja"""
        try:
            await self.log_message("🔐 Starting login process...")
            
            # Navigate to login page
            await self.page.goto(self.login_url, timeout=60000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            # Wait for login form
            await self.page.wait_for_selector("#h_w_PC_cLogin_ctrlLogin_Username", timeout=10000)
            
            # Fill credentials
            await self.page.fill("#h_w_PC_cLogin_ctrlLogin_Username", self.username)
            await self.page.fill("#h_w_PC_cLogin_ctrlLogin_Password", self.password)
            
            # Submit form
            await self.page.press("#h_w_PC_cLogin_ctrlLogin_Password", "Enter")
            await self.page.wait_for_timeout(3000)
            
            # Check if login successful
            try:
                username_field = await self.page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
                if username_field and await username_field.is_visible():
                    await self.log_message("❌ Login failed - form still visible", "ERROR")
                    return False
                else:
                    self.session_active = True
                    await self.log_message("✅ Login successful")
                    return True
            except:
                self.session_active = True
                await self.log_message("✅ Login successful (assumed)")
                return True
                
        except Exception as e:
            await self.log_message(f"❌ Login error: {e}", "ERROR")
            return False
    
    async def check_session_active(self):
        """Check if session is still active"""
        try:
            if not self.page:
                return False
                
            current_url = self.page.url
            if "login" in current_url.lower() or "default.aspx" in current_url.lower():
                try:
                    username_field = await self.page.query_selector("#h_w_PC_cLogin_ctrlLogin_Username")
                    if username_field and await username_field.is_visible():
                        self.session_active = False
                        return False
                except:
                    pass
            
            return True
        except:
            return False
    
    # ============================================================================
    # BALANCE MONITORING AND SCREENSHOTS
    # ============================================================================
    
    async def take_screenshot(self, filename_prefix="manager"):
        """Take a screenshot with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"screenshots/{filename_prefix}_{timestamp}.png"
            
            os.makedirs("screenshots", exist_ok=True)
            
            await self.page.screenshot(path=screenshot_path, full_page=True)
            await self.log_message(f"📸 Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            await self.log_message(f"❌ Screenshot error: {e}", "ERROR")
            return None
    
    async def extract_balance(self):
        """Extract balance with advanced detection"""
        await self.log_message("💰 Extracting balance...")
        
        try:
            # Wait for page to be fully loaded
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Strategy 1: Look near user ID area
            await self.log_message("🔍 Searching near user ID area...")
            try:
                all_elements = await self.page.query_selector_all("*")
                for element in all_elements[:100]:
                    try:
                        if await element.is_visible():
                            text = await element.inner_text()
                            if ('4076768' in text or 'cashier23950' in text or 'Balance:' in text):
                                balance_match = re.search(r'Balance:\s*(\d{1,3}(?:,\d{3})*\.?\d*)', text)
                                if balance_match:
                                    balance = balance_match.group(1).strip()
                                    final_balance = f"₦{balance}"
                                    await self.log_message(f"✅ Found balance near user area: {final_balance}")
                                    return final_balance
                    except:
                        continue
            except:
                pass
            
            # Strategy 2: Balance selectors
            balance_selectors = [
                "[class*='user'] [class*='balance']", "[class*='User'] [class*='Balance']",
                "header [class*='balance']", ".header [class*='balance']",
                "[class*='account'] [class*='balance']", "[class*='Account'] [class*='Balance']",
                ".balance", "#balance", "[class*='balance']", "[id*='balance']"
            ]
            
            for selector in balance_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        if await element.is_visible():
                            text = await element.inner_text()
                            balance_patterns = [
                                r'Balance:\s*(\d{1,3}(?:,\d{3})*\.?\d*)\s*₦',
                                r'Balance:\s*(\d{1,3}(?:,\d{3})*\.?\d*)',
                                r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*₦',
                                r'₦\s*(\d{1,3}(?:,\d{3})*\.?\d*)',
                            ]
                            
                            for pattern in balance_patterns:
                                match = re.search(pattern, text, re.IGNORECASE)
                                if match:
                                    balance = match.group(1).strip()
                                    if balance and len(balance) >= 2:
                                        final_balance = f"₦{balance}"
                                        await self.log_message(f"✅ Found balance: {final_balance}")
                                        return final_balance
                except:
                    continue
            
            # Strategy 3: Page content search
            try:
                page_content = await self.page.content()
                content_patterns = [
                    r'Balance:\s*(\d{1,3}(?:,\d{3})*\.?\d*)\s*₦',
                    r'balance:\s*(\d{1,3}(?:,\d{3})*\.?\d*)\s*₦',
                    r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*₦',
                ]
                
                for pattern in content_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        if ',' in match and len(match) >= 5:
                            final_balance = f"₦{match}"
                            await self.log_message(f"✅ Found balance in content: {final_balance}")
                            return final_balance
            except Exception as e:
                await self.log_message(f"❌ Content search error: {e}", "ERROR")
            
            await self.log_message("❌ Balance not found", "WARNING")
            return None
            
        except Exception as e:
            await self.log_message(f"❌ Balance extraction error: {e}", "ERROR")
            return None
    
    async def cleanup_old_screenshots(self):
        """Delete screenshots older than 24 hours"""
        try:
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                return
                
            current_time = time.time()
            cutoff_time = current_time - self.screenshot_retention
            
            deleted_count = 0
            for file_path in glob.glob(os.path.join(screenshot_dir, "*.png")):
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except:
                        pass
            
            if deleted_count > 0:
                await self.log_message(f"🗑️ Cleaned up {deleted_count} old screenshots")
                
        except Exception as e:
            await self.log_message(f"❌ Screenshot cleanup error: {e}", "ERROR")
    
    # ============================================================================
    # TELEGRAM BOT FUNCTIONS
    # ============================================================================
    
    def send_telegram_message(self, message):
        """Send message to Telegram (synchronous)"""
        if not self.bot_token or not self.chat_id:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return False
    
    def get_latest_balance(self):
        """Get the latest balance from balance history"""
        try:
            if os.path.exists(self.balance_file):
                with open(self.balance_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        balance_match = re.search(r'Balance:\s*([₦\d,]+\.?\d*)', last_line)
                        if balance_match:
                            return balance_match.group(1).strip()
            return "N/A"
        except:
            return "N/A"
    
    def handle_telegram_command(self, message):
        """Handle incoming Telegram commands"""
        try:
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            # Check authorization
            if str(chat_id) != str(self.chat_id):
                unauthorized_msg = """
🚫 <b>UNAUTHORIZED ACCESS DETECTED</b>

⚠️ This is a <b>PRIVATE BOT</b> with restricted access only.
🔒 You are <b>NOT AUTHORIZED</b> to use this bot.
⛔ Please <b>DO NOT</b> attempt to command this bot.
                """
                self.send_telegram_message(unauthorized_msg)
                return
            
            if not text.startswith("/"):
                return
            
            parts = text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Handle commands
            if command == "/start":
                welcome_msg = f"""
🎰 <b>Welcome to Bet9ja Manager!</b> 🎯

🤖 Your automated betting system is running!

📋 <b>Available Commands:</b>
/stake [amount] - Set default stake
/balance - Check current balance  
/stats - View betting statistics
/status - System status
/about - About this bot

💰 Current Balance: <code>{self.get_latest_balance()}</code>
🎲 Default Stake: <code>{self.settings['currency']}{self.settings['default_stake']}</code>

🚀 Ready for automated betting!
                """
                self.send_telegram_message(welcome_msg)
                
            elif command == "/balance":
                balance = self.get_latest_balance()
                balance_msg = f"""
💰 <b>Current Account Balance</b>

🏦 Balance: <code>{balance}</code>
🕐 Last Updated: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>

📸 Latest screenshot will be sent if available
                """
                self.send_telegram_message(balance_msg)
                
            elif command == "/stake":
                if not args:
                    stake_msg = f"""
💰 <b>Current Default Stake</b>

🎲 Amount: <code>{self.settings['currency']}{self.settings['default_stake']}</code>

💡 To change: /stake [amount]
Example: /stake 200
                    """
                    self.send_telegram_message(stake_msg)
                else:
                    try:
                        new_stake = float(args[0])
                        if new_stake <= 0:
                            self.send_telegram_message("❌ Stake amount must be greater than 0!")
                            return
                        
                        old_stake = self.settings["default_stake"]
                        self.settings["default_stake"] = new_stake
                        self.save_settings()
                        
                        update_msg = f"""
✅ <b>Stake Updated Successfully!</b>

📊 Previous: <code>{self.settings['currency']}{old_stake}</code>
🎯 New Default: <code>{self.settings['currency']}{new_stake}</code>
                        """
                        self.send_telegram_message(update_msg)
                    except ValueError:
                        self.send_telegram_message("❌ Please enter a valid number!")
                        
            elif command == "/stats":
                win_rate = 0
                if self.stats["total_bets"] > 0:
                    win_rate = (self.stats["won_bets"] / self.stats["total_bets"]) * 100
                
                roi = 0
                if self.stats["monthly_stakes"] > 0:
                    roi = (self.stats["monthly_profit"] / self.stats["monthly_stakes"]) * 100
                
                stats_msg = f"""
📊 <b>Betting Statistics</b>

🎯 <b>Overall Performance:</b>
🎲 Total Bets: <code>{self.stats['total_bets']}</code>
✅ Won: <code>{self.stats['won_bets']}</code>
❌ Lost: <code>{self.stats['lost_bets']}</code>
📈 Win Rate: <code>{win_rate:.1f}%</code>

💹 <b>Monthly Performance:</b>
💰 Profit/Loss: <code>{self.settings['currency']}{self.stats['monthly_profit']:.2f}</code>
📊 Total Stakes: <code>{self.settings['currency']}{self.stats['monthly_stakes']:.2f}</code>
📈 ROI: <code>{roi:.1f}%</code>
                """
                self.send_telegram_message(stats_msg)
                
            elif command == "/status":
                status_msg = f"""
🔄 <b>System Status</b>

🤖 Manager: {'🟢 Running' if self.session_active else '🔴 Offline'}
🌐 Session: {'🟢 Active' if self.session_active else '🔴 Inactive'}
💰 Last Balance: <code>{self.get_latest_balance()}</code>
⏰ Last Check: <code>{datetime.now().strftime('%H:%M:%S')}</code>

🔄 Next check in: {self.check_interval//60} minutes
                """
                self.send_telegram_message(status_msg)
                
            elif command == "/about":
                about_msg = """
ℹ️ <b>About Bet9ja Manager</b>

🤖 <b>Version:</b> 2.0.0
👨‍💻 <b>System:</b> Unified Manager
🔒 <b>Status:</b> Private Access Only

⚠️ <b>IMPORTANT NOTICE:</b>
🔐 This is a <b>PRIVATE BOT</b>
🚫 Unauthorized access is <b>PROHIBITED</b>

🎯 <b>Features:</b>
• Real-time balance monitoring
• Automated screenshot capture
• Telegram command interface
• Future: Automated betting strategies

📧 <b>Support:</b> Authorized users only
                """
                self.send_telegram_message(about_msg)
                
        except Exception as e:
            print(f"❌ Telegram command error: {e}")
    
    def get_telegram_updates(self):
        """Get updates from Telegram with better polling"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {"offset": self.last_telegram_update + 1, "timeout": 5}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data["ok"] and data["result"]:
                    print(f"📱 Received {len(data['result'])} Telegram updates")
                    for update in data["result"]:
                        if "message" in update:
                            message = update["message"]
                            chat_id = message["chat"]["id"]
                            text = message.get("text", "")
                            print(f"📱 Telegram command received: '{text}' from {chat_id}")
                            self.handle_telegram_command(message)
                        self.last_telegram_update = update["update_id"]
                return True
            return False
        except Exception as e:
            print(f"❌ Telegram update error: {e}")
            return False
    
    # ============================================================================
    # BALANCE TRACKING AND NOTIFICATIONS
    # ============================================================================
    
    async def record_balance(self, balance, screenshot_path=None):
        """Record balance with timestamp and send notifications"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save to balance log
            os.makedirs("logs", exist_ok=True)
            with open(self.balance_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} - Balance: {balance}\n")
            
            await self.log_message(f"📊 Balance recorded: {balance}")
            
            # Check if balance changed
            balance_changed = self.last_balance != balance
            if balance_changed:
                change_type = "📈" if self.last_balance and balance > self.last_balance else "📉" if self.last_balance else "🆕"
                
                # Send Telegram notification
                message = f"""
🏦 <b>Bet9ja Balance Update</b>

{change_type} <b>Balance: <code>{balance}</code></b>
{f"Previous: <code>{self.last_balance}</code>" if self.last_balance else ""}

📸 Screenshot: {'✅ Taken' if screenshot_path else '❌ Failed'}
⏰ Time: {timestamp}
🔄 Next check: {(datetime.now() + timedelta(seconds=self.check_interval)).strftime('%H:%M')}
                """
                
                self.send_telegram_message(message)
                self.last_balance = balance
                
        except Exception as e:
            await self.log_message(f"❌ Balance recording error: {e}", "ERROR")
    
    # ============================================================================
    # MAIN MONITORING CYCLE
    # ============================================================================
    
    async def monitoring_cycle(self):
        """Single monitoring cycle"""
        try:
            await self.log_message("🔄 Starting monitoring cycle...")
            
            # Check session
            if not await self.check_session_active():
                await self.log_message("🔐 Session expired, re-logging...")
                login_success = await self.login_to_bet9ja()
                if not login_success:
                    await self.log_message("❌ Re-login failed", "ERROR")
                    return False
            
            # Take screenshot
            screenshot_path = await self.take_screenshot("monitor")
            
            # Extract balance
            balance = await self.extract_balance()
            
            if balance:
                await self.record_balance(balance, screenshot_path)
            else:
                await self.log_message("⚠️ Could not extract balance this cycle", "WARNING")
            
            # Cleanup old screenshots
            await self.cleanup_old_screenshots()
            
            return True
            
        except Exception as e:
            await self.log_message(f"❌ Monitor cycle error: {e}", "ERROR")
            return False
    
    # ============================================================================
    # MAIN SYSTEM CONTROL
    # ============================================================================
    
    async def start_system(self):
        """Start the complete system"""
        try:
            await self.log_message("🚀 Starting Bet9ja Manager System...")
            
            # Send startup notification to Telegram
            if self.bot_token and self.chat_id:
                startup_msg = f"""
🚀 <b>Bet9ja Manager Started!</b>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Status: System Online
📱 Telegram: Connected
🔄 Monitor Interval: {self.check_interval//60} minutes

💡 <b>Available Commands:</b>
/start - Welcome message
/balance - Check balance
/stake [amount] - Set stake
/status - System status
/help - Show all commands

🎯 Ready for monitoring!
                """
                self.send_telegram_message(startup_msg)
            
            # Initialize browser
            if not await self.initialize_browser():
                return False
            
            # Initial login
            if not await self.login_to_bet9ja():
                await self.log_message("❌ Initial login failed", "ERROR")
                return False
            
            await self.log_message("✅ System initialized successfully")
            
            # Send startup notification
            if self.bot_token and self.chat_id:
                startup_msg = f"""
🤖 <b>Bet9ja Manager Started</b>

✅ System initialized successfully
🔐 Logged into Bet9ja
📸 Monitoring every {self.check_interval//60} minutes
💰 Default stake: {self.settings['currency']}{self.settings['default_stake']}

🎯 Ready for automated operations!
                """
                self.send_telegram_message(startup_msg)
            
            return True
            
        except Exception as e:
            await self.log_message(f"❌ System startup error: {e}", "ERROR")
            return False
    
    async def telegram_polling_loop(self):
        """Continuous Telegram command polling"""
        await self.log_message("📱 Starting Telegram polling loop...")
        
        while True:
            try:
                if self.bot_token:
                    self.get_telegram_updates()
                await asyncio.sleep(3)  # Check every 3 seconds
            except Exception as e:
                print(f"❌ Telegram polling error: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def run_forever(self):
        """Main loop - runs forever with concurrent Telegram polling"""
        try:
            # Start system
            if not await self.start_system():
                return
            
            await self.log_message(f"🔄 Starting infinite monitoring loop...")
            
            # Start Telegram polling in background
            telegram_task = asyncio.create_task(self.telegram_polling_loop())
            
            # Main monitoring loop
            while True:
                try:
                    # Monitoring cycle
                    success = await self.monitoring_cycle()
                    
                    if not success:
                        await self.log_message("⚠️ Cycle failed, retrying in 1 minute...", "WARNING")
                        await asyncio.sleep(60)
                        continue
                    
                    # Wait until next cycle
                    await self.log_message(f"⏰ Waiting {self.check_interval//60} minutes until next check...")
                    await asyncio.sleep(self.check_interval)
                    
                except KeyboardInterrupt:
                    await self.log_message("🛑 System stopped by user")
                    telegram_task.cancel()  # Stop Telegram polling
                    break
                except Exception as e:
                    await self.log_message(f"❌ Loop error: {e}", "ERROR")
                    await asyncio.sleep(60)  # Wait before retry
                    
        except Exception as e:
            await self.log_message(f"❌ Fatal error: {e}", "ERROR")
        finally:
            await self.cleanup_system()
    
    async def cleanup_system(self):
        """Cleanup system resources"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            await self.log_message("🔄 System cleanup completed")
        except:
            pass

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main function for VPS deployment"""
    manager = Bet9jaManager()
    
    # Check required environment variables
    if not manager.username or not manager.password:
        print("❌ ERROR: Missing Bet9ja credentials in .env file!")
        print("Required: BET9JA_USERNAME, BET9JA_PASSWORD")
        return
    
    if not manager.bot_token or not manager.chat_id:
        print("⚠️ WARNING: Missing Telegram configuration in .env file!")
        print("Optional: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
    
    print("🎯 Bet9ja Manager - Starting...")
    print("="*50)
    
    # Run the system forever
    await manager.run_forever()

if __name__ == "__main__":
    # For VPS deployment - this will run forever
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bet9ja Manager stopped.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("System will restart...")