from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings


def create_vector_store(file_path: str, collection_name: str = "pdf_collection", qdrant_url: str = "http://localhost:6333"):
    # Load the PDF document
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    print(f'Loaded {len(documents)} documents from {file_path}')

    # Split the documents into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(documents)

    print(f'Split into {len(split_docs)} chunks.')

    # Use HuggingFace embeddings for vectorization
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")

    # Create a Qdrant vector store
    vector_store = QdrantVectorStore.from_documents(
        split_docs,
        embeddings,
        collection_name=collection_name,
        url=qdrant_url,
    )
    print(f"Vector store created with {len(split_docs)} documents in '{collection_name}'.")


def get_vector_store(query: str, collection_name: str = "pdf_collection", qdrant_url: str = "http://localhost:6333"):
    retiver = QdrantVectorStore.from_existing_collection(
        collection_name=collection_name,
        embedding=HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5"),
        url=qdrant_url,
    )
    query = query.strip()
    results = retiver.similarity_search(query)
    return results



# def main():
#     file_path = "./pdf/BAJHLIP23020V012223.pdf" 
#     create_vector_store(file_path)
#     # print(get_vector_store(input("What is the fs model in the PDF?")))
#     input_user = input("Press Enter to exit...")  
    