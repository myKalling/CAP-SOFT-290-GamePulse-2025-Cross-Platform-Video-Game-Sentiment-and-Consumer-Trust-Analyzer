class Developer (
    DevID: int
    Developer: string

)

class Platform (
    PlatformID: int
    Platform: string
)

class Game (
    GameID: int
    Title: string
    DevID: int
)

class Review (
    ReviewID: int
    GamePlatformsID: int
    Review: string
    Sentiment: string
)

class GamePlatforms (
    GamePlatformsID: int
    GameID: int
    PlatformID: int
    ReleaseDate: date
    Price: decimal
)