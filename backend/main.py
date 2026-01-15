import math
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse
import requests
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import redis
import pickle
from typing import List
import json
import requests

app = FastAPI(
    title="TMDb Ratings Demo",
    description="Fetch TMDb user ratings safely via backend for ALS recommendations.",
    version="1.0.0",
)
# Load TMDb API key from environment variables
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5500",
                   "http://127.0.0.1", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


r = redis.Redis(host="tmdb-redis", port=6379, db=0)
# Load item factors once at startup
item_factors = pickle.loads(r.get("item_factors"))


def sanitize_floats(d):
    return {k: (v if not isinstance(v, float) or math.isfinite(v) else 0.0) for k, v in d.items()}


def get_poster_url(id) -> str:
    print(f"Fetching poster for TMDb ID {id}")
    url = f"https://api.themoviedb.org/3/movie/{id}?language=en-US"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None

    try:
        return response.json()['poster_path']
    except Exception:
        return None


@app.get("/")
def index():
    return FileResponse("static/index.html")


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


@app.get("/api/get-recommendations")
def tmdb_callback(request: Request, request_token: str, top_n: int = 10):
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

    try:
        liked_pairs = [(str(m["tmdbId"]), str(m["rating"])) for m in data]
        liked_movies = [(int(mid), float(rating))
                        for mid, rating in liked_pairs]
    except Exception:
        return {"error": "Something went wrong parsing ratings"}

    filtered_liked = []
    for mid, rating in liked_movies:
        movie_instance = r.get(f"movie:{mid}")
        if movie_instance:
            filtered_liked.append((mid, rating))
        else:
            print(f"Skipping TMDb ID {mid} – not found in Redis")

    liked_movies = filtered_liked
    for mid, rating in liked_movies:
        movie_instance = r.get(f"movie:{mid}")
        meta = json.loads(movie_instance)
        print(
            f"User liked movie TMDb ID {mid} ({meta['title']}) with rating {rating}")

    # Get vectors of liked movies
    liked_vectors = []
    weights = []
    for mid, rating in liked_movies:
        vec = next(
            (item.features for item in item_factors if item.id == mid), None)
        if vec:
            liked_vectors.append(vec)
            weights.append(rating)

    if not liked_vectors:
        return {"error": "No valid liked movies found"}

    # Weighted average to compute synthetic user vector
    user_vector = [sum(v*w for v, w in zip(vals, weights))/sum(weights)
                   for vals in zip(*liked_vectors)]

    # Score all items
    scored_items = [(item.id, sum(
        a*b for a, b in zip(user_vector, item.features))) for item in item_factors]
    scored_items.sort(key=lambda x: -x[1])

    # Fetch metadata from Redis
    enriched = []
    for movie_id, score in scored_items[:top_n]:
        data = r.get(f"movie:{movie_id}")
        if data:
            meta = json.loads(data)
            meta["score"] = score  # add ALS score
            meta["url"] = f"https://www.themoviedb.org/movie/{meta['tmdbId']}"
            if not meta.get("poster_path"):
                # if meta.get("poster_path") is None:
                poster = get_poster_url(movie_id)
                if poster is None:
                    print("No poster found")
                    continue
                else:
                    meta["poster_path"] = poster
                    r.set(f"movie:{movie_id}", json.dumps(meta))
            enriched.append(meta)

    return {"recommendations": [sanitize_floats(m) for m in enriched]}
