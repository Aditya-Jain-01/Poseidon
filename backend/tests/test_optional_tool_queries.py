"""Regression tests for provider-generated null search arguments."""

from unittest.mock import patch

from app.tools.crm import crm_read
from app.tools.notes_reminders import notes_reminders_read
from app.tools.registry import get_tool


def test_notes_read_accepts_null_as_read_all() -> None:
    stored = {
        "notes": [{"id": "n1", "text": "alpha"}],
        "reminders": [{"id": "r1", "text": "beta"}],
    }
    with patch("app.tools.notes_reminders.read_json", return_value=stored):
        assert notes_reminders_read(None) == stored


def test_crm_read_accepts_null_as_read_all() -> None:
    stored = {"contacts": [{"id": "c1", "name": "Ada"}]}
    with patch("app.tools.crm.read_json", return_value=stored):
        result = crm_read(None)
    assert result == {"contacts": stored["contacts"], "count": 1}


def test_notes_read_schema_allows_string_or_null_query() -> None:
    tool = get_tool("notes_reminders_read")
    assert tool is not None
    query_schema = tool["schema"]["function"]["parameters"]["properties"]["query"]
    assert query_schema["anyOf"] == [{"type": "string"}, {"type": "null"}]
