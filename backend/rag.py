# rag.py
import os
from dotenv import load_dotenv


load_dotenv()


from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser


from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


#Embeddibgs
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

#Vectorstore
vectorstore = FAISS.load_local(
    "faiss_index",
    embeddings,
    allow_dangerous_deserialization=True,
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

#llm
model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"



tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

# Create pipeline
pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=64,  
    temperature=0.3,  
    do_sample=True,
    top_p=0.9,
    repetition_penalty=1.2, 
    return_full_text=False, 
)


llm = HuggingFacePipeline(pipeline=pipe)

#prompt
prompt = PromptTemplate(
    template="""You are a strict question-answering system.

If the context does NOT contain information needed to answer the question,
respond with exactly: "Not related."

Context:
{context}

Question:
{question}

Answer:""",
    input_variables=["context", "question"],
)



#join the docs
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

#make runnable chain
rag_chain = (
    {
        "context": retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)


# backend/rag.py
def get_rag_chain():
    return rag_chain
