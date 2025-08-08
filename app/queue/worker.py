from ..db.collections.files import files_collection
from bson import ObjectId
from .vectorStore import create_vector_store
# import asyncio
import asyncio


async def process_file(id: str, file_path: str):
    try:
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "processing"}}
        )
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "storing chunks in qdrant db"}}
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_vector_store, file_path)

        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "chunking is done"}}
        )
    except Exception as e:
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": f"error: {str(e)}"}}
        )


# rq worker --with-scheduler --url redis://valkey:6379
