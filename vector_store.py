import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

def create_knowledge_base(pdf_path):
    # 1. Load PDF
    print(f"Loading {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # 2. Split PDF into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    # 3. Setup Gemini Embeddings
    api_key = os.getenv("GOOGLE_API_KEY")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2", 
        google_api_key=api_key
    )
    
    # 4. Create or Update Index
    print(f"Processing {len(docs)} chunks into vector index...")
    try:
        if os.path.exists("faiss_learning_index"):
            vector_store = FAISS.load_local("faiss_learning_index", embeddings, allow_dangerous_deserialization=True)
            new_store = FAISS.from_documents(docs, embeddings)
            vector_store.merge_from(new_store)
            vector_store.save_local("faiss_learning_index")
            print("✅ Success: Appended to faiss_learning_index.")
        else:
            vector_store = FAISS.from_documents(docs, embeddings)
            vector_store.save_local("faiss_learning_index")
            print("✅ Success: faiss_learning_index created locally.")
    except Exception as e:
        print(f"❌ Error during embedding: {e}")

if __name__ == "__main__":
    pdf_file = "data/machine_learning_course.pdf" 
    if os.path.exists(pdf_file):
        create_knowledge_base(pdf_file)
    else:
        print(f"❌ Error: Could not find {pdf_file}")