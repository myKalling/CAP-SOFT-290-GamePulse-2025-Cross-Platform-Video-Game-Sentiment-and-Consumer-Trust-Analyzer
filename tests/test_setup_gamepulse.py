import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import setup_gamepulse


class SetupTests(unittest.TestCase):
    def test_environment_file_is_created_without_overwriting_existing_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / ".env.example").write_text("EXAMPLE=value\n", encoding="utf-8")
            setup_gamepulse.copy_environment(directory)
            self.assertEqual((directory / ".env").read_text(encoding="utf-8"), "EXAMPLE=value\n")
            (directory / ".env").write_text("EXISTING=value\n", encoding="utf-8")
            setup_gamepulse.copy_environment(directory)
            self.assertEqual((directory / ".env").read_text(encoding="utf-8"), "EXISTING=value\n")

    def test_unsupported_node_stops_before_changing_files(self):
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="23.0.0\n")
        with patch.object(setup_gamepulse.shutil, "which", return_value="executable"), \
             patch.object(setup_gamepulse.subprocess, "run", return_value=result), \
             patch.object(setup_gamepulse, "copy_environment") as copy:
            with self.assertRaisesRegex(RuntimeError, "Unsupported Node.js"):
                setup_gamepulse.main([])
            copy.assert_not_called()

    def test_install_failure_stops_setup(self):
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="24.3.0\n")
        with patch.object(setup_gamepulse.shutil, "which", return_value="executable"), \
             patch.object(setup_gamepulse.subprocess, "run", return_value=result), \
             patch.object(setup_gamepulse, "copy_environment"), \
             patch.object(setup_gamepulse, "install_python", side_effect=subprocess.CalledProcessError(1, "pip")), \
             patch.object(setup_gamepulse, "run") as run:
            with self.assertRaises(subprocess.CalledProcessError):
                setup_gamepulse.main([])
            run.assert_not_called()

    def test_check_only_does_not_change_files_or_install(self):
        with patch.object(setup_gamepulse, "preflight", return_value="npm"), \
             patch.object(setup_gamepulse, "copy_environment") as copy, \
             patch.object(setup_gamepulse, "install_python") as install, \
             patch.object(setup_gamepulse, "check_database") as database, \
             patch.object(setup_gamepulse, "run") as run:
            setup_gamepulse.main(["--check-only"])
            copy.assert_not_called()
            install.assert_not_called()
            database.assert_not_called()
            run.assert_not_called()

    def test_database_check_is_opt_in_and_runs_before_install(self):
        with patch.object(setup_gamepulse, "preflight", return_value="npm"), \
             patch.object(setup_gamepulse, "check_database", side_effect=RuntimeError("database unavailable")) as database, \
             patch.object(setup_gamepulse, "copy_environment") as copy:
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                setup_gamepulse.main(["--check-database"])
            database.assert_called_once()
            copy.assert_not_called()

    def test_database_check_requires_backend_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "Run setup first"):
                setup_gamepulse.check_database(Path(temporary))


if __name__ == "__main__":
    unittest.main()
