"""jarvis.llm

JARVIS Language Model Interface with multi-provider support.
Features:
- Groq API key rotation
- Multi-provider fallback (Groq → Gemini → OpenRouter)
- Rate limit handling
- Error recovery
"""

import logging
import random
import time
from typing import Dict, List, Optional, Union

from groq import Groq
from jarvis import config

logger = logging.getLogger(__name__)


class JarvisLLM:
    """JARVIS LLM interface with fallback support."""

    def __init__(self):
        self.api_keys = config.GROQ_API_KEYS.copy()
        self.current_key_index = 0
        self.model = config.GROQ_MODEL
        self.client = None
        self.failed_keys = set()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Groq client with current API key and test it."""
        if not self.api_keys:
            logger.error("❌ No Groq API keys configured!")
            logger.error("   Add GROQ_API_KEY, GROQ_API_KEY2, etc to .env file")
            return

        logger.info(f"🔑 Testing {len(self.api_keys)} API key(s)...")

        while self.current_key_index < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            if key and key not in self.failed_keys:
                try:
                    self.client = Groq(api_key=key)
                    # Test the key with a simple API call
                    logger.info(f"🧪 Testing key {self.current_key_index + 1}...")
                    test_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=5
                    )
                    logger.info(f"✅ Groq client initialized with key {self.current_key_index + 1}")
                    return
                except Exception as e:
                    error_str = str(e)
                    logger.warning(f"❌ Key {self.current_key_index + 1} failed: {error_str[:100]}")
                    if "auth" in error_str.lower() or "401" in error_str:
                        logger.warning("   → Authentication error - key may be invalid or expired")
                    elif "rate" in error_str.lower() or "429" in error_str:
                        logger.warning("   → Rate limit hit - will try other keys")
                    self.failed_keys.add(key)
            self.current_key_index += 1

        logger.error("❌ All Groq API keys failed to initialize!")
        logger.error("   Please check your .env file and ensure API keys are valid")

    def _rotate_api_key(self):
        """Rotate to next available API key."""
        original_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        while self.current_key_index != original_index:
            key = self.api_keys[self.current_key_index]
            if key and key not in self.failed_keys:
                try:
                    self.client = Groq(api_key=key)
                    logger.info(f"🔄 Rotated to API key {self.current_key_index + 1}")
                    return True
                except Exception as e:
                    logger.warning(f"Key {self.current_key_index + 1} failed: {e}")
                    self.failed_keys.add(key)
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        logger.error("No working API keys available!")
        return False

    def _call_groq(self, messages: List[Dict], max_tokens: int = 1024) -> str:
        """Call Groq API with automatic key rotation on failure."""
        if not self.client:
            self._initialize_client()
            if not self.client:
                raise Exception("No working API keys available. Please check your .env file.")

        attempts = 0
        max_attempts = len(self.api_keys) if self.api_keys else 1

        while attempts < max_attempts:
            try:
                logger.info(f"🤖 Using model: {self.model}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                return response.choices[0].message.content

            except Exception as e:
                error_str = str(e).lower()
                attempts += 1

                if "rate limit" in error_str or "429" in error_str:
                    logger.warning(f"Rate limit hit, rotating key... ({attempts}/{max_attempts})")
                    if self._rotate_api_key():
                        time.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        break
                elif "401" in error_str or "authentication" in error_str:
                    logger.warning(f"Auth failed, rotating key... ({attempts}/{max_attempts})")
                    if self._rotate_api_key():
                        continue
                    else:
                        break
                elif "413" in error_str or "payload too large" in error_str:
                    # Trim message history and retry
                    if len(messages) > 2:
                        logger.warning("Payload too large, trimming history...")
                        messages = [messages[0]] + messages[-2:]  # Keep system + last 2
                        attempts -= 1  # Don't count as attempt
                        continue
                    raise
                else:
                    logger.error(f"Groq API error: {e}")
                    raise

        # All Groq keys exhausted, try fallback providers
        return self._fallback_call(messages, max_tokens)

    def _fallback_call(self, messages: List[Dict], max_tokens: int) -> str:
        """Fallback to other providers when Groq fails."""

        # Try Gemini first
        if config.GEMINI_API_KEY:
            try:
                logger.info("🔄 Trying Gemini fallback...")
                import google.generativeai as genai
                genai.configure(api_key=config.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = messages[-1]["content"] if messages else ""
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.warning(f"Gemini fallback failed: {e}")

        # Try OpenRouter as last resort
        if config.OPENROUTER_API_KEY:
            try:
                logger.info("🔄 Trying OpenRouter fallback...")
                import requests
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": messages,
                        "max_tokens": max_tokens
                    },
                    timeout=30
                )
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"OpenRouter fallback failed: {e}")

        raise Exception("All LLM providers failed")

    def chat(self, message: str, context: Optional[List[Dict]] = None) -> Union[str, Dict]:
        """Main chat interface with JARVIS."""
        try:
            messages = context if context else []
            if not messages:
                messages = [
                    {"role": "system", "content": "You are JARVIS, an intelligent AI assistant."},
                    {"role": "user", "content": message}
                ]
            else:
                messages.append({"role": "user", "content": message})

            response_text = self._call_groq(messages)

            # Check if response contains actions/commands
            if "{" in response_text and "}" in response_text:
                try:
                    import json
                    # Try to extract JSON actions
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_str = response_text[json_start:json_end]
                    parsed = json.loads(json_str)
                    if "text" in parsed or "actions" in parsed:
                        return parsed
                except:
                    pass

            return response_text

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise

    def quick_response(self, prompt: str, max_tokens: int = 256) -> str:
        """Quick response for simple queries."""
        messages = [
            {"role": "system", "content": "You are JARVIS, a helpful AI assistant. Be concise."},
            {"role": "user", "content": prompt}
        ]
        return self._call_groq(messages, max_tokens=max_tokens)


def quick_chat(prompt: str) -> str:
    """Quick chat function for simple prompts."""
    llm = JarvisLLM()
    return llm.quick_response(prompt)
