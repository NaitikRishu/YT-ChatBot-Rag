from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# LLM 
model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=200,
    temperature=0.3,
    do_sample=True,
    top_p=0.9,
    repetition_penalty=1.2,
    return_full_text=False,
)

llm = HuggingFacePipeline(pipeline=pipe)


prompt = PromptTemplate(
    template="""<|system|>
You are a helpful assistant that answers questions about YouTube videos.
Use ONLY the information from the provided context to answer.
Be concise and clear. If the answer is not in the context, say "This information is not covered in the video."

When answering follow-up questions, consider the conversation history to provide contextual responses.</s>
<|user|>
Context from the video:
{context}

Question: {question}

Please provide a clear, concise answer based only on the context above.</s>
<|assistant|>
""",
    input_variables=["context", "question"],
)

# Format documents 
def format_docs(docs):
    """Join retrieved documents into a single context string"""
    return "\n\n".join(doc.page_content for doc in docs)


def extract_answer(text: str) -> str:
    """
    Extract and clean the answer from LLM output.
    Removes any repeated prompts and system messages.
    """
    text = text.strip()
    
    
    cleanup_phrases = [
        "You are a helpful assistant",
        "Use ONLY the information",
        "Context from the video:",
        "Question:",
        "Please provide",
        "<|system|>",
        "<|user|>",
        "<|assistant|>",
        "</s>",
        "When answering follow-up"
    ]
    
    for phrase in cleanup_phrases:
        text = text.replace(phrase, "")
    
   
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs:
        for para in paragraphs:
            if len(para) > 20:
                return para
    
    
    text = " ".join(text.split())
    
   
    if len(text) > 500:
        text = text[:500]
        last_period = text.rfind('.')
        if last_period > 300:
            text = text[:last_period + 1]
    
    return text.strip()


def get_rag_chain(retriever):
    """
    Create a basic RAG chain without history.
    For backward compatibility.
    """
    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
        | RunnableLambda(extract_answer)
    )
    return rag_chain


def get_rag_chain_with_history(retriever):
    """
    Create a RAG chain that supports conversation history.
    The question input can include previous conversation context.
    """
    return get_rag_chain(retriever)  # Same implementation for now