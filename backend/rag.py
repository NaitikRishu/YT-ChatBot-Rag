from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

#LLM
model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=150,
    temperature=0.6,
    do_sample=True,
    top_p=0.9,
    repetition_penalty=1.1,
    return_full_text=False,  # Only return generated text, not the prompt
)

llm = HuggingFacePipeline(pipeline=pipe)

#prompt
prompt = PromptTemplate(
    template="""<|system|>
You are a helpful assistant. Answer questions based only on the provided context. If the answer is not in the context, say "The video does not clearly explain this."</s>
<|user|>
Context: {context}

Question: {question}</s>
<|assistant|>
""",
    input_variables=["context", "question"],
)

# Join documents into a single string
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def extract_answer(text: str) -> str:
    """
    Extract only the answer portion from the LLM output.
    TinyLlama often repeats the prompt, so we need to clean it.
    """
    # Try to find "Answer:" and take everything after it
    if "Answer:" in text:
        parts = text.split("Answer:")
        answer = parts[-1].strip()
    else:
        answer = text.strip()
    
    
    answer = answer.replace("You are a helpful assistant.", "")
    answer = answer.replace("Do NOT repeat the context.", "")
    
   
    answer = " ".join(answer.split())
    
    return answer

# Rag Chain
def get_rag_chain(retriever):
    """
    Create a RAG chain with the provided retriever.
    This allows us to use different retrievers for different videos.
    """
    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
        | RunnableLambda(extract_answer)  # Clean the output
    )
    return rag_chain