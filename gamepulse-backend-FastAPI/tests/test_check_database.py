import os
import unittest
from unittest.mock import Mock, patch

import pyodbc

import check_database


class DatabaseCheckTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"GAMEPULSE_SQL_DRIVER": "Test driver"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        dotenv = patch.object(check_database, "load_dotenv")
        dotenv.start()
        self.addCleanup(dotenv.stop)

    def test_missing_driver_does_not_attempt_connection(self):
        with patch.object(check_database.pyodbc, "drivers", return_value=[]), \
             patch.object(check_database, "connect") as connect:
            self.assertEqual(check_database.main(), 1)
            connect.assert_not_called()

    def test_connection_failure_is_reported(self):
        with patch.object(check_database.pyodbc, "drivers", return_value=["Test driver"]), \
             patch.object(check_database, "connect", side_effect=pyodbc.Error("connection failed")):
            self.assertEqual(check_database.main(), 1)

    def test_successful_connection_is_closed(self):
        connection = Mock()
        with patch.object(check_database.pyodbc, "drivers", return_value=["Test driver"]), \
             patch.object(check_database, "connect", return_value=connection):
            self.assertEqual(check_database.main(), 0)
            connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
