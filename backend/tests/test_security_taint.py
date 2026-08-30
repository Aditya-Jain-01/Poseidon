"""Unit tests for Taint Tracking and Provenance Downgrade."""

import unittest
from app.security.taint import TaintTracker, is_channel_untrusted, BASE_AUTORUN_TOOLS, BASE_APPROVAL_REQUIRED_TOOLS


class TestTaintTracking(unittest.TestCase):
    """Test suite for taint tracking and dynamic tool tier downgrade."""

    def test_channel_trust_classification(self):
        """Web/CLI is trusted; Telegram/Email/MCP untrusted are untrusted."""
        self.assertFalse(is_channel_untrusted("web"))
        self.assertFalse(is_channel_untrusted("web_operator"))
        self.assertFalse(is_channel_untrusted("cli"))
        self.assertFalse(is_channel_untrusted("local"))

        self.assertTrue(is_channel_untrusted("telegram"))
        self.assertTrue(is_channel_untrusted("email"))
        self.assertTrue(is_channel_untrusted("mcp_untrusted"))
        self.assertTrue(is_channel_untrusted("incoming_webhook"))

    def test_auto_run_tool_in_trusted_context(self):
        """Read tool in trusted context auto-runs without approval."""
        res = TaintTracker.evaluate_tool_tier("crm_read", is_tainted=False)
        self.assertFalse(res["requires_approval"])
        self.assertEqual(res["tier"], "auto_run")
        self.assertFalse(res["downgraded_by_taint"])

    def test_auto_run_tool_downgraded_when_tainted(self):
        """Read tool in tainted context is downgraded to require approval."""
        res = TaintTracker.evaluate_tool_tier("crm_read", is_tainted=True)
        self.assertTrue(res["requires_approval"])
        self.assertEqual(res["tier"], "downgraded_approval_required")
        self.assertTrue(res["downgraded_by_taint"])
        self.assertTrue(any("TAINTED" in r for r in res["reasons"]))

    def test_write_tool_always_requires_approval(self):
        """Write tools always require approval whether context is tainted or not."""
        res_trusted = TaintTracker.evaluate_tool_tier("crm_write", is_tainted=False)
        self.assertTrue(res_trusted["requires_approval"])
        self.assertEqual(res_trusted["tier"], "approval_required")
        self.assertFalse(res_trusted["downgraded_by_taint"])

        res_tainted = TaintTracker.evaluate_tool_tier("crm_write", is_tainted=True)
        self.assertTrue(res_tainted["requires_approval"])
        self.assertEqual(res_tainted["tier"], "approval_required")


if __name__ == "__main__":
    unittest.main()
