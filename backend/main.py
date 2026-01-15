from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
import requests
from dotenv import load_dotenv

app = FastAPI(
    title="TMDb Ratings Demo",
    description="Fetch TMDb user ratings safely via backend for ALS recommendations.",
    version="1.0.0",
)
# Load TMDb API key from environment variables
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5500",
                   "http://127.0.0.1", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/request-token")
def request_token():
    """
    Requests a new TMDb request token from TMDb API.
    Returns the token to the frontend.
    """
    url = "https://api.themoviedb.org/3/authentication/token/new"
    params = {"api_key": TMDB_API_KEY}
    response = requests.get(url, params=params).json()
    return {"request_token": response["request_token"]}


@app.get("/api/get-ratings")
def tmdb_callback(request: Request, request_token: str):
    """
    TMDb redirects here after the user approves the request token.
    This endpoint exchanges the request token for a session ID,
    then fetches the user’s rated movies.
    """
    # Step 1: Create session ID using the request token
    session_url = "https://api.themoviedb.org/3/authentication/session/new"
    session_resp = requests.post(
        session_url,
        params={"api_key": TMDB_API_KEY},
        json={"request_token": request_token}
    ).json()

    if "session_id" not in session_resp:
        return JSONResponse(content={"error": "Failed to create session"}, status_code=400)

    session_id = session_resp["session_id"]

    # Step 2: Get account details to fetch account ID
    account_url = "https://api.themoviedb.org/3/account"
    account_resp = requests.get(
        account_url,
        params={"api_key": TMDB_API_KEY, "session_id": session_id}
    ).json()
    account_id = account_resp.get("id")

    if not account_id:
        return JSONResponse(content={"error": "Failed to get account ID"}, status_code=400)

    # Step 3: Get user rated movies
    rated_url = f"https://api.themoviedb.org/3/account/{account_id}/rated/movies"
    rated_resp = requests.get(
        rated_url,
        params={"api_key": TMDB_API_KEY, "session_id": session_id}
    ).json()

    rated_movies = rated_resp.get("results", [])

    # Step 4: Map to tmdbId + rating
    data = [{"tmdbId": m["id"], "rating": m["rating"]} for m in rated_movies]

    # For demo purposes, return JSON to frontend
    return {"rated_movies": data}

@app.get("/api/demo-movies")
def demo_movies():
    return {
        "movies": [
            {
                "tmdbId": 550,
                "title": "Fight Club",
                "rating": 4.7,
                "poster_path": "/a26cQPRhJPX6GbWfQbvZdrrp9j9.jpg"
            },
            {
                "tmdbId": 857,
                "title": "Saving Private Ryan",
                "rating": 4.8,
                "poster_path": "/uqx37cS8cpHg8U35f9U5IBlrCV3.jpg"
            },
            {
                "tmdbId": 8741,
                "title": "Paths of Glory",
                "rating": 4.6,
                "poster_path": "/seMydAaoxQP6F0xbE1jOcTmn5Jr.jpg"
            },
            {
                "tmdbId": 28,
                "title": "Apocalypse Now",
                "rating": 4.9,
                "poster_path": "/gQB8Y5RCMkv2zwzFHbUJX3kAhvA.jpg"
            }
        ]
    }