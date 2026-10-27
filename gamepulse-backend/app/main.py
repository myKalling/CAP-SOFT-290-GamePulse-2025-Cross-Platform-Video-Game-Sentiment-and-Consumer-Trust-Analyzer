from fastapi import FastAPI
from schemas import Game, Developer, Platform, Review, GamePlatforms

app = FastAPI()
# to start the api put this is terminal: uvicorn main:app --reload

@app.get("/")
def read_root():
    return {"status": "GamePulse API is running"}
