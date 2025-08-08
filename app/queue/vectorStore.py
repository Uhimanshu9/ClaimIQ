from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_core.documents import Document
import re
from typing import List, Optional


def auto_tag_clause(text: str) -> List[str]:
    tags = []
    if re.search(r'waiting period|after \d+ (days|months)', text, re.I):
        tags.append("waiting_period")
    if re.search(r'shall not cover|excluded|not payable', text, re.I):
        tags.append("exclusion")
    if re.search(r'covered under|is payable|insured is entitled', text, re.I):
        tags.append("coverage")
    if re.search(r'eligible if|required to|must be', text, re.I):
        tags.append("eligibility")
    if re.search(r'pre-existing|diagnosed before', text, re.I):
        tags.append("pre_existing_condition")
    if re.search(r'maximum benefit|limit.*policy', text, re.I):
        tags.append("benefit_limit")
    return tags or ["unknown"]


def create_vector_store(file_path: str, collection_name: str = "pdf_collection", qdrant_url: str = "http://qdrant:6333"):
    try:
        print(f"[INFO] Starting vector store creation for file: {file_path}")

        loader = PyPDFLoader(file_path)
        documents = loader.load()
        print(f"[INFO] Loaded {len(documents)} documents from {file_path}")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=10000, chunk_overlap=200)
        split_docs = text_splitter.split_documents(documents)
        print(f"[INFO] Split documents into {len(split_docs)} chunks")

        for doc in split_docs:
            tags = auto_tag_clause(doc.page_content)
            doc.metadata['tags'] = tags

        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
        print(
            "[INFO] Initialized HuggingFace embeddings with model BAAI/bge-base-en-v1.5")

        vector_store = QdrantVectorStore.from_documents(
            split_docs,
            embeddings,
            collection_name=collection_name,
            url=qdrant_url,
        )
        print(
            f"[INFO] Vector store created with {len(split_docs)} chunks in collection '{collection_name}' at '{qdrant_url}'")

    except Exception as e:
        print(f"[ERROR] Failed to create vector store: {e}")
        raise e


def get_vector_store(query: str, collection_name: str = "pdf_collection", qdrant_url: str = "http://qdrant:6333", required_tags: Optional[List[str]] = None):
    try:
        print(
            f"[INFO] Starting similarity search for query: '{query}' in collection '{collection_name}'")

        retriever = QdrantVectorStore.from_existing_collection(
            collection_name=collection_name,
            embedding=HuggingFaceEmbeddings(
                model_name="BAAI/bge-base-en-v1.5"),
            url=qdrant_url,
        )
        print(f"[INFO] Connected to existing collection '{collection_name}'")

        if required_tags:
            print(f"[INFO] Filtering search results by tags: {required_tags}")

            results = retriever.similarity_search_with_score(query, k=20)
            filtered_results = [doc for doc, score in results if any(
                tag in doc.metadata.get("tags", []) for tag in required_tags)]
            print(
                f"[INFO] Retrieved {len(filtered_results)} filtered results for query '{query}'")
            return filtered_results
        else:
            results = retriever.similarity_search(query)
            print(
                f"[INFO] Retrieved {len(results)} results for query '{query}'")
            return results

    except Exception as e:
        print(f"[ERROR] Similarity search failed: {e}")
        raise e
