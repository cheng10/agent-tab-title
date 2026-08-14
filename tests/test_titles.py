from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sqlite3


MODULE_PATH = Path(__file__).parents[1] / "agent-tab-title.py"
SPEC = importlib.util.spec_from_file_location("agent_tab_title", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TitleTests(unittest.TestCase):
    def test_tmux_binary_uses_running_server_executable(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TMUX": "/tmp/tmux-1001/iterm36,2204772,0"},
            clear=False,
        ), mock.patch.object(MODULE.Path, "exists", return_value=True):
            self.assertEqual(MODULE.tmux_binary(), "/proc/2204772/exe")

    def test_tmux_binary_can_be_overridden(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"AGENT_TAB_TITLE_TMUX_BIN": "/opt/tmux/bin/tmux"},
            clear=False,
        ):
            self.assertEqual(MODULE.tmux_binary(), "/opt/tmux/bin/tmux")

    def test_normalize_slug_has_no_project_specific_prefix(self) -> None:
        self.assertEqual(MODULE.normalize_slug("codex_fix_title_refresh"), "fix-title-refresh")
        self.assertEqual(MODULE.normalize_slug("customer_repository"), "customer-repository")

    def test_safe_prompt_removes_url_and_email(self) -> None:
        title = MODULE.safe_prompt_title("Review login flow https://example.test a@example.com")
        self.assertEqual(title, "Review login flow")

    def test_safe_prompt_rejects_token_shapes(self) -> None:
        self.assertEqual(MODULE.safe_prompt_title("debug sk-abcdefghijklmnop"), "")
        self.assertEqual(
            MODULE.safe_prompt_title("debug eyJabcdefghijk.abcdefghijklmnop.abcdefghijklmnop"),
            "",
        )

    def test_safe_mode_does_not_use_raw_prompt(self) -> None:
        with mock.patch.object(MODULE, "state_database", return_value=None):
            title = MODULE.read_task(
                "codex",
                "12345678-1234-1234-1234-123456789abc",
                "confidential customer migration",
                "safe",
            )
        self.assertEqual(title, "codex-789abc")

    def test_safe_mode_does_not_use_first_user_message_from_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state_5.sqlite"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE threads (id TEXT PRIMARY KEY, title TEXT, first_user_message TEXT)"
            )
            connection.execute(
                "INSERT INTO threads VALUES (?, ?, ?)",
                (
                    "12345678-1234-1234-1234-123456789abc",
                    "",
                    "confidential database prompt",
                ),
            )
            connection.commit()
            connection.close()
            with mock.patch.object(MODULE, "state_database", return_value=database):
                title = MODULE.read_task(
                    "codex",
                    "12345678-1234-1234-1234-123456789abc",
                    "",
                    "safe",
                )
        self.assertEqual(title, "codex-789abc")

    def test_prompt_mode_is_explicit(self) -> None:
        with mock.patch.object(MODULE, "state_database", return_value=None):
            title = MODULE.read_task(
                "codex",
                "12345678-1234-1234-1234-123456789abc",
                "Improve tab titles",
                "prompt",
            )
        self.assertEqual(title, "Improve tab titles")

    def test_legacy_trae_adapter_uses_stable_fallback_label(self) -> None:
        with mock.patch.object(MODULE, "state_database", return_value=None):
            title = MODULE.read_task(
                "trae",
                "12345678-1234-1234-1234-123456789abc",
                "",
                "safe",
            )
        self.assertEqual(title, "trae-789abc")

    def test_codex_home_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "state_12.sqlite"
            expected.touch()
            (Path(directory) / "state_9.sqlite").touch()
            with mock.patch.dict(os.environ, {"CODEX_HOME": directory}):
                self.assertEqual(MODULE.state_database("codex"), expected)


if __name__ == "__main__":
    unittest.main()
