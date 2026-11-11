import unittest
from unittest.mock import Mock

import pyodbc
from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app
from app.procedures import execute_procedure


class ProcedureEndpointTests(unittest.TestCase):
    def setUp(self):
        self.cursor = Mock()
        self.cursor.description = [("Result",)]
        self.cursor.fetchall.return_value = [(42,)]
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        app.dependency_overrides[get_connection] = lambda: self.connection
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(get_connection, None)

    def test_all_procedures_use_expected_sql_and_parameters(self):
        cases = [
            ("/procedures/developers", "EXEC dbo.GetAllDevelopers", (), True),
            ("/procedures/developers/7", "EXEC dbo.GetDevelopers @DeveloperID = ?", (7,), False),
            ("/procedures/platforms", "EXEC dbo.GetAllPlatforms", (), True),
            ("/procedures/platforms/7", "EXEC dbo.GetPlatform @PlatformID = ?", (7,), False),
            ("/procedures/genres", "EXEC dbo.GetAllGenres", (), True),
            ("/procedures/genres/7", "EXEC dbo.GetGenre @GenreID = ?", (7,), False),
            ("/procedures/games", "EXEC dbo.GetALLGames", (), True),
            ("/procedures/games/search?search_term=O%27Brien", "EXEC dbo.SearchGames @SearchTerm = ?", ("O'Brien",), True),
            ("/procedures/games/top/free", "EXEC dbo.GetTop10FreeGames", (), True),
            ("/procedures/games/top/paid", "EXEC dbo.GetTop10PaidGames", (), True),
            ("/procedures/games/7", "EXEC dbo.GetGame @GameID = ?", (7,), False),
            ("/procedures/games/7/reviews", "EXEC dbo.GetGameReviews @GameID = ?", (7,), True),
            ("/procedures/reviews/7", "EXEC dbo.GetReview @ReviewID = ?", (7,), False),
        ]
        for path, sql, params, is_list in cases:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [{"Result": 42}] if is_list else {"Result": 42})
                self.cursor.execute.assert_called_with(sql, params)
        self.assertEqual(self.cursor.close.call_count, len(cases))

    def test_empty_and_missing_results(self):
        self.cursor.fetchall.return_value = []
        self.assertEqual(self.client.get("/procedures/games").json(), [])
        self.assertEqual(self.client.get("/procedures/games/9").status_code, 404)

    def test_search_length_and_default(self):
        self.assertEqual(self.client.get("/procedures/games/search").status_code, 200)
        self.cursor.execute.assert_called_with("EXEC dbo.SearchGames @SearchTerm = ?", ("",))
        self.assertEqual(
            self.client.get("/procedures/games/search", params={"search_term": "x" * 101}).status_code,
            422,
        )

    def test_sql_error_result_is_not_success(self):
        self.cursor.description = [("ErrorMessage",)]
        self.cursor.fetchall.return_value = [("database detail",)]
        with self.assertLogs("app.procedures", level="ERROR"):
            response = self.client.get("/procedures/games")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Stored procedure execution failed")
        self.cursor.close.assert_called_once()

    def test_odbc_error_is_not_success(self):
        self.cursor.execute.side_effect = pyodbc.Error("database detail")
        with self.assertLogs("app.procedures", level="ERROR"):
            response = self.client.get("/procedures/games")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("database detail", response.text)
        self.cursor.close.assert_called_once()

    def test_skips_non_row_results(self):
        self.cursor.description = None

        def nextset():
            self.cursor.description = [("Result",)]
            return True

        self.cursor.nextset.side_effect = nextset
        self.assertEqual(execute_procedure(self.connection, "EXEC dbo.GetALLGames"), [{"Result": 42}])
        self.cursor.close.assert_called_once()

    def test_missing_result_set_is_error(self):
        self.cursor.description = None
        self.cursor.nextset.return_value = False
        with self.assertLogs("app.procedures", level="ERROR"):
            response = self.client.get("/procedures/games")
        self.assertEqual(response.status_code, 500)
        self.cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
