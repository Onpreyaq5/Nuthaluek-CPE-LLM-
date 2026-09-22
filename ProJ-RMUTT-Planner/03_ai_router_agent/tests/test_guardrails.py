import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.guardrails import validate_tools_for_intent
from src.models import ClassificationResult, Slots, ToolCall

class TestGuardrails(unittest.TestCase):
    def test_schedule_conflict_not_called(self):
        classification = ClassificationResult(
            intent="SCHEDULE_CONFLICT",
            confidence=0.9,
            reasoning="test",
            source="keyword",
            slots=Slots()
        )
        tools = []
        ok, reason = validate_tools_for_intent(classification, tools)
        self.assertFalse(ok)
        self.assertIn("ไม่สามารถตรวจสอบตารางชนได้โดยไม่ผ่านระบบตรวจ", reason)

    def test_schedule_conflict_failed(self):
        classification = ClassificationResult(
            intent="SCHEDULE_CONFLICT",
            confidence=0.9,
            reasoning="test",
            source="keyword",
            slots=Slots()
        )
        tools = [
            ToolCall(
                tool="check_conflicts",
                args={"sections": ["CPE101"]},
                success=False,
                error="ConnectError",
                result=None
            )
        ]
        ok, reason = validate_tools_for_intent(classification, tools)
        self.assertFalse(ok)
        self.assertIn("ไม่ตอบสนองในขณะนี้", reason)

    def test_schedule_conflict_success(self):
        classification = ClassificationResult(
            intent="SCHEDULE_CONFLICT",
            confidence=0.9,
            reasoning="test",
            source="keyword",
            slots=Slots()
        )
        tools = [
            ToolCall(
                tool="check_conflicts",
                args={"sections": ["CPE101"]},
                success=True,
                error=None,
                result={"conflicts": []}
            )
        ]
        ok, reason = validate_tools_for_intent(classification, tools)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

if __name__ == '__main__':
    unittest.main()
