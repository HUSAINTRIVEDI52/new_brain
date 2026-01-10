import sys
import os
import unittest
import json
import logging
from io import StringIO
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logger import log_event, setup_logger

class TestLogging(unittest.TestCase):
    def setUp(self):
        self.log_output = StringIO()
        self.logger = setup_logger("test_logger")
        # Clear existing handlers
        self.logger.handlers = []
        handler = logging.StreamHandler(self.log_output)
        from utils.logger import JsonFormatter
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)

    def test_json_format_and_fields(self):
        print("\n--- Testing JSON Log Format ---")
        extra_data = {"user_id": "user-123", "duration_ms": 150, "status": "success"}
        
        # We need to use the logger directly or patch log_event
        from unittest.mock import patch
        with patch('utils.logger.logger', self.logger):
            log_event(logging.INFO, "test_event", "Test message", **extra_data)
        
        output = self.log_output.getvalue().strip()
        print(f"Log output: {output}")
        
        log_json = json.loads(output)
        self.assertEqual(log_json["level"], "INFO")
        self.assertEqual(log_json["event"], "test_event")
        self.assertEqual(log_json["user_id"], "user-123")
        self.assertEqual(log_json["duration_ms"], 150)
        self.assertIn("timestamp", log_json)

    def test_privacy_enforcement(self):
        print("\n--- Testing Logging Privacy (No raw content) ---")
        # Attempt to log sensitive data
        sensitive_data = {
            "user_id": "user-123",
            "raw_text": "THIS SHOULD BE HIDDEN",
            "embedding": [0.1, 0.2, 0.3]
        }
        
        with patch('utils.logger.logger', self.logger):
            log_event(logging.INFO, "privacy_test", "Checking privacy", **sensitive_data)
        
        output = self.log_output.getvalue().strip()
        log_json = json.loads(output)
        
        print(f"Sanitized Log: {output}")
        
        # Verify sensitive keys are NOT present
        self.assertNotIn("raw_text", log_json)
        self.assertNotIn("embedding", log_json)
        # Verify safe keys ARE present
        self.assertEqual(log_json["user_id"], "user-123")
        self.assertEqual(log_json["event"], "privacy_test")

if __name__ == "__main__":
    unittest.main()
