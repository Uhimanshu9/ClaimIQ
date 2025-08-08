from google import genai
from google.genai import types
from ..queue.vectorStore import get_vector_store
GEMINI_API_KEY = "AIzaSyDa9Wc6y0J538wl_sIH7X10H4igsrcB1fU"


# Initialize Gemini client
# Replace with secure loading in prod
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are an expert assistant for processing and evaluating natural
language queries against unstructured documents such as insurance policies, contracts, and emails.

Your job is to:
- Interpret vague, incomplete, or natural language queries and extract structured information (e.g., age, location, treatment, policy duration).
- Retrieve and evaluate relevant clauses or rules from the provided documents using semantic understanding.
- Decide on the outcome (e.g., approval or rejection of claim, payout amount, eligibility) based on the retrieved information.
- Return a structured, interpretable response including decision, amount (if applicable), and clear justification.
- Reference the exact document clauses used in making the decision.

Respond in the following format:

Answer:
{
  "decision": "<Approved / Rejected / Eligible / Not Eligible / Info>",
  "amount": "<Amount if applicable or 'N/A'>",
  "justification": "<Clear explanation of how the decision was derived>",
}

References:
- "<quote or clause 1>" from <filename or metadata>
- "<quote or clause 2>" from <filename or metadata>
"""


def chat_with_gemini(query: str, collection_name: str = "pdf_collection") -> dict:
    try:
        # Step 1: Retrieve relevant document chunks
        results = get_vector_store(
            query=query, collection_name=collection_name)

        if not results:
            return {
                "answer": "Sorry, no relevant information found in the documents.",
                "references": []
            }

        # Step 2: Prepare input for Gemini
        context_chunks = "\n\n".join([
            f"{doc.page_content}\n[Metadata: {doc.metadata}]" for doc in results
        ])

        full_prompt = f"""
{SYSTEM_PROMPT}

Query: {query}

Document Chunks:
{context_chunks}
"""

        # Step 3: Call Gemini
        response = client.models.generate_content(
            model="gemini-1.5-flash-latest",  # Use gemini-1.5-pro-latest for better reasoning
            contents=[full_prompt]
        )

        return {
            "query": query,
            "answer": response.text
        }

    except Exception as e:
        return {
            "error": str(e)
        }
