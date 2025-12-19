"""
Test script to verify pytubefix transcript fetching works.
Run this after installing pytubefix.

Usage:
    python test_pytubefix.py
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required packages are installed"""
    logger.info("Testing imports...")
    
    required_packages = {
        'pytubefix': 'pytubefix',
        'fastapi': 'fastapi',
        'langchain': 'langchain',
        'langchain_community': 'langchain-community',
        'langchain_huggingface': 'langchain-huggingface',
        'sentence_transformers': 'sentence-transformers',
        'transformers': 'transformers',
        'torch': 'torch',
        'faiss': 'faiss-cpu',
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            logger.info(f"✅ {package}")
        except ImportError:
            logger.error(f"❌ {package} - Run: pip install {package}")
            missing.append(package)
    
    if missing:
        logger.error(f"\nMissing packages: {', '.join(missing)}")
        logger.error("Install with: pip install " + " ".join(missing))
        return False
    
    logger.info("\n✅ All packages installed!\n")
    return True


def test_pytubefix_fetch():
    """Test fetching a transcript with pytubefix"""
    logger.info("Testing pytubefix transcript fetching...")
    
    try:
        from pytubefix import YouTube
        import re
        
        # Test with a popular video that definitely has captions
        video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        logger.info(f"Fetching transcript for: {url}")
        
        # Create YouTube object
        yt = YouTube(url)
        logger.info(f"✅ Successfully accessed video: {yt.title}")
        
        # Check available captions
        available_captions = list(yt.captions.keys())
        logger.info(f"Available captions: {available_captions}")
        
        if not available_captions:
            logger.error("❌ No captions available for this video")
            return False
        
        # Try to get English captions
        caption = None
        for lang_code in ['en', 'a.en', 'en-US', 'en-GB']:
            if lang_code in yt.captions:
                caption = yt.captions[lang_code]
                logger.info(f"✅ Found {lang_code} captions")
                break
        
        # If no English, use first available
        if caption is None:
            first_lang = available_captions[0]
            caption = yt.captions[first_lang]
            logger.info(f"✅ Using {first_lang} captions")
        
        # Get caption text
        logger.info("Downloading caption data...")
        caption_text = caption.generate_srt_captions()
        
        if not caption_text:
            logger.error("❌ Caption text is empty")
            return False
        
        logger.info(f"✅ Downloaded {len(caption_text)} characters of caption data")
        
        # Parse SRT format
        transcript = []
        blocks = caption_text.split('\n\n')
        
        for block in blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                text = ' '.join(lines[2:]).strip()
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', '', text)
                if text:
                    transcript.append({'text': text})
        
        if transcript:
            logger.info(f"✅ Successfully parsed {len(transcript)} transcript segments")
            logger.info(f"\nFirst 3 segments:")
            for i, entry in enumerate(transcript[:3]):
                logger.info(f"  {i+1}. {entry['text'][:70]}...")
            logger.info("\n✅ pytubefix transcript fetching works!\n")
            return True
        else:
            logger.error("❌ Transcript is empty after parsing")
            return False
                
    except ImportError:
        logger.error("❌ pytubefix not installed. Run: pip install pytubefix")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_model():
    """Test loading the embedding model"""
    logger.info("Testing embedding model loading...")
    
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        
        logger.info("Loading BAAI/bge-small-en-v1.5 (this may take a minute on first run)...")
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        
        # Test embedding
        test_text = "This is a test sentence."
        logger.info(f"Creating embedding for: '{test_text}'")
        embedding = embeddings.embed_query(test_text)
        
        logger.info(f"✅ Embedding created successfully (dimension: {len(embedding)})\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading embedding model: {e}\n")
        return False


def test_llm():
    """Test loading the LLM"""
    logger.info("Testing LLM loading...")
    
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        from langchain_huggingface import HuggingFacePipeline
        
        model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        
        logger.info(f"Loading {model_id} (this may take several minutes on first run)...")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id)
        
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=50,
            temperature=0.7,
            return_full_text=False,
        )
        
        llm = HuggingFacePipeline(pipeline=pipe)
        
        logger.info("Testing text generation...")
        test_prompt = "The capital of France is"
        result = llm.invoke(test_prompt)
        
        logger.info(f"✅ LLM loaded successfully")
        logger.info(f"Test generation: '{test_prompt}' -> '{result[:50]}...'\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading LLM: {e}\n")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("YouTube RAG Chatbot - Testing pytubefix Setup")
    logger.info("=" * 60 + "\n")
    
    tests = [
        ("Package Imports", test_imports),
        ("pytubefix Transcript Fetching", test_pytubefix_fetch),
        ("Embedding Model", test_embedding_model),
        ("LLM (TinyLlama)", test_llm),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"{'=' * 60}")
        logger.info(f"TEST: {test_name}")
        logger.info(f"{'=' * 60}\n")
        
        result = test_func()
        results.append((test_name, result))
        
        if not result:
            logger.error(f"\n❌ {test_name} FAILED\n")
        
        logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        logger.info("\n🎉 All tests passed! You're ready to run the application.\n")
        logger.info("Next steps:")
        logger.info("  1. Make sure backend/index_manager.py uses pytubefix")
        logger.info("  2. Start backend: cd backend && uvicorn app:app --reload")
        logger.info("  3. Start frontend: cd frontend && python -m http.server 8080")
        logger.info("  4. Open browser: http://localhost:8080\n")
        return 0
    else:
        logger.error("\n❌ Some tests failed. Please fix the issues above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())