from pyspark.sql.types import FloatType
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
import redis
import pickle
from dotenv import load_dotenv
import os
from pyspark.sql.functions import col

load_dotenv()

spark = SparkSession.builder.appName("ALS-MovieLens-Demo").getOrCreate()

DATASET = os.getenv("DATASET", "small")  # "small" or "normal"

if DATASET == "small":
    data_path = "/spark/data/ml-latest-small/"
else:
    data_path = "/spark/data/ml-latest/"


# Load MovieLens small ratings dataset
ratings = spark.read.csv(
    f"{data_path}ratings.csv",
    header=True,
    inferSchema=True
)

links = spark.read.csv(
    f"{data_path}links.csv",
    header=True,
    inferSchema=False  # read everything as string
)

# Join ratings with links to get tmdbId as string
ratings_tmdb = ratings.join(links, on="movieId", how="inner") \
                      .select("userId", "tmdbId", "rating")

# Filter out nulls or empty strings
ratings_tmdb = ratings_tmdb.filter(
    (col("tmdbId").isNotNull()) & (col("tmdbId") != ""))

# Optionally, cast to float if ALS requires numeric IDs
ratings_tmdb = ratings_tmdb.withColumn(
    "tmdbId", col("tmdbId").cast(FloatType()))

# Train ALS using tmdbId as itemCol
als = ALS(
    userCol="userId",
    itemCol="tmdbId",   # <-- now ALS uses TMDb IDs
    ratingCol="rating",
    rank=10,
    maxIter=5,
    regParam=0.1,
    coldStartStrategy="drop"
)
model = als.fit(ratings_tmdb)

# Save model factors to Redis for fast access
# load from env variables in docker-compose
HOST = os.getenv("REDIS_HOST", "tmdb-redis")
PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=HOST, port=PORT, db=0)
user_factors = model.userFactors.collect()
item_factors = model.itemFactors.collect()
r.set("user_factors", pickle.dumps(user_factors))
r.set("item_factors", pickle.dumps(item_factors))

print("ALS model trained and saved to Redis successfully")
spark.stop()
