from datetime import date
from decimal import Decimal
from pydantic import BaseModel

class Developer(BaseModel):
    DevID: int
    Developer: str


class Platform(BaseModel):
    PlatformID: int
    Platform: str


class Game(BaseModel):
    GameID: int
    Title: str
    DevID: int


class Review(BaseModel):
    ReviewID: int
    GamePlatformsID: int
    Review: str
    Sentiment: int


class GamePlatforms(BaseModel):
    GamePlatformsID: int
    GameID: int
    PlatformID: int
    ReleaseDate: date
    Price: Decimal