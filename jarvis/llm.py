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


def create_groq_client(api_key: str) -> Groq:
    """Create a Groq client across older groq/newer httpx installs."""
    try:
        return Groq(api_key=api_key)
    except TypeError as exc:
        error_text = str(exc).lower()
        if "unexpected keyword argument 'proxies'" not in error_text:
            raise

        logger.warning(
            "Detected Groq/httpx proxy compatibility issue; retrying with "
            "an explicit HTTP client. Reinstall requirements to make this permanent."
        )

        try:
            import httpx
        except ImportError as httpx_exc:
            raise RuntimeError(
                "Groq needs a compatible httpx install. Install httpx==0.27.0 "
                "or upgrade the groq package."
            ) from httpx_exc

        return Groq(
            api_key=api_key,
            http_client=httpx.Client(timeout=60.0, follow_redirects=True),
        )


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
        """Initialize Groq client with current API key."""
        logger.info(f"🔑 GROQ_API_KEYS found: {len(self.api_keys)} keys")

        if not self.api_keys:
            logger.error("❌ No Groq API keys configured!")
            logger.error("   Looking for: GROQ_API_KEY, GROQ_API_KEY2, GROQ_API_KEY3, GROQ_API_KEY4")
            logger.error("   in .env file")
            return

        for i, key in enumerate(self.api_keys):
            if not key:
                logger.warning(f"Key {i+1} is empty, skipping")
                continue
            if key in self.failed_keys:
                logger.warning(f"Key {i+1} already failed, skipping")
                continue

            try:
                # Mask key for logging
                masked_key = key[:10] + "..." + key[-4:] if len(key) > 14 else "***"
                logger.info(f"🧪 Initializing Groq client with key {i+1}: {masked_key}")

                self.client = create_groq_client(key)
                self.current_key_index = i

                # Try a test call
                try:
                    test_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=5
                    )
                    logger.info(f"✅ Key {i+1} works! Groq client ready.")
                    return
                except Exception as test_e:
                    # Test call failed but client created - might work on retry
                    error_str = str(test_e).lower()
                    if "rate" in error_str or "429" in error_str:
                        logger.warning(f"⚠️ Key {i+1} hit rate limit on test, but client created")
                        return  # Keep this client, will retry on actual call
                    elif "auth" in error_str or "401" in error_str:
                        logger.error(f"❌ Key {i+1} authentication failed: {test_e}")
                        self.failed_keys.add(key)
                        self.client = None
                    else:
                        logger.warning(f"⚠️ Key {i+1} test call failed: {test_e}")
                        # Keep the client anyway, might be transient
                        return

            except Exception as e:
                logger.error(f"❌ Key {i+1} initialization failed: {e}")
                self.failed_keys.add(key)
                self.client = None

        logger.error("❌ All Groq API keys failed to initialize!")

    def _rotate_api_key(self):
        """Rotate to next available API key."""
        original_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        while self.current_key_index != original_index:
            key = self.api_keys[self.current_key_index]
            if key and key not in self.failed_keys:
                try:
                    self.client = create_groq_client(key)
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

    def chat(self, message: str, context: Optional[List[Dict]] = None, max_tokens: int = 512) -> Union[str, Dict]:
        """Main chat interface with JARVIS - Fast & Concise."""
        try:
            # JARVIS personality - concise and helpful
            system_prompt = """You are JARVIS, Tony Stark's AI assistant. Be concise, helpful, proactive.

Available tool commands (colon syntax):
- NASA: nasa-apod, nasa-mars:[sol], nasa-earth:[lat,lon], nasa-iss, nasa-space, nasa-library:[query]
- Finnhub: finnhub-quote:[SYM], finnhub-news:[SYM], finnhub-company:[SYM], finnhub-financials:[SYM], finnhub-forex:[PAIR], finnhub-crypto:[PAIR]
- Ninjas: nutrition:[food], city:[name], fact, exercises:[muscle], ip-lookup:[ip], sentiment:[text], email-validate:[email]
- Finance: crypto:[coin], stock:[SYM], currency:[FROM TO AMT]
- Media: youtube:[query], movies:[title], games:[game], recipe:[ingredient], podcast:[topic]
- Data: weather:[city], forecast:[city], news:[topic], wiki:[topic], country:[name], holidays:[code], global-holidays:[code]
- Fun: joke, quote, advice, number-fact:[n], useless-fact, riddle, coin, dice, 8ball:[question]
- System: system, ping:[host], smart-search:[query], daily:[city], translate:[target|text]
- Utility: image:[prompt], qr:[data], web:[query], reddit:[subreddit], github-user:[user], github-repo:[repo], books:[query], anime:[query]

Help the user decide which command fits their need. Keep responses under 100 words."""

            messages = context if context else []
            if not messages:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            else:
                # Ensure system prompt is first
                if not any(m.get("role") == "system" for m in messages):
                    messages.insert(0, {"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": message})

            # Use smaller max_tokens for faster, cheaper responses
            response_text = self._call_groq(messages, max_tokens=max_tokens)

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
