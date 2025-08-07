from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from .utils.file import save_to_disk
from .db.collections.files import files_collection, FileSchema
from .queue.create_queue import q
from .queue.worker import process_file
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
        results = get_vector_store(query=request.query, collection_name=request.collection_name)
        return {
            "query": request.query,
            "results": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                } for doc in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

