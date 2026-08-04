from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Literal
from datetime import datetime, timezone
import asyncio
from .utils.file import save_to_disk
from .db.collections.files import files_collection, FileSchema
from .db.collections.chat_history import chat_history_collection
from .queue.create_queue import q
from .queue.worker import process_file
# from .utils.chat_gemini import chat_with_gemini
from fastapi import HTTPException
from .queue.vectorStore import delete_document_vectors, retrieve
from .llm.router import ProviderConfigurationError, supported_providers
from bson import ObjectId
from rq.job import Job
from rq.command import send_stop_job_command

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    collection_name: str = "pdf_collection"
    provider: Literal["gemini", "openai"] = "gemini"
    model: str | None = Field(default=None, max_length=128)


class BedrockQueryRequest(BaseModel):
    query: str
    model: str | None = Field(default=None, max_length=128)


class ChatMessage(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)
    thinking: str | None = Field(default=None, max_length=20000)
    isError: bool | None = None


class ChatHistoryUpsertRequest(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=200)
    document_name: str = Field(min_length=1, max_length=500)
    file_id: str | None = Field(default=None, max_length=128)
    provider: Literal["gemini", "openai"] = "gemini"
    messages: list[ChatMessage] = Field(min_length=1, max_length=500)


def serialize_chat_history(chat: dict[str, Any]) -> dict[str, Any]:
    """Return Mongo documents in the camelCase shape the React client uses."""
    return {
        "id": chat["conversation_id"],
        "title": chat["title"],
        "documentName": chat["document_name"],
        "fileId": chat.get("file_id"),
        "provider": chat.get("provider", "gemini"),
        "messages": chat.get("messages", []),
        "updatedAt": chat["updated_at"].isoformat(),
    }


@app.get("/")
def read_root():
    return {"Hello": "World!"}


@app.post("/upload")
async def update_file(file: UploadFile):
    # id = uuid4()
    db_file = await files_collection.insert_one(
        document=FileSchema(
            name=file.filename,
            status="pending",
            progress=0,
            stage="uploading",
        )
    )
    filepath = f"/mnt/uploads/{str(db_file.inserted_id)}/{file.filename}"
    #
    await save_to_disk(file=await file.read(), path=filepath)
    # push to queue
    job = q.enqueue(process_file, str(db_file.inserted_id), filepath)
    # mongo save
    await files_collection.update_one({"_id": db_file.inserted_id}, {
        "$set": {
            "status": "queued",
            "progress": 5,
            "stage": "queued",
            "job_id": job.id,
        }
    })
    # await queue.push(id, filepath)
    return {"file_id": str(db_file.inserted_id), "job_id": job.id}


@app.get("/files/{file_id}/status")
async def get_file_status(file_id: str):
    """Return safe indexing progress for an uploaded file."""
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    file_record = await files_collection.find_one({"_id": ObjectId(file_id)})
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": str(file_record["_id"]),
        "status": file_record.get("status", "pending"),
        "progress": file_record.get("progress", 0),
        "stage": file_record.get("stage", "queued"),
        "error": file_record.get("error_message"),
    }


@app.post("/files/{file_id}/cancel")
async def cancel_file_processing(file_id: str):
    """Cancel a queued or active indexing job for an uploaded document."""
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    file_record = await files_collection.find_one({"_id": ObjectId(file_id)})
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    if file_record.get("status") in {"ready", "cancelled"}:
        raise HTTPException(status_code=409, detail="This document cannot be cancelled.")

    job_id = file_record.get("job_id")
    if job_id:
        try:
            job = Job.fetch(job_id, connection=q.connection)
            if job.get_status() in {"queued", "deferred", "scheduled"}:
                job.cancel()
            else:
                send_stop_job_command(q.connection, job_id)
        except Exception:
            # The job may already have finished or been removed; the status below
            # still prevents it from being used as part of the knowledge base.
            pass

    await asyncio.to_thread(delete_document_vectors, file_id)

    await files_collection.update_one(
        {"_id": ObjectId(file_id)},
        {"$set": {"status": "cancelled", "progress": 0, "stage": "cancelled"}},
    )
    return {"file_id": file_id, "status": "cancelled"}


@app.get("/documents")
async def list_documents():
    """List documents available to the shared application knowledge base."""
    documents = []
    cursor = files_collection.find({}).sort("_id", -1)
    async for file_record in cursor:
        # Legacy records have no RQ job id. A pending status after a restart is
        # not trustworthy, so keep the document out of the knowledge base.
        if file_record.get("status") in {"pending", "queued", "processing"} and not file_record.get("job_id"):
            await files_collection.update_one(
                {"_id": file_record["_id"]},
                {"$set": {
                    "status": "interrupted",
                    "progress": 0,
                    "stage": "worker stopped before indexing completed",
                }},
            )
            file_record["status"] = "interrupted"
            file_record["progress"] = 0
            file_record["stage"] = "worker stopped before indexing completed"
        documents.append({
            "file_id": str(file_record["_id"]),
            "name": file_record.get("name", "Untitled document"),
            "status": file_record.get("status", "pending"),
            "progress": file_record.get("progress", 0),
            "stage": file_record.get("stage", "queued"),
        })
    return {"documents": documents}


@app.get("/chat-history")
async def list_chat_history():
    """Return completed conversations, newest first, from MongoDB."""
    conversations = []
    cursor = chat_history_collection.find({"messages.0": {"$exists": True}}).sort("updated_at", -1)
    async for conversation in cursor:
        conversations.append(serialize_chat_history(conversation))
    return {"conversations": conversations}


@app.put("/chat-history/{conversation_id}")
async def save_chat_history(conversation_id: str, request: ChatHistoryUpsertRequest):
    """Create or update one non-empty conversation in the chat_history collection."""
    if conversation_id != request.id:
        raise HTTPException(status_code=400, detail="Conversation id does not match the request body.")

    now = datetime.now(timezone.utc)
    record = {
        "conversation_id": request.id,
        "title": request.title,
        "document_name": request.document_name,
        "file_id": request.file_id,
        "provider": request.provider,
        "messages": [message.model_dump(exclude_none=True) for message in request.messages],
        "updated_at": now,
    }
    await chat_history_collection.update_one(
        {"conversation_id": request.id},
        {"$set": record, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    saved = await chat_history_collection.find_one({"conversation_id": request.id})
    return {"conversation": serialize_chat_history(saved)}


@app.post("/query")
async def query_pdf(request: QueryRequest):
    try:
        response = retrieve(
            user_query=request.query,
            provider=request.provider,
            model=request.model,
        )
        return {"status": "success", "data": response}
    except (ProviderConfigurationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/bedrock/query")
async def query_with_bedrock(request: BedrockQueryRequest):
    """Answer a document query with the configured Amazon Bedrock model."""
    try:
        response = retrieve(user_query=request.query, provider="bedrock", model=request.model)
        return {"status": "success", "data": response}
    except (ProviderConfigurationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bedrock query failed: {str(e)}")


@app.get("/providers")
def get_providers():
    """Return the providers that clients may select for generated answers."""
    return {"providers": supported_providers()}
