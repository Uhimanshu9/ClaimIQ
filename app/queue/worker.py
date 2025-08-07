from ..db.collections.files import files_collection
from bson import ObjectId
from .vectorStore import create_vector_store
import asyncio


async def process_file(id: str, file_path: str):
    try:
        # Update status to processing
        await files_collection.update_one({"_id": ObjectId(id)}, {
            "$set": {"status": "processing"}
        })

        # Update status to indicate storing chunks
        await files_collection.update_one({"_id": ObjectId(id)}, {
            "$set": {"status": "storing chunks in qdrant db"}
        })

        # Run the synchronous create_vector_store function in a thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_vector_store, file_path)

        # Update status to chunking done
        await files_collection.update_one({"_id": ObjectId(id)}, {
            "$set": {"status": "chunking is done"}
        })

    except Exception as e:
        # Update status with error information
        await files_collection.update_one({"_id": ObjectId(id)}, {
            "$set": {"status": f"error: {str(e)}"}
        })
        # Optionally, you could log the error or re-raise


# If you want an entry point to test this async function standalone:
# import asyncio
# asyncio.run(process_file("some_file_id_here", "/path/to/file.pdf"))



# rq worker --with-scheduler --url redis://valkey:6379