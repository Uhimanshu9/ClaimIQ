import os
import json
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from typing import List, Dict, Any

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_core.embeddings import Embeddings

from google import genai
from google.genai import types
from pathlib import Path



# ===== Load env =====
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "pdf_collection")

# ===== Init Gemini client =====
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ===== Embedding helpers =====
def get_gemini_embedding(text: str, dims: int = 768) -> List[float]:
    """
    Return embedding vector for given text.
    """
    response = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=dims),
    )
    # response.embeddings is expected; adjust if SDK differs
    return response.embeddings[0].values


class GeminiEmbeddings(Embeddings):
    def __init__(self, dims: int = 768):
        self.dims = dims

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [get_gemini_embedding(t, dims=self.dims) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return get_gemini_embedding(text, dims=self.dims)


# ===== 1) Query expansion with retries, returns list[str] =====
def create_queries(query: str, max_retries: int = 4, model: str = "gemini-2.5-flash") -> List[str]:
    prompt = f"""
Take the user query below and create 4 different queries:
- 2 less abstract / more specific versions (include context keywords)
- 2 more abstract / umbrella versions
Return ONLY a JSON array of strings, nothing else.
User query: {json.dumps(query)}
"""
    for attempt in range(1, max_retries + 1):
        resp = gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction="Output must be a JSON array of strings.")
        )
        raw = resp.text.strip() if hasattr(resp, "text") else ""
        # try to locate JSON substring if there's extra text
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            # try to extract first occurrence of '[' ... ']'
            try:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                candidate = raw[start:end]
                parsed = json.loads(candidate)
                if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                    return parsed
            except Exception:
                pass

        print(f"[query expansion] Attempt {attempt} failed to produce clean JSON. Retrying...")
        time.sleep(0.5 * attempt)

    print("[query expansion] falling back to original query")
    return [query]


# ===== 2) Create vector store from PDF (store metadata) =====
def create_vector_store(file_path: str, collection_name: str = COLLECTION_NAME):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} page-like documents from {file_path}")

    # Use structure-aware splitter but keep chunks reasonably sized
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    split_docs = text_splitter.split_documents(documents)
    print(f"Split into {len(split_docs)} chunks")

    # attach metadata: unique id, source filename, page number if available
    for d in split_docs:
        d.metadata = d.metadata or {}
        d.metadata["_chunk_id"] = str(uuid.uuid4())
        d.metadata["source_document"] = os.path.basename(file_path)

    embedding = GeminiEmbeddings(dims=768)
    vector_store = QdrantVectorStore.from_documents(
        split_docs,
        embedding=embedding,
        collection_name=collection_name,
        url=QDRANT_URL
    )
    print("Vector store created / updated in Qdrant.")


# ===== 3) Search vector store (reusable) =====
def search_vector_store(query: str, top_k: int = 3, collection_name: str = COLLECTION_NAME):
    embedding = GeminiEmbeddings(dims=768)
    retriever = QdrantVectorStore.from_existing_collection(
        collection_name=collection_name,
        embedding=embedding,
        url=QDRANT_URL
    )
    # LangChain retriever similarity_search takes string query and returns Document objects
    results = retriever.similarity_search(query, k=top_k)
    return results


# ===== 4) Merge unique chunks by text =====
def merge_unique_chunks(results_list: List[Any]) -> List[Any]:
    seen = set()
    unique = []
    for chunk in results_list:
        text = chunk.page_content.strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(chunk)
    return unique


