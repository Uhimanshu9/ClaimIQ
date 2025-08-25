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
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, put_pdf, file_path)

        # Step 3: mark success
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "status": "ready",
                "qdrant_message": result["message"],  # store log info from put_pdf
                "file_path": result["file_path"]
            }}
        )
    except Exception as e:
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": f"error: {str(e)}"}}
        )
        print(f"Error processing file {id}: {str(e)}")  

    return {"status": "done"}