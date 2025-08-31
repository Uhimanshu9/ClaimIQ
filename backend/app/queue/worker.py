from ..db.collections.files import files_collection
from bson import ObjectId
from .vectorStore import put_pdf
import asyncio


async def process_file(id: str, file_path: str):
    try:
        # Step 1: mark processing
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "processing"}}
        )

        # Step 2: run put_pdf in background thread
        result = await asyncio.to_thread(put_pdf, file_path)

        # Step 3: mark success
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "status": "ready",
                "qdrant_message": result.get("message", ""),
                "file_path": result.get("file_path", file_path)
            }}
        )
        return {"status": "ready", "file_id": str(id)}

    except Exception as e:
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "error", "error_message": str(e)}}
        )
        print(f"Error processing file {id}: {str(e)}")
        return {"status": "error", "file_id": str(id), "error": str(e)}
