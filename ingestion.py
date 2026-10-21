import chromadb
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from config import (
    LECTURES_DIR,
    CHROMA_DIR,
    EMBEDDING_MODEL_NAME,
    CHROMA_COLLECTION_NAME,
    RETRIEVER_K,
)


def get_vectorstore_and_retriever():
    """Load PDF lecture notes, build or connect to the ChromaDB vector store, and return retriever."""
    print("Initializing document ingestion and vector retriever...")
    
    loader = PyPDFDirectoryLoader(str(LECTURES_DIR))
    documents = loader.load()

    if not documents:
        print(f"[*] Note: No PDF documents found in '{LECTURES_DIR}'.")
        print("    Place your PDF files in the './lectures' folder to index study materials.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents) if documents else []

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if chunks:
        print(f"[*] Split into {len(chunks)} text chunks. Indexing into ChromaDB...")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            client=chroma_client,
            collection_name=CHROMA_COLLECTION_NAME,
        )
    else:
        vectorstore = Chroma(
            client=chroma_client,
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
        )

    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
    return vectorstore, retriever