# ===== 5) Rerank using Gemini (ask Gemini to output JSON scores) =====
def rerank_with_gemini(query: str, chunks: List[Any], max_retries: int = 3, model: str = "gemini-2.5-flash") -> List[Dict]:
    """
    Input: query and list of chunk objects (must have .page_content and .metadata['_chunk_id'])
    Output: list of dicts: [{chunk_id, score, page_content, metadata}, ...] sorted descending by score
    """
    # prepare small context sample to keep prompt size bounded:
    candidates = []
    for c in chunks:
        txt = c.page_content.strip()
        mid = c.metadata.get("_chunk_id", str(uuid.uuid4()))
        candidates.append({"id": mid, "text": txt[:2000], "meta": c.metadata})

    # build a prompt containing numbered chunks
    numbered_text = "\n\n".join([f"#{i+1} (id:{cand['id']}):\n{cand['text']}" for i, cand in enumerate(candidates)])
    prompt = f"""
You are a scoring assistant. Given the user query and a list of document chunks, return a JSON array of numbers (one per chunk in the same order)
where each number is the relevance score from 0 (not relevant) to 1 (highly relevant).

User query: {json.dumps(query)}

Chunks (in order):
{numbered_text}

Return ONLY a JSON array of floats like: [0.12, 0.9, ...] with exactly one float per chunk.
"""

    for attempt in range(1, max_retries + 1):
        resp = gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction="Output must be a JSON array of floats.")
        )
        raw = resp.text.strip() if hasattr(resp, "text") else ""
        try:
            scores = json.loads(raw)
            if isinstance(scores, list) and len(scores) == len(candidates):
                # build result list
                out = []
                for s, cand in zip(scores, candidates):
                    try:
                        score = float(s)
                    except Exception:
                        score = 0.0
                    out.append({
                        "chunk_id": cand["id"],
                        "score": score,
                        "page_content": cand["text"],
                        "metadata": cand["meta"]
                    })
                # sort by score descending
                out.sort(key=lambda x: x["score"], reverse=True)
                return out
        except json.JSONDecodeError:
            # attempt to extract JSON substring
            try:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                candidate = raw[start:end]
                scores = json.loads(candidate)
                if isinstance(scores, list) and len(scores) == len(candidates):
                    out = []
                    for s, cand in zip(scores, candidates):
                        try:
                            score = float(s)
                        except Exception:
                            score = 0.0
                        out.append({
                            "chunk_id": cand["id"],
                            "score": score,
                            "page_content": cand["text"],
                            "metadata": cand["meta"]
                        })
                    out.sort(key=lambda x: x["score"], reverse=True)
                    return out
            except Exception:
                pass

        print(f"[reranker] attempt {attempt} failed — retrying...")
        time.sleep(0.4 * attempt)

    # fallback: use chunk ordering from input with heuristic scores
    fallback = []
    for i, cand in enumerate(candidates):
        fallback.append({
            "chunk_id": cand["id"],
            "score": max(0.001, 1.0 - (i * 0.05)),
            "page_content": cand["text"],
            "metadata": cand["meta"]
        })
    fallback.sort(key=lambda x: x["score"], reverse=True)
    return fallback


# ===== 6) Generate final answer with Gemini LLM constrained to provided chunks =====
def generate_answer_with_gemini(query: str, top_chunks: List[Dict], model: str = "gemini-2.5-flash", max_retries: int = 3) -> Dict[str, Any]:
    """
    top_chunks: list of dicts produced by rerank_with_gemini (chunk_id, page_content, metadata)
    Returns a dict: {answer: str, explanation: str, evidence: [...]}
    """
    # build evidence block with metadata tags
    evidence_blocks = []
    for i, c in enumerate(top_chunks, 1):
        meta = c.get("metadata", {})
        src = meta.get("source_document", "unknown")
        section = meta.get("section_title", "")
        block = f"--- CHUNK {i} | id:{c['chunk_id']} | source:{src} | section:{section} ---\n{c['page_content']}"
        evidence_blocks.append(block)

    prompt = f"""
System: You are an answer engine that must ONLY use the provided document chunks to answer the user's question.
If the answer cannot be found in the provided chunks, reply exactly: "Not present in provided documents."

USER QUESTION:
{json.dumps(query)}

CONTEXT CHUNKS:
{'\n\n'.join(evidence_blocks)}

INSTRUCTIONS:
1) Provide a short concise answer (1-3 sentences).
2) Provide a short explanation referencing the chunks (quote or paraphrase and include chunk ids like CHUNK 1).
3) Provide an evidence list of the chunk ids you used.
4) Output a JSON object EXACTLY in this format:
{{"answer": "...", "explanation": "...", "evidence": ["CHUNK 1","CHUNK 3"]}}
Return ONLY this JSON object.
"""

    for attempt in range(1, max_retries + 1):
        resp = gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction="Output must be a single JSON object.")
        )
        raw = resp.text.strip() if hasattr(resp, "text") else ""
        try:
            parsed = json.loads(raw)
            return parsed
        except json.JSONDecodeError:
            # try to extract JSON substring
            try:
                start = raw.index("{")
                end = raw.rindex("}") + 1
                candidate = raw[start:end]
                parsed = json.loads(candidate)
                return parsed
            except Exception:
                pass
        print(f"[generator] attempt {attempt} failed — retrying...")
        time.sleep(0.5 * attempt)

    # fallback answer
    return {"answer": "Not present in provided documents.", "explanation": "", "evidence": []}


