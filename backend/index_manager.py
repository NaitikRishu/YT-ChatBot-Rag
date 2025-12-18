from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import shutil
import os

FAISS_DIR = "faiss_index"

def build_index_for_video(video_id: str):
    # 🔥 DELETE OLD INDEX (overwrite allowed)
    if os.path.exists(FAISS_DIR):
        shutil.rmtree(FAISS_DIR)

    # 1. Transcript
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id)
    text = " ".join(t.text for t in transcript)

    # 2. Split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    docs = [Document(page_content=t) for t in splitter.split_text(text)]

    # 3. Embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5"
    )

    # 4. FAISS
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(FAISS_DIR)

    return vectorstore.as_retriever(search_kwargs={"k": 4})
