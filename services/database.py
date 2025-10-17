from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# Get MongoDB connection string from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
DB_NAME = "msl"
MONGO_URI = os.getenv("MONGO_URI", DATABASE_URL)
client = AsyncIOMotorClient(MONGO_URI)

print(client.list_database_names())
db = client[DB_NAME]


users_collection = db.users
sessions_collection = db.user_sessions
personas_collections = db.personas
questions_collections = db.questions
category_collections = db.categories
user_progress_collections = db.user_progress
