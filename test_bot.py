#!/usr/bin/env python3
"""
Unit tests for the bot.
"""

import unittest
from bot import Bot


class TestBot(unittest.TestCase):
    """Test cases for the Bot class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bot = Bot("Test Bot")
    
    def test_bot_initialization(self):
        """Test that bot initializes with correct name."""
        self.assertEqual(self.bot.name, "Test Bot")
    
    def test_greet(self):
        """Test greeting message."""
        greeting = self.bot.greet()
        self.assertIn("Test Bot", greeting)
        self.assertIn("Hello", greeting)
    
    def test_get_time(self):
        """Test time retrieval."""
        time_msg = self.bot.get_time()
        self.assertIn("current time", time_msg)
    
    def test_get_uptime(self):
        """Test uptime retrieval."""
        uptime_msg = self.bot.get_uptime()
        self.assertIn("running for", uptime_msg)
        self.assertIn("seconds", uptime_msg)
    
    def test_process_greeting_messages(self):
        """Test processing of greeting messages."""
        greetings = ['hi', 'hello', 'hey', 'HI', 'HELLO']
        for greeting in greetings:
            response = self.bot.process_message(greeting)
            self.assertIn("Hello", response)
    
    def test_process_time_message(self):
        """Test processing of time request."""
        response = self.bot.process_message("time")
        self.assertIn("current time", response)
    
    def test_process_uptime_message(self):
        """Test processing of uptime request."""
        response = self.bot.process_message("uptime")
        self.assertIn("running for", response)
    
    def test_process_help_message(self):
        """Test processing of help request."""
        response = self.bot.process_message("help")
        self.assertIn("Available commands", response)
        self.assertIn("hi/hello/hey", response)
    
    def test_process_quit_message(self):
        """Test processing of quit request."""
        quit_messages = ['quit', 'exit', 'bye']
        for msg in quit_messages:
            response = self.bot.process_message(msg)
            self.assertIn("Goodbye", response)
    
    def test_process_unknown_message(self):
        """Test processing of unknown message."""
        response = self.bot.process_message("unknown command")
        self.assertIn("received your message", response)
        self.assertIn("help", response.lower())
    
    def test_get_help(self):
        """Test help message content."""
        help_msg = self.bot.get_help()
        self.assertIn("Available commands", help_msg)
        self.assertIn("hi/hello/hey", help_msg)
        self.assertIn("time", help_msg)
        self.assertIn("uptime", help_msg)
        self.assertIn("quit/exit/bye", help_msg)


if __name__ == "__main__":
    unittest.main()
