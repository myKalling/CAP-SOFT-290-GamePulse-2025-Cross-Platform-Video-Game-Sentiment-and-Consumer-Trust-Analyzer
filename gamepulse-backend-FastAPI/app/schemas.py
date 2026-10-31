from datetime import date

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Developer(APIModel):
    DeveloperID: int
    DeveloperName: str


class Platform(APIModel):
    PlatformID: int
    PlatformName: str


class Game(APIModel):
    GameID: int
    Title: str
    DeveloperID: int
    DeveloperName: str


class GamePlatform(APIModel):
    GamePlatformsID: int
    GameID: int
    PlatformID: int
    PlatformName: str
    ReleaseDate: date
    Price: float


class Review(APIModel):
    ReviewID: int
    GamePlatformsID: int
    Review: str
    Sentiment: int


class GameGenre(APIModel):
    GameID: int
    GenreID: int
    Genre: str
