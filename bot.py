#!/usr/bin/env python3
"""
A simple bot for basic communication and interactions.
"""

import sys
from datetime import datetime


class Bot:
    """A simple bot class for handling basic communication."""
    
    def __init__(self, name="SJ Bot"):
        """Initialize the bot with a name."""
        self.name = name
        self.start_time = datetime.now()
    
    def greet(self):
        """Greet the user."""
        return f"Hello! I'm {self.name}. How can I help you today?"
    
    def get_time(self):
        """Get the current time."""
        return f"The current time is: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    def get_uptime(self):
        """Get bot uptime."""
        uptime = datetime.now() - self.start_time
        return f"I've been running for {uptime.total_seconds():.2f} seconds"
    
    def process_message(self, message):
        """Process a user message and return a response."""
        message_lower = message.lower().strip()
        
        if message_lower in ['hi', 'hello', 'hey']:
            return self.greet()
        elif message_lower in ['time', 'what time is it']:
            return self.get_time()
        elif message_lower in ['uptime', 'how long have you been running']:
            return self.get_uptime()
        elif message_lower in ['help', '?']:
            return self.get_help()
        elif message_lower in ['quit', 'exit', 'bye']:
            return "Goodbye! Have a great day!"
        else:
            return f"I received your message: '{message}'. Type 'help' for available commands."
    
    def get_help(self):
        """Return help information."""
        return """Available commands:
- hi/hello/hey: Greet the bot
- time: Get current time
- uptime: Get bot uptime
- help: Show this help message
- quit/exit/bye: Exit the bot"""
    
    def run(self):
        """Run the bot in interactive mode."""
        print(self.greet())
        print("Type 'help' for available commands or 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input(f"{self.name}> ").strip()
                if not user_input:
                    continue
                
                response = self.process_message(user_input)
                print(response)
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break


def main():
    """Main entry point for the bot."""
    bot = Bot()
    bot.run()


if __name__ == "__main__":
    main()
