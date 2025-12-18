# backend/index_manager.py

from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os


embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)


def build_index_for_video(video_id: str):
    # 1. Fetch transcript
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    text = " ".join(chunk["text"] for chunk in transcript)

    # 2. Split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    chunks = splitter.split_text(text)
    docs = [Document(page_content=c) for c in chunks]

    # 3. Build FAISS
    vectorstore = FAISS.from_documents(docs, embeddings)

    # 4. Save per-video
    save_path = f"faiss_indexes/{video_id}"
    os.makedirs(save_path, exist_ok=True)
    vectorstore.save_local(save_path)

    return {
        "status": "indexed",
        "chunks": len(docs),
        "path": save_path
    }
