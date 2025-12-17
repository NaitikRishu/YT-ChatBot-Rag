# backend.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.rag import rag_chain

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Query(BaseModel):
    question: str

@app.post("/ask")
def ask(query: Query):
    answer = rag_chain.invoke(query.question)
    return {"answer": answer}
