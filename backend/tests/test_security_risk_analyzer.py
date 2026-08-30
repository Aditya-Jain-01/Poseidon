"""Unit tests for Tool Risk Analyzer and Parameter Diff Generator."""

import unittest
from app.security.risk_analyzer import RiskAnalyzer


class TestRiskAnalyzer(unittest.TestCase):
    """Test suite for tool call risk calculation and parameter diffing."""

    def test_low_risk_read_tool(self):
        """Read tool with benign parameters has low risk."""
        analysis = RiskAnalyzer.analyze_tool_call(
            tool_name="calendar_read",
            arguments={"start_date": "2026-09-01"},
            is_tainted=False,
        )
        self.assertEqual(analysis["risk_level"], "low")
        self.assertEqual(len(analysis["warnings"]), 0)
        self.assertEqual(len(analysis["dangerous_params"]), 0)

    def test_medium_risk_standard_write_tool(self):
        """Standard write tool has medium risk."""
        analysis = RiskAnalyzer.analyze_tool_call(
            tool_name="notes_reminders_create",
            arguments={"title": "Buy groceries", "body": "Milk, eggs, bread"},
            is_tainted=False,
        )
        self.assertEqual(analysis["risk_level"], "medium")

    def test_high_risk_tainted_write(self):
        """Write tool invoked from tainted context is high risk."""
        analysis = RiskAnalyzer.analyze_tool_call(
            tool_name="notes_reminders_create",
            arguments={"title": "Meeting notes"},
            is_tainted=True,
        )
        self.assertEqual(analysis["risk_level"], "high")
        self.assertTrue(any("TAINTED" in w for w in analysis["warnings"]))

    def test_high_risk_dangerous_url_parameter(self):
        """Tool call with external URL parameter is flagged high risk."""
        analysis = RiskAnalyzer.analyze_tool_call(
            tool_name="crm_write",
            arguments={"customer_id": "123", "website": "https://suspicious-domain.com/webhook"},
            is_tainted=False,
        )
        self.assertEqual(analysis["risk_level"], "high")
        self.assertEqual(len(analysis["dangerous_params"]), 1)
        self.assertEqual(analysis["dangerous_params"][0]["param"], "website")

    def test_parameter_diff_generation(self):
        """Diff between original values and updated values is computed accurately."""
        orig = {"title": "Team Standup", "time": "10:00"}
        new = {"title": "Urgent Sync", "time": "10:00"}
        analysis = RiskAnalyzer.analyze_tool_call(
            tool_name="calendar_update",
            arguments=new,
            original_values=orig,
        )
        self.assertIn("title", analysis["diff"])
        self.assertEqual(analysis["diff"]["title"]["old"], "Team Standup")
        self.assertEqual(analysis["diff"]["title"]["new"], "Urgent Sync")
        self.assertNotIn("time", analysis["diff"])


if __name__ == "__main__":
    unittest.main()
