"""
backend/src/ai/provider_pool.py

Zero-Cost Multi-Account API Key Pool & Rotation Engine for Helios.
Supports automatic key rotation and provider failover across:
1. Google Gemini API (gemini-2.0-flash, gemini-1.5-pro)
2. Groq API (llama-3.3-70b-versatile, llama-3.1-8b-instant)
3. Tavily Web Search API (1,000 free monthly searches per account)

Automatically catches 429 RateLimit / QuotaExhausted errors and seamlessly switches
to the next available API key in the pool.
"""
import os
import time
import logging
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger("helios.ai_pool")

class KeyState:
    def __init__(self, key: str):
        self.key = key
        self.failed_at: Optional[float] = None
        self.cooldown_seconds: float = 3600.0  # 1 hour cooldown on rate limit

    @property
    def is_available(self) -> bool:
        if self.failed_at is None:
            return True
        if time.time() - self.failed_at > self.cooldown_seconds:
            # Cooldown expired, mark available again
            self.failed_at = None
            return True
        return False

    def mark_failed(self):
        self.failed_at = time.time()
        logger.warning(f"API key ending in '...{self.key[-4:]}' marked on cooldown due to rate limit/quota.")


class MultiKeyPool:
    def __init__(self, env_prefix: str):
        self.env_prefix = env_prefix
        self.keys: List[KeyState] = []
        self._load_keys()

    def _load_keys(self):
        raw_keys = []
        # Check single env var with comma separation: e.g. GEMINI_API_KEYS=key1,key2
        plural_env = os.getenv(f"{self.env_prefix}_KEYS", "")
        if plural_env:
            raw_keys.extend([k.strip() for k in plural_env.split(",") if k.strip()])

        # Check single env var: e.g. GEMINI_API_KEY
        single_env = os.getenv(f"{self.env_prefix}_KEY", "")
        if single_env and single_env not in raw_keys:
            raw_keys.append(single_env.strip())

        # Check numbered env vars: e.g. GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
        for i in range(1, 20):
            k = os.getenv(f"{self.env_prefix}_KEY_{i}", "").strip()
            if k and k not in raw_keys:
                raw_keys.append(k)

        self.keys = [KeyState(k) for k in raw_keys]
        logger.info(f"Loaded {len(self.keys)} API keys for pool '{self.env_prefix}'")

    def get_working_key(self) -> Optional[str]:
        for key_state in self.keys:
            if key_state.is_available:
                return key_state.key
        return None

    def mark_key_failed(self, key: str):
        for key_state in self.keys:
            if key_state.key == key:
                key_state.mark_failed()
                break


class ZeroCostAIEngine:
    def __init__(self):
        self.gemini_pool = MultiKeyPool("GEMINI_API")
        self.groq_pool = MultiKeyPool("GROQ_API")
        self.tavily_pool = MultiKeyPool("TAVILY_API")

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        """
        Generates text using zero-cost models with multi-key rotation:
        1. Tries Gemini 2.0 Flash across all Gemini keys in pool.
        2. Falls back to Groq Llama-3.3-70b across all Groq keys in pool.
        """
        # Step 1: Try Gemini Pool
        while True:
            key = self.gemini_pool.get_working_key()
            if not key:
                break
            try:
                res = await self._call_gemini(key, prompt, system_instruction)
                return res
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                    self.gemini_pool.mark_key_failed(key)
                else:
                    logger.error(f"Gemini call failed with non-quota error: {e}")
                    self.gemini_pool.mark_key_failed(key)

        # Step 2: Fallback to Groq Pool
        while True:
            key = self.groq_pool.get_working_key()
            if not key:
                break
            try:
                res = await self._call_groq(key, prompt, system_instruction)
                return res
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "rate_limit" in err_msg or "quota" in err_msg:
                    self.groq_pool.mark_key_failed(key)
                else:
                    logger.error(f"Groq call failed: {e}")
                    self.groq_pool.mark_key_failed(key)

        raise RuntimeError("All zero-cost AI API keys in pool (Gemini & Groq) exhausted or unavailable!")

    async def _call_gemini(self, key: str, prompt: str, system_instruction: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\n{prompt}" if system_instruction else prompt}
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API status {resp.status_code}: {resp.text}")
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_groq(self, key: str, prompt: str, system_instruction: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_instruction or "You are an expert AI assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Groq API status {resp.status_code}: {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def search_web(self, query: str) -> Dict[str, Any]:
        """
        Executes web search using multi-key Tavily API pool (1,000 free searches/key).
        Automatically rotates keys when quota is reached.
        """
        while True:
            key = self.tavily_pool.get_working_key()
            if not key:
                raise RuntimeError("All Tavily Search API keys exhausted across accounts!")
            try:
                url = "https://api.tavily.com/search"
                payload = {
                    "api_key": key,
                    "query": query,
                    "search_depth": "smart",
                    "include_answer": True
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code != 200:
                        raise RuntimeError(f"Tavily API status {resp.status_code}: {resp.text}")
                    return resp.json()
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "unauthorized" in err_msg:
                    self.tavily_pool.mark_key_failed(key)
                else:
                    self.tavily_pool.mark_key_failed(key)


# Global Singleton Instance
ai_engine = ZeroCostAIEngine()
