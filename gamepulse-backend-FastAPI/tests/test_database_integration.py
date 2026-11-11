"""Opt-in, read-only tests against a restored GamePulse SQL Server database."""

import os
import unittest

from fastapi.testclient import TestClient

from app.main import app


@unittest.skipUnless(os.getenv("GAMEPULSE_TEST_DATABASE") == "1", "requires a restored GamePulse database")
class DatabaseIntegrationTests(unittest.TestCase):
    def test_all_database_routes(self):
        with TestClient(app) as client:
            def get(path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, f"{path}: {response.text}")
                return response.json()

            self.assertEqual(get("/health/db")["status"], "connected")
            developers = get("/developers")
            platforms = get("/platforms")
            games = get("/games?limit=1")
            genres = get("/procedures/genres")
            reviews = get("/reviews?limit=1")
            for name, rows in (("developers", developers), ("platforms", platforms),
                               ("games", games), ("genres", genres), ("reviews", reviews)):
                self.assertTrue(rows, f"Integration test requires at least one {name} row")

            developer_id = developers[0]["DeveloperID"]
            platform_id = platforms[0]["PlatformID"]
            game_id = games[0]["GameID"]
            genre_id = genres[0]["GenreID"]
            review_id = reviews[0]["ReviewID"]

            self.assertEqual(get(f"/games/{game_id}")["GameID"], game_id)
            self.assertEqual(get(f"/games/{game_id}/summary")["GameID"], game_id)
            for path in (f"/games?developer_id={developer_id}",
                         f"/game-platforms?game_id={game_id}",
                         f"/genres?game_id={game_id}",
                         f"/reviews?game_id={game_id}&sentiment=50",
                         "/procedures/developers", "/procedures/platforms",
                         "/procedures/games", "/procedures/games/search?search_term=game",
                         "/procedures/games/top/free", "/procedures/games/top/paid",
                         f"/procedures/games/{game_id}/reviews"):
                self.assertIsInstance(get(path), list)
            for path, key, value in (
                (f"/procedures/developers/{developer_id}", "DeveloperID", developer_id),
                (f"/procedures/platforms/{platform_id}", "PlatformID", platform_id),
                (f"/procedures/genres/{genre_id}", "GenreID", genre_id),
                (f"/procedures/games/{game_id}", "GameID", game_id),
                (f"/procedures/reviews/{review_id}", "ReviewID", review_id),
            ):
                self.assertEqual(get(path)[key], value)


if __name__ == "__main__":
    unittest.main()
