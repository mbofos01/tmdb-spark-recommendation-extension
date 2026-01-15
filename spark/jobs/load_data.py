import pandas as pd
import redis
import json
import os
from dotenv import load_dotenv

HOST = os.getenv("REDIS_HOST", "tmdb-redis")
PORT = int(os.getenv("REDIS_PORT", 6379))
# Connect to Redis
r = redis.Redis(host=HOST, port=PORT, db=0)

DATASET = os.getenv("DATASET", "small")  # "small" or "normal"

if DATASET == "small":
    data_path = "/spark/data/ml-latest-small/"
else:
    data_path = "/spark/data/ml-latest/"

# Load MovieLens data
# movieId, title, genres
movies_df = pd.read_csv(f"{data_path}movies.csv")
# movieId, imdbId, tmdbId
links_df = pd.read_csv(f"{data_path}links.csv")
# optional: movieId, tag, userId
tags_df = pd.read_csv(f"{data_path}tags.csv")
# ratings
ratings_df = pd.read_csv(f"{data_path}ratings.csv")
avg_ratings = ratings_df.groupby("movieId")["rating"].mean().reset_index()
avg_ratings.columns = ["movieId", "avg_rating"]

# Merge movies and links
movies = movies_df.merge(links_df, on="movieId", how="left")
movies = movies.merge(avg_ratings, on="movieId", how="left")

# Optional: aggregate tags
if not tags_df.empty:
    tags_agg = tags_df.groupby("movieId")["tag"].apply(list).reset_index()
    movies = movies.merge(tags_agg, on="movieId", how="left")
else:
    movies["tag"] = None

# Load into Redis
for _, row in movies.iterrows():
    try:
        movie_key = f"movie:{int(row['tmdbId'])}"
        data = {
            "db_movieId": int(row["movieId"]),
            "title": row["title"],
            "genres": row["genres"],
            "imdbId": str(row["imdbId"]) if not pd.isna(row["imdbId"]) else None,
            "tmdbId": str(row["tmdbId"]) if not pd.isna(row["tmdbId"]) else None,
            "tags": row["tag"] if row["tag"] is not None else [],
            "rating": round(float(row["avg_rating"]), 2) if not pd.isna(row["avg_rating"]) else 0.0
        }
        r.set(movie_key, json.dumps(data))
    except Exception:
        pass

print(f"{len(movies)} movies loaded into Redis.")
