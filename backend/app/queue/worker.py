from ..db.collections.files import files_collection
from bson import ObjectId
from .vectorStore import put_pdf
import asyncio


async def _process_file(id: str, file_path: str):
    try:
        # Step 1: mark processing
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "processing", "progress": 15, "stage": "extracting document text"}}
        )

        # Step 2: run put_pdf in background thread
        result = await asyncio.to_thread(put_pdf, file_path, id)

        # Step 3: mark success
        file_record = await files_collection.find_one({"_id": ObjectId(id)})
        if file_record and file_record.get("status") == "cancelled":
            return {"status": "cancelled", "file_id": str(id)}

        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "status": "ready",
                "progress": 100,
                "stage": "indexed",
                "qdrant_message": result.get("message", ""),
                "file_path": result.get("file_path", file_path)
            }}
        )
        return {"status": "ready", "file_id": str(id)}

    except Exception as e:
        await files_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "error", "stage": "failed", "error_message": str(e)}}
        )
        print(f"Error processing file {id}: {str(e)}")
        return {"status": "error", "file_id": str(id), "error": str(e)}


def process_file(id: str, file_path: str):
    """Synchronous RQ entrypoint for the asynchronous file-processing workflow."""
    return asyncio.run(_process_file(id, file_path))
