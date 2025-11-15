"""Test Gemini API connection for Robot 1.5."""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.services.llm_service import LLMService

def test_gemini_connection():
    """Test that Gemini API is configured and working."""
    print("Testing Gemini API connection...")
    print("-" * 50)

    # Check if API key is set
    if not settings.GEMINI_API_KEY:
        print("[FAIL] GEMINI_API_KEY not set in environment")
        return False

    print(f"[OK] GEMINI_API_KEY found (length: {len(settings.GEMINI_API_KEY)} chars)")

    # Initialize LLM service (pass API key from settings)
    try:
        llm_service = LLMService(api_key=settings.GEMINI_API_KEY)
        print("[OK] LLMService initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize LLMService: {e}")
        return False

    # Test connection
    print("\nTesting API connection...")
    try:
        is_connected = llm_service.test_connection()
        if is_connected:
            print("[SUCCESS] Gemini API connection successful!")
            return True
        else:
            print("[FAIL] Gemini API connection failed")
            return False
    except Exception as e:
        print(f"[FAIL] Connection test error: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_connection()
    sys.exit(0 if success else 1)
