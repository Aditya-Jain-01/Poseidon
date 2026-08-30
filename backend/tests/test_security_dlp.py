"""Unit tests for Data Loss Prevention (DLP) Scanner."""

import unittest
from app.security.dlp import DLPScanner


class TestDLPScanner(unittest.TestCase):
    """Test suite for outbound DLP scanning and redaction."""

    def test_benign_text_unchanged(self):
        """Regular agent response is unchanged."""
        text = "Your meeting with Alex is scheduled for tomorrow at 2:00 PM."
        res = DLPScanner.scan_and_redact(text)
        self.assertTrue(res.is_safe)
        self.assertEqual(res.sanitized_text, text)
        self.assertEqual(res.redaction_count, 0)

    def test_redacts_openai_api_key(self):
        """OpenAI / OpenRouter API keys are scrubbed."""
        text = "Here is your key: sk-abcdef1234567890abcdef1234567890. Keep it safe!"
        res = DLPScanner.scan_and_redact(text)
        self.assertFalse(res.is_safe)
        self.assertIn("[REDACTED_API_KEY]", res.sanitized_text)
        self.assertNotIn("sk-abcdef1234567890", res.sanitized_text)
        self.assertEqual(res.redaction_count, 1)

    def test_redacts_aws_and_github_tokens(self):
        """AWS and GitHub credentials are scrubbed."""
        text = "AWS key AKIA1234567890ABCDEF and GitHub token ghp_123456789012345678901234567890123456"
        res = DLPScanner.scan_and_redact(text)
        self.assertFalse(res.is_safe)
        self.assertIn("[REDACTED_AWS_KEY]", res.sanitized_text)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", res.sanitized_text)
        self.assertNotIn("AKIA1234567890ABCDEF", res.sanitized_text)

    def test_redacts_private_key(self):
        """RSA Private Key blocks are redacted."""
        text = (
            "Here is the certificate:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA0Y3...\n"
            "-----END RSA PRIVATE KEY-----"
        )
        res = DLPScanner.scan_and_redact(text)
        self.assertFalse(res.is_safe)
        self.assertIn("[REDACTED_PRIVATE_KEY]", res.sanitized_text)
        self.assertNotIn("MIIEowIBAAKCAQEA0Y3", res.sanitized_text)

    def test_redacts_ssn(self):
        """Social Security Numbers are redacted."""
        text = "User's SSN on file is 000-12-3456."
        res = DLPScanner.scan_and_redact(text)
        self.assertFalse(res.is_safe)
        self.assertIn("[REDACTED_SSN]", res.sanitized_text)
        self.assertNotIn("000-12-3456", res.sanitized_text)


if __name__ == "__main__":
    unittest.main()
