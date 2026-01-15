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


def get_movie_info(id) -> str:
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
        info = response.json()
        return {"poster_path": info.get("poster_path"), "vote_average": info.get("vote_average"), "vote_count": info.get("vote_count"), "title": info.get("title")}
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
def tmdb_callback(request: Request, request_token: str = None, user_id: str = None, top_n: int = 10):
    """
    TMDb redirects here after the user approves the request token.
    Exchanges request token for session ID (if needed), then fetches user's rated movies.
    """
    if not user_id:
        return JSONResponse({"error": "Missing user_id"}, status_code=400)

    # Step 0: Try to reuse existing session_id
    session_id = r.get(f"user_session:{user_id}")
    if session_id:
        session_id = session_id.decode("utf-8")
    else:
        # Step 1: Exchange request token for session_id
        if not request_token:
            return JSONResponse({"error": "Missing request_token for first-time login"}, status_code=400)

        session_url = "https://api.themoviedb.org/3/authentication/session/new"
        session_resp = requests.post(
            session_url,
            params={"api_key": TMDB_API_KEY},
            json={"request_token": request_token}
        ).json()

        session_id = session_resp.get("session_id")
        if not session_id:
            return JSONResponse({"error": "Failed to create session. Token may be expired."}, status_code=400)

        # Save session_id for future use
        r.set(f"user_session:{user_id}", session_id)

    # Step 2: Get account ID
    account_url = "https://api.themoviedb.org/3/account"
    account_resp = requests.get(
        account_url,
        params={"api_key": TMDB_API_KEY, "session_id": session_id}
    ).json()
    account_id = account_resp.get("id")
    if not account_id:
        return JSONResponse({"error": "Failed to get account ID. Session may be invalid."}, status_code=400)

    # Step 3: Get user rated movies
    rated_url = f"https://api.themoviedb.org/3/account/{account_id}/rated/movies"
    rated_resp = requests.get(
        rated_url,
        params={"api_key": TMDB_API_KEY, "session_id": session_id}
    ).json()

    rated_movies = rated_resp.get("results", [])

    # Step 4: Map to tmdbId + rating (existing logic)
    try:
        liked_pairs = [(str(m["id"]), str(m["rating"])) for m in rated_movies]
        liked_movies = [(int(mid), float(rating))
                        for mid, rating in liked_pairs]
    except Exception:
        return {"error": "Something went wrong parsing ratings"}

    # Step 5: Filter only movies present in Redis
    filtered_liked = []
    unused_liked = []
    for mid, rating in liked_movies:
        movie_instance = r.get(f"movie:{mid}")
        if movie_instance:
            filtered_liked.append((mid, rating))
        else:
            unused_liked.append((mid, rating))
            print(f"Skipping TMDb ID {mid} – not found in Redis")

    liked_movies = filtered_liked

    for mid, rating in liked_movies:
        movie_instance = r.get(f"movie:{mid}")
        meta = json.loads(movie_instance)
        print(
            f"User liked movie TMDb ID {mid} ({meta['title']}) with rating {rating}")

    # Step 6: Compute user vector & score items (existing ALS logic)
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

    user_vector = [sum(v*w for v, w in zip(vals, weights))/sum(weights)
                   for vals in zip(*liked_vectors)]

    scored_items = [(item.id, sum(
        a*b for a, b in zip(user_vector, item.features))) for item in item_factors]
    scored_items.sort(key=lambda x: -x[1])

    # Step 7: Enrich with metadata from Redis (existing logic)
    enriched = []
    for movie_id, score in scored_items[:top_n]:
        data = r.get(f"movie:{movie_id}")
        if data:
            meta = json.loads(data)
            meta["score"] = score
            meta["url"] = f"https://www.themoviedb.org/movie/{meta['tmdbId']}"
            if not meta.get("poster_path"):
                info = get_movie_info(movie_id)
                if info and info.get("poster_path"):
                    meta["poster_path"] = info["poster_path"]
                    meta["vote_average"] = info.get("vote_average")
                    meta["vote_count"] = info.get("vote_count")
                    r.set(f"movie:{movie_id}", json.dumps(meta))
                else:
                    print("No poster found")
                    continue

            enriched.append(meta)

    enriched_liked = []
    for lm in liked_movies:
        data = r.get(f"movie:{lm[0]}")
        if data:
            meta = json.loads(data)
            meta["user_rating"] = lm[1]
            meta["url"] = f"https://www.themoviedb.org/movie/{meta['tmdbId']}"
            if not meta.get("poster_path"):
                info = get_movie_info(lm[0])
                if info and info.get("poster_path"):
                    meta["poster_path"] = info["poster_path"]
                    meta["vote_average"] = info.get("vote_average")
                    meta["vote_count"] = info.get("vote_count")
                    r.set(f"movie:{lm[0]}", json.dumps(meta))
                else:
                    print("No poster found for liked movie")
                    continue
        enriched_liked.append(meta)

    enriched_unused_liked = []
    for lm in unused_liked:
        meta = {}
        meta["url"] = f"https://www.themoviedb.org/movie/{lm[0]}"
        info = get_movie_info(lm[0])
        if info and info.get("poster_path"):
            meta["poster_path"] = info["poster_path"]
            meta["vote_average"] = info.get("vote_average")
            meta["title"] = info.get("title")
            meta["vote_count"] = info.get("vote_count")
            meta["user_rating"] = lm[1]
        enriched_unused_liked.append(meta)

    # Sanitize floats and return
    return {"recommendations": [sanitize_floats(m) for m in enriched], "used_movies":  [sanitize_floats(m) for m in enriched_liked], "unused_movies": [sanitize_floats(m) for m in enriched_unused_liked]}
