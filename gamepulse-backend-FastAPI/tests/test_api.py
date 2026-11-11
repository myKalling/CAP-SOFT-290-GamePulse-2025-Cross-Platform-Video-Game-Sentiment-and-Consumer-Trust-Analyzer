import unittest
from unittest.mock import Mock, patch

import pyodbc
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import connect, get_connection
from app.main import app, infer_sentiment
from app.main_learning import app as learning_app


class APIEndpointTests(unittest.TestCase):
    def setUp(self):
        self.cursor = Mock()
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        app.dependency_overrides[get_connection] = lambda: self.connection
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(get_connection, None)

    def test_learning_entry_point_and_root(self):
        self.assertIs(learning_app, app)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_direct_list_routes_and_filters(self):
        cases = [
            ("/developers", ("DeveloperID", "DeveloperName"), (1, "Studio"), ()),
            ("/platforms", ("PlatformID", "PlatformName"), (1, "PC"), ()),
            ("/games?developer_id=2&offset=3&limit=4", ("GameID", "Title", "Price"), (1, "Game", 0), (2, 3, 4)),
            ("/game-platforms?game_id=2&offset=3&limit=4", ("GamePlatformsID", "GameID", "Title", "Price", "PlatformID", "PlatformName"), (1, 2, "Game", 0, 1, "PC"), (2, 3, 4)),
            ("/genres?game_id=2&offset=3&limit=4", ("GameID", "GenreID", "Genre"), (2, 1, "Action"), (2, 3, 4)),
            ("/reviews?game_id=2&sentiment=75.5&offset=3&limit=4", ("ReviewID", "GameID", "Title", "Review", "Sentiment", "ReviewDate", "UserID"), (1, 2, "Game", None, 75.5, None, None), (2, 75.5, 3, 4)),
        ]
        for path, columns, row, params in cases:
            with self.subTest(path=path):
                self.cursor.description = [(column,) for column in columns]
                self.cursor.fetchall.return_value = [row]
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()), 1)
                self.assertEqual(self.cursor.execute.call_args.args[1], params)
        self.assertEqual(self.cursor.close.call_count, len(cases))

    def test_validation_and_missing_game(self):
        for path in ("/games?limit=501", "/games?offset=-1", "/games?developer_id=0",
                     "/reviews?sentiment=101", "/genres?game_id=0"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 422)
        self.cursor.description = [("GameID",)]
        self.cursor.fetchall.return_value = []
        self.assertEqual(self.client.get("/games/999").status_code, 404)
        self.assertEqual(self.client.get("/games/999/summary").status_code, 404)

    def test_health_and_summary(self):
        self.cursor.description = [("database_name",)]
        self.cursor.fetchall.return_value = [("GamePulse",)]
        self.assertEqual(self.client.get("/health/db").json(),
                         {"status": "connected", "database": "GamePulse"})
        self.cursor.description = [(name,) for name in (
            "GameID", "Title", "ReviewCount", "AverageSentiment",
            "PositiveReviews", "NegativeReviews", "NeutralReviews")]
        self.cursor.fetchall.return_value = [(1, "Game", 3, 50.123, 1, 1, 1)]
        response = self.client.get("/games/1/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["AverageSentiment"], 50.12)

    def test_sentiment_and_empty_text(self):
        response = self.client.post("/sentiment", json={"text": "Great gameplay, but buggy."})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["mixed"])
        self.assertEqual(self.client.post("/sentiment", json={"text": "  "}).status_code, 422)

    def test_mixed_threshold_uses_unrounded_shares(self):
        analyzer = Mock()
        analyzer.lexicon = {}
        analyzer.polarity_scores.side_effect = [{"compound": 0.75}, {"compound": -0.247}]
        with patch("app.main.SentimentIntensityAnalyzer", return_value=analyzer):
            result = infer_sentiment("good but bad")
        self.assertEqual(result["negative_share"], 0.25)
        self.assertFalse(result["mixed"])


class DatabaseConnectionTests(unittest.TestCase):
    def test_partial_sql_authentication_does_not_fall_back_to_windows(self):
        for env in ({"GAMEPULSE_SQL_USER": "user"}, {"GAMEPULSE_SQL_PASSWORD": "password"}):
            with self.subTest(env=list(env)), patch.dict("os.environ", env, clear=True):
                with patch("app.database.pyodbc.connect") as db_connect:
                    with self.assertLogs("app.database", level="ERROR"):
                        with self.assertRaises(HTTPException) as error:
                            connect()
                    self.assertEqual(error.exception.status_code, 503)
                    db_connect.assert_not_called()

    def test_connection_error_returns_503(self):
        with patch("app.database.connect", side_effect=pyodbc.Error("connection failed")):
            with self.assertLogs("app.database", level="ERROR"):
                with self.assertRaises(HTTPException) as error:
                    next(get_connection())
        self.assertEqual(error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
