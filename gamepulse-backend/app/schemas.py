from datetime import date
from decimal import Decimal


class Developer:
    DevID: int
    Developer: str


class Platform:
    PlatformID: int
    Platform: str


class Game:
    GameID: int
    Title: str
    DevID: int


class Review:
    ReviewID: int
    GamePlatformsID: int
    Review: str
    Sentiment: int


class GamePlatforms:
    GamePlatformsID: int
    GameID: int
    PlatformID: int
    ReleaseDate: date
    Price: Decimal


class Genre:
    GenreID: int
    Genre: str


class GameGenres:
    GameID: int
    GenreID: int