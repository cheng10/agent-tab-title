from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "byobu-session-picker.py"
SPEC = importlib.util.spec_from_file_location("byobu_session_picker", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ByobuPickerTests(unittest.TestCase):
    def test_label_combines_task_and_repository_context(self) -> None:
        session = MODULE.Session(
            name="351",
            windows=1,
            attached=False,
            group="351",
            task="fix-title-refresh",
            context="agent-tab-title:main*",
        )
        label = MODULE.session_label(session, 90)
        self.assertIn("351", label)
        self.assertIn("fix-title-refresh | agent-tab-title:main*", label)
        self.assertIn("[1w detached]", label)

    def test_label_truncates_long_titles(self) -> None:
        session = MODULE.Session("407", 2, True, "407", "x" * 100, "repo:main")
        label = MODULE.session_label(session, 64)
        self.assertIn("…", label)
        self.assertIn("[2w attached]", label)

    def test_control_characters_are_removed(self) -> None:
        self.assertEqual(MODULE.clean("hello\nworld\x1btitle"), "hello world title")
        self.assertEqual(MODULE.clean("⠇ repo:main"), "repo:main")

    def test_cjk_characters_use_two_terminal_columns(self) -> None:
        self.assertEqual(MODULE.display_width("修复 ab"), 7)


if __name__ == "__main__":
    unittest.main()
