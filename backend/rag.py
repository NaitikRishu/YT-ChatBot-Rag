from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# LLM Configuration
model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)


pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=200,  # Increased for better answers
    temperature=0.3,  # Lower for more focused answers
    do_sample=True,
    top_p=0.9,
    repetition_penalty=1.2,  # Increased to reduce repetition
    return_full_text=False,
)

llm = HuggingFacePipeline(pipeline=pipe)

# Improved Prompt Template
prompt = PromptTemplate(
    template="""<|system|>
You are a helpful assistant that answers questions about YouTube videos.
Use ONLY the information from the provided context to answer.
Be concise and clear. If the answer is not in the context, say "This information is not covered in the video."</s>
<|user|>
Context from the video:
{context}

Question: {question}

Please provide a clear, concise answer based only on the context above.</s>
<|assistant|>
""",
    input_variables=["context", "question"],
)

# Format documents for context
def format_docs(docs):
    """Join retrieved documents into a single context string"""
    return "\n\n".join(doc.page_content for doc in docs)


def extract_answer(text: str) -> str:
    """
    Extract and clean the answer from LLM output.
    Removes any repeated prompts and system messages.
    """
    # Remove common repetitions
    text = text.strip()
    
    # Remove system messages if they appear
    cleanup_phrases = [
        "You are a helpful assistant",
        "Use ONLY the information",
        "Context from the video:",
        "Question:",
        "Please provide",
        "<|system|>",
        "<|user|>",
        "<|assistant|>",
        "</s>"
    ]
    
    for phrase in cleanup_phrases:
        text = text.replace(phrase, "")
    
    # Take only the first paragraph if multiple exist
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs:
        # Return first substantial paragraph (> 20 chars)
        for para in paragraphs:
            if len(para) > 20:
                return para
    
    # Clean up whitespace
    text = " ".join(text.split())
    
    # Limit length to avoid rambling
    if len(text) > 500:
        # Try to cut at a sentence boundary
        text = text[:500]
        last_period = text.rfind('.')
        if last_period > 300:
            text = text[:last_period + 1]
    
    return text.strip()


def get_rag_chain(retriever):
    """
    Create a RAG chain with the provided retriever.
    Retrieves relevant context and generates answers using the LLM.
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