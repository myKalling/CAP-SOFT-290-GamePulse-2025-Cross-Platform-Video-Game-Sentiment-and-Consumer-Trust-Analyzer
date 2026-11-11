from datetime import date

from pydantic import BaseModel, ConfigDict


class SentimentRequest(BaseModel):
    text: str


class SentimentResult(BaseModel):
    score_100: float
    positive_share: float
    negative_share: float
    mixed: bool
    rating: int
    category: str


class GameReviewSummary(BaseModel):
    GameID: int
    Title: str
    ReviewCount: int
    AverageSentiment: float | None
    PositiveReviews: int
    NegativeReviews: int
    NeutralReviews: int


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
    Price: float | None


class GamePlatform(APIModel):
    GamePlatformsID: int
    GameID: int
    Title: str
    Price: float | None
    PlatformID: int
    PlatformName: str


class Review(APIModel):
    ReviewID: int
    GameID: int
    Title: str
    Review: str | None
    Sentiment: float
    ReviewDate: date | None
    UserID: int | None


class GameGenre(APIModel):
    GameID: int
    GenreID: int
    Genre: str
