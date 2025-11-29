import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    print(f"Connecting to {mongo_url}")
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    try:
        # Try a simple operation
        print("Listing collections...")
        collections = await db.list_collection_names()
        print("Collections:", collections)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