# ===== 7) Small example rules engine (age check) =====
def apply_rules_and_ml(extracted_attributes: Dict[str, Any], applicant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Very small deterministic rules example:
    - If policy has age_min/age_max and applicant age outside → ineligible
    """
    result = {"eligible": None, "reasons": [], "confidence": 1.0}
    age = applicant.get("age")
    if age is None:
        result["eligible"] = None
        result["reasons"].append("Applicant age not provided")
        result["confidence"] = 0.4
        return result

    age_min = extracted_attributes.get("age_min")
    age_max = extracted_attributes.get("age_max")
    if age_min is not None and age < age_min:
        result["eligible"] = False
        result["reasons"].append(f"Applicant age {age} < policy minimum {age_min}")
        return result
    if age_max is not None and age > age_max:
        result["eligible"] = False
        result["reasons"].append(f"Applicant age {age} > policy maximum {age_max}")
        return result

    result["eligible"] = True
    result["reasons"].append("Passed deterministic age checks")
    return result


# ===== 8) Small util to extract numeric constraints from chunks (very small heuristic) =====
import re
def extract_structured_params_from_chunks(chunks: List[Dict]) -> Dict[str, Any]:
    """
    Heuristic: look for patterns like 'age 18 to 65' or 'aged between 18 and 65' etc.
    Returns dict with keys like age_min, age_max
    """
    text = " ".join([c["page_content"] for c in chunks]).lower()
    # pattern examples: 'age 18 to 65', 'aged between 18 and 65', 'age limit is 65 years'
    m = re.search(r"age[s]?\s*(?:limit)?\s*(?:is|:|of|between)?\s*(\d{1,3})\s*(?:to|and|-)\s*(\d{1,3})", text)
    out = {}
    if m:
        try:
            out["age_min"] = int(m.group(1))
            out["age_max"] = int(m.group(2))
        except ValueError:
            pass
    # fallback single-sided
    m2 = re.search(r"max(?:imum)? age\s*(?:is|:)?\s*(\d{1,3})", text)
    if m2:
        out["age_max"] = int(m2.group(1))
    m3 = re.search(r"min(?:imum)? age\s*(?:is|:)?\s*(\d{1,3})", text)
    if m3:
        out["age_min"] = int(m3.group(1))
    return out


# ===== 9) Main RAG pipeline function (puts it all together) =====
def rag_pipeline(user_query: str, applicant_context: Dict[str, Any] = None, top_k_per_query: int = 3, top_k_final: int = 5):
    # 1. Expand queries
    expanded = create_queries(user_query)
    print("[pipeline] expanded queries:", expanded)

    # 2. Search in parallel across expanded queries
    all_hits = []
    with ThreadPoolExecutor(max_workers=min(6, len(expanded))) as ex:
        futures = [ex.submit(search_vector_store, q, top_k=top_k_per_query) for q in expanded]
        for f in futures:
            res = f.result()
            all_hits.extend(res)

    # 3. Merge unique
    unique_chunks = merge_unique_chunks(all_hits)
    print(f"[pipeline] unique chunks retrieved: {len(unique_chunks)}")

    if not unique_chunks:
        return {"answer": "Not present in provided documents.", "evidence": [], "decision": None}

    # 4. Rerank using Gemini
    reranked = rerank_with_gemini(user_query, unique_chunks)
    # choose top N for generation
    top_chunks = reranked[:top_k_final]

    # 5. Generate final answer with Gemini LLM
    llm_response = generate_answer_with_gemini(user_query, top_chunks)
    # assemble evidence details from top_chunks mapping to CHUNK ids used by LLM
    evidence_map = {}
    for i, c in enumerate(top_chunks, 1):
        evidence_map[f"CHUNK {i}"] = {"chunk_id": c["chunk_id"], "source": c["metadata"].get("source_document"), "text_preview": c["page_content"][:300]}

    # 6. Extract structured params and apply rules (example)
    extracted = extract_structured_params_from_chunks(top_chunks)
    decision = None
    if applicant_context:
        decision = apply_rules_and_ml(extracted, applicant_context)

    # Final packaged result
    return {
        "answer": llm_response.get("answer"),
        "explanation": llm_response.get("explanation"),
        "evidence": llm_response.get("evidence"),
        "evidence_map": evidence_map,
        "extracted_attributes": extracted,
        "decision": decision
    }




def put_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    High-level function to load, chunk, embed, and store a PDF in Qdrant.

    Args:
        pdf_path (str): Full path to the PDF file.

    Returns:
        dict: Information about the process.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Run the existing vector store creation logic
    create_vector_store(str(pdf_file))

    return {
        "status": "success",
        "message": f"PDF '{pdf_file.name}' stored in Qdrant.",
        "file_path": str(pdf_file)
    }


# 
def retrieve(user_query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    High-level function to search Qdrant for a user query and summarize with Gemini.
    """
    # Step 1: Expand the query
    expanded_queries = create_queries(user_query)

    # Step 2: Search each variation in Qdrant
    all_results = []
    for q in expanded_queries:
        all_results.extend(search_vector_store(q, top_k=top_k))

    # Step 3: Merge duplicate chunks
    unique_chunks = merge_unique_chunks(all_results)

    # Step 4: Prepare context text from retrieved chunks
    context_text = "\n\n".join(chunk.page_content for chunk in unique_chunks)

    # Step 5: Ask Gemini for a one-line final answer
    gemini_prompt = f"""
    You are an insurance policy assistant. 
    Based on the following retrieved information, answer the question in ONE short, clear sentence.

    Question: {user_query}

    Context:
    {context_text}

    If the answer cannot be found in the context, say "Not enough information."
    """
    gemini_response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=gemini_prompt
    )
    final_answer = gemini_response.text.strip()

    # Step 6: Return clean JSON with final answer
    return {
        "query": user_query,
        "expanded_queries": expanded_queries,
        "results": [
            {
                "content": chunk.page_content,
                "metadata": chunk.metadata
            }
            for chunk in unique_chunks
        ],
        "final_answer": final_answer
    }
# if __name__ == "__main__":
#     import json

#     # Example test query
#     query = "46M, knee surgery, Pune, 3-month policy"

#     # Call your retrieve function
#     result = retrieve(query, top_k=3)

#     # Pretty print JSON output
#     print(json.dumps(result, indent=2, ensure_ascii=False))

# if __name__ == "__main__":
#     import json

#     query = "46M, knee surgery, Pune, 3-month policy"
#     result = retrieve(query, top_k=3)

#     # Pretty print full JSON
#     print("\n--- FULL RESPONSE ---")
#     print(json.dumps(result, indent=2, ensure_ascii=False))

#     # Highlight answer
#     print("\n--- FINAL ANSWER ---")
#     print(result["final_answer"])

#     # If answer says "Yes", show related titles from metadata
#     if result["final_answer"].lower().startswith("yes"):
#         titles = set()
#         for chunk in result["results"]:
#             title = chunk["metadata"].get("title")
#             if title:
#                 titles.add(title)

#         if titles:
#             print("\n--- SUPPORTING DOCUMENT TITLES ---")
#             for t in titles:
#                 print(f"- {t}")
#         else:
#             print("\n(No titles found in metadata)")


put_pdf("zz.pdf")