# build_index.py

from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


from youtube_transcript_api import YouTubeTranscriptApi

ytt_api = YouTubeTranscriptApi()


video_id = "-HzgcbRXUK8"

transcript = ytt_api.fetch(video_id)
text = " ".join(s.text for s in transcript)


# 2. Split text
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

chunks = splitter.split_text(text)
docs = [Document(page_content=c) for c in chunks]

# 3. Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

# 4. FAISS index
vectorstore = FAISS.from_documents(docs, embeddings)
vectorstore.save_local("faiss_index")

print("FAISS index built successfully")
