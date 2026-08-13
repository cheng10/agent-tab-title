from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class InstallerTests(unittest.TestCase):
    def test_default_install_is_codex_only_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = {**os.environ, "HOME": directory}
            command = [sys.executable, str(ROOT / "install.py")]
            subprocess.run(command, env=env, check=True, capture_output=True, text=True)
            second = subprocess.run(
                command, env=env, check=True, capture_output=True, text=True
            )

            self.assertTrue((home / ".codex" / "hooks.json").exists())
            self.assertFalse((home / ".trae" / "cli" / "hooks.json").exists())
            self.assertFalse((home / ".local" / "bin" / "byobu-select-session").exists())
            self.assertNotIn("backup:", second.stdout)

            hooks = json.loads(
                (home / ".codex" / "hooks.json").read_text(encoding="utf-8")
            )
            command_text = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
            self.assertIn("--title-source safe", command_text)
            self.assertIn("--product codex", command_text)

    def test_prompt_mode_and_experimental_adapter_are_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "HOME": directory}
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "install.py"),
                    "--products",
                    "codex,trae-next",
                    "--title-source",
                    "prompt",
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            hooks = json.loads(
                (Path(directory) / ".trae" / "cli" / "hooks.json").read_text(
                    encoding="utf-8"
                )
            )
            command_text = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
            self.assertIn("--product trae-next", command_text)
            self.assertIn("--title-source prompt", command_text)

    def test_enhanced_byobu_picker_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = {**os.environ, "HOME": directory}
            subprocess.run(
                [sys.executable, str(ROOT / "install.py"), "--byobu-picker"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            picker = home / ".local" / "bin" / "byobu-select-session"
            self.assertTrue(picker.exists())
            self.assertTrue(os.access(picker, os.X_OK))


if __name__ == "__main__":
    unittest.main()
