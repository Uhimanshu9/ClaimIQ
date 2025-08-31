from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from .utils.file import save_to_disk
from .db.collections.files import files_collection, FileSchema
from .queue.create_queue import q
from .queue.worker import process_file
# from .utils.chat_gemini import chat_with_gemini
from fastapi import HTTPException
from .queue.vectorStore import retrieve

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    collection_name: str = "pdf_collection"


@app.get("/")
def read_root():
    return {"Hello": "World!"}


@app.post("/upload")
async def update_file(file: UploadFile):
    # id = uuid4()
    db_file = await files_collection.insert_one(
        document=FileSchema(
            name=file.filename,
            status="pending"
        )
    )
    filepath = f"/mnt/uploads/{str(db_file.inserted_id)}/{file.filename}"
    #
    await save_to_disk(file=await file.read(), path=filepath)
    # push to queue
    q.enqueue(process_file, str(db_file.inserted_id), filepath)
    # mongo save
    await files_collection.update_one({"_id": db_file.inserted_id}, {
        "$set": {
            "status": "queued",
        }
    })
    # await queue.push(id, filepath)
    return {"file_id": str(db_file.inserted_id)}


@app.post("/query")
async def query_pdf(request: QueryRequest):
    try:
        response = retrieve(
            user_query=request.query,
            # collection_name=request.collection_name
        )
        return {"status": "success", "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
