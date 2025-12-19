

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import shutil
import os
import logging
import re
import time
from urllib.error import HTTPError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FAISS_DIR = "faiss_index"


_embeddings_model = None


def get_embeddings():
    
    global _embeddings_model
    if _embeddings_model is None:
        logger.info("Loading embeddings model...")
        _embeddings_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5"
        )
    return _embeddings_model


def fetch_transcript_with_pytubefix(video_id: str, max_retries: int = 3):
    """
    Fetch transcript using pytubefix with retry logic for rate limits.
    
    Args:
        video_id: YouTube video ID
        max_retries: Maximum number of retry attempts
        
    Returns:
        List of transcript entries with 'text' key
        
    Raises:
        ValueError: If transcript cannot be fetched
    """
    try:
        from pytubefix import YouTube
        from pytubefix.exceptions import VideoUnavailable
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        logger.info(f"Fetching transcript with pytubefix for: {video_id}")
        
        # Create YouTube object with error handling
        try:
            yt = YouTube(url)
        except VideoUnavailable:
            raise ValueError("Video is unavailable, private, or does not exist")
        except Exception as e:
            raise ValueError(f"Could not access video: {str(e)}")
        
        # Try to get captions with retry logic
        for attempt in range(max_retries):
            try:
                caption = None
                
                # Get available captions
                available_captions = yt.captions
                if not available_captions:
                    raise ValueError("No captions available for this video")
                
                # Log available captions
                caption_list = [(cap.code, cap.name) for cap in available_captions]
                logger.info(f"Available captions: {caption_list}")
                
                # Try to get English captions with different codes
                english_codes = ['en', 'a.en', 'en-US', 'en-GB', 'en-CA']
                for lang_code in english_codes:
                    try:
                        caption = yt.captions[lang_code]
                        logger.info(f"Found caption with code: {lang_code}")
                        break
                    except KeyError:
                        continue
                
                # If no exact match, try any caption that starts with 'en'
                if caption is None:
                    for cap in available_captions:
                        if cap.code.startswith('en'):
                            caption = cap
                            logger.info(f"Using caption: {cap.code} ({cap.name})")
                            break
                
                # If still no English, use first available
                if caption is None:
                    caption = list(available_captions)[0]
                    logger.info(f"No English captions found. Using: {caption.code} ({caption.name})")
                
                # Download caption text - THIS CAN FAIL WITH 429
                logger.info(f"Downloading caption data (attempt {attempt + 1}/{max_retries})...")
                caption_text = caption.generate_srt_captions()
                
                # If we got here, it worked!
                logger.info("Caption download successful")
                break
                
            except HTTPError as e:
                if e.code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 5  # 5, 10, 20 seconds
                        logger.warning(f"Rate limited (429). Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(
                            "YouTube is rate limiting your IP address. Please:\n"
                            "1. Wait 1-2 hours and try again\n"
                            "2. Switch to a different network (mobile hotspot, VPN)\n"
                            "3. Try a different video later"
                        )
                else:
                    raise ValueError(f"HTTP Error {e.code}: {e.reason}")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(2)
                    continue
                else:
                    raise
        
        # Parse SRT format
        transcript = []
        
        # Split by double newline (SRT format separates entries)
        blocks = caption_text.split('\n\n')
        
        for block in blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            
            # SRT format: index, timestamp, text
            if len(lines) >= 3:
                # Skip index (lines[0]) and timestamp (lines[1])
                # Get text (lines[2:] in case text spans multiple lines)
                text = ' '.join(lines[2:]).strip()
                
                # Remove SRT formatting tags like <font>, </font>, etc.
                text = re.sub(r'<[^>]+>', '', text)
                
                if text:
                    transcript.append({'text': text})
        
        if not transcript:
            raise ValueError("Transcript is empty after parsing")
        
        logger.info(f"Successfully fetched {len(transcript)} transcript segments")
        return transcript
            
    except ImportError:
        raise ValueError(
            "pytubefix not installed. Install with: pip install pytubefix"
        )
    except ValueError:
        # Re-raise ValueError with original message
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise ValueError(f"Failed to fetch transcript: {str(e)}")
    


def build_index_for_video(video_id: str):
    """
    Build FAISS index for a YouTube video's transcript using pytubefix.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        FAISS retriever object
        
    Raises:
        ValueError: If transcript cannot be fetched
        Exception: For other unexpected errors
    """
    try:
        # Delete old index
        if os.path.exists(FAISS_DIR):
            logger.info(f"Removing existing index at {FAISS_DIR}")
            shutil.rmtree(FAISS_DIR)

        # 1. Fetch transcript using pytubefix
        logger.info(f"Fetching transcript for video: {video_id}")
        transcript_list = fetch_transcript_with_pytubefix(video_id)

        # 2. Extract text from transcript
        if not transcript_list:
            raise ValueError("Transcript is empty")
            
        text = " ".join(entry["text"] for entry in transcript_list)
        
        if len(text.strip()) < 50:
            raise ValueError("Transcript too short to index (less than 50 characters)")

        logger.info(f"Transcript length: {len(text)} characters")

        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = splitter.split_text(text)
        
        
        docs = [Document(
            page_content=chunk,
            metadata={
                "video_id": video_id,
                "chunk_index": i,
                "source": "youtube"
            }
        ) for i, chunk in enumerate(chunks)]

        logger.info(f"Created {len(docs)} document chunks")

        
        embeddings = get_embeddings()

       
        logger.info("Building FAISS index...")
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(FAISS_DIR)
        
        logger.info("Index built successfully")
        
        
        return vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error building index: {e}", exc_info=True)
        raise Exception(f"Failed to build index: {str(e)}")


def load_existing_index():
    """Load an existing FAISS index if available"""
    if not os.path.exists(FAISS_DIR):
        return None
    
    try:
        logger.info("Loading existing FAISS index...")
        embeddings = get_embeddings()
        vectorstore = FAISS.load_local(
            FAISS_DIR, 
            embeddings,
            allow_dangerous_deserialization=True  # Required for FAISS
        )
        logger.info("Successfully loaded existing index")
        return vectorstore.as_retriever(search_kwargs={"k": 4})
    except Exception as e:
        logger.error(f"Failed to load existing index: {e}")
        return None