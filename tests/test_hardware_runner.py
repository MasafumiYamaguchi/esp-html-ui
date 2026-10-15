"""Guard against accepting missing hardware evidence as a successful test."""
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    "hardware_runner", Path(__file__).resolve().parents[1] / "scripts/test_hardware.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RecordedBoard:
    def __init__(self, lines=(), statuses=()):
        self.lines = []
        self.statuses = []
        self.pending_lines = list(lines)
        self.pending_statuses = list(statuses)

    def send(self, command):
        pass

    def wait(self, predicate, timeout=10):
        self.lines.extend(self.pending_lines)
        self.pending_lines.clear()
        return "TEST_DONE failures=0"

    def drain(self, seconds):
        self.lines.extend(self.pending_lines)
        self.statuses.extend(self.pending_statuses)


class HardwareEvidenceTests(unittest.TestCase):
    def test_serial_timeout_does_not_split_a_status_record(self):
        board = runner.Board.__new__(runner.Board)
        board.serial = Mock()
        board.serial.readline.side_effect = [b"STATUS uptime=2000 count=0 focus=inc",
                                            b"rement heap=42\r\n"]
        board.log = io.BytesIO()
        board.partial_line = bytearray()
        board.lines = []
        board.statuses = []
        self.assertEqual(board.line(), "")
        self.assertIn("focus=increment", board.line())
        self.assertEqual(board.statuses[0]["focus"], "increment")

    def test_done_without_checks_is_not_a_pass(self):
        result = runner.self_test(RecordedBoard())
        self.assertFalse(result["passed"])
        self.assertIn("lcd_gram_readback", result["missing"])

    def test_failed_check_overrides_successful_done_marker(self):
        lines = [f"CHECK PASS {name}" for name in runner.EXPECTED_CHECKS]
        lines.append("CHECK FAIL lcd_gram_readback")
        result = runner.self_test(RecordedBoard(lines))
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed"], ["lcd_gram_readback"])

    def test_counter_evidence_cannot_pass_the_layout_test(self):
        board = RecordedBoard([f"CHECK PASS {name}" for name in runner.EXPECTED_CHECKS])
        result = runner.self_test(board, layout_check=True)
        self.assertFalse(result["passed"])
        self.assertIn("description_wrapped", result["missing"])

    def test_no_button_activity_is_incomplete(self):
        result = runner.manual(RecordedBoard(), 1, "confirmed")
        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "incomplete")

    def test_physical_sequence_needs_an_optical_confirmation(self):
        board = RecordedBoard(
            ["PHYSICAL_KEY next=0 enter=1", "PHYSICAL_KEY next=0 enter=0",
             "PHYSICAL_KEY next=1 enter=0", "PHYSICAL_KEY next=0 enter=0",
             "PHYSICAL_KEY next=0 enter=1", "PHYSICAL_KEY next=0 enter=0"],
            [{"count": "1", "focus": "increment"}, {"count": "1", "focus": "reset"},
             {"count": "0", "focus": "reset"}])
        result = runner.manual(board, 1, "unverified")
        self.assertTrue(result["physical_sequence_passed"])
        self.assertFalse(result["passed"])
        self.assertTrue(runner.manual(board, 1, "confirmed")["passed"])

    def test_old_physical_logs_are_not_current_evidence(self):
        board = RecordedBoard()
        board.lines = ["PHYSICAL_KEY next=0 enter=1", "PHYSICAL_KEY next=0 enter=0",
                       "PHYSICAL_KEY next=1 enter=0", "PHYSICAL_KEY next=0 enter=0",
                       "PHYSICAL_KEY next=0 enter=1", "PHYSICAL_KEY next=0 enter=0"]
        board.statuses = [{"count": "1", "focus": "increment"},
                          {"count": "1", "focus": "reset"}, {"count": "0", "focus": "reset"}]
        self.assertFalse(runner.manual(board, 1, "confirmed")["passed"])

    def test_wrong_order_does_not_prove_the_manual_sequence(self):
        board = RecordedBoard(
            ["PHYSICAL_KEY next=1 enter=1", "PHYSICAL_KEY next=0 enter=0"],
            [{"count": "0", "focus": "reset"}, {"count": "1", "focus": "increment"}])
        self.assertFalse(runner.manual(board, 1, "confirmed")["passed"])


if __name__ == "__main__":
    unittest.main()
