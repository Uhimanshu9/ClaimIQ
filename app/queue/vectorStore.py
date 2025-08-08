from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings


def create_vector_store(file_path: str, collection_name: str = "pdf_collection", qdrant_url: str = "http://qdrant:6333"):
    try:
        print(f"[INFO] Starting vector store creation for file: {file_path}")

        # Load the PDF document
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        print(f"[INFO] Loaded {len(documents)} documents from {file_path}")

        # Split the documents into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=200)
        split_docs = text_splitter.split_documents(documents)
        print(f"[INFO] Split documents into {len(split_docs)} chunks")

        # Initialize embeddings
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
        print(f"[INFO] Initialized HuggingFace embeddings with model 'BAAI/bge-base-en-v1.5'")

        # Create or update Qdrant vector store
        vector_store = QdrantVectorStore.add_documents(
            split_docs,
            embeddings,
            collection_name=collection_name,
            url=qdrant_url,
        )
        print(f"[INFO] Vector store created with {len(split_docs)} chunks in collection '{collection_name}' at '{qdrant_url}'")

    except Exception as e:
        print(f"[ERROR] Failed to create vector store: {e}")
        raise e


def get_vector_store(query: str, collection_name: str = "pdf_collection", qdrant_url: str = "http://qdrant:6333"):
    try:
        print(f"[INFO] Starting similarity search for query: '{query}' in collection '{collection_name}'")

        retiver = QdrantVectorStore.from_existing_collection(
            collection_name=collection_name,
            embedding=HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5"),
            url=qdrant_url,
        )
        print(f"[INFO] Connected to existing collection '{collection_name}'")

        query = query.strip()
        results = retiver.similarity_search(query)

        print(f"[INFO] Retrieved {len(results)} results for query '{query}'")
        return results

    except Exception as e:
        print(f"[ERROR] Similarity search failed: {e}")
        raise e


# Uncomment main to test locally
# def main():
#     file_path = "./pdf/BAJHLIP23020V012223.pdf" 
#     create_vector_store(file_path)
#     query = input("Enter your search query: ")
#     results = get_vector_store(query)
#     print("Search Results:")
#     for r in results:
#         print(r)
#     input_user = input("Press Enter to exit...")  
