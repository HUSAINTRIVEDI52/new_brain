import httpx
import logging
import time
from functools import lru_cache
from typing import List, Optional, Dict, Any, Literal
from utils.config import settings
from utils.logger import log_event

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/google-deepmind/antigravity",
            "X-Title": settings.PROJECT_NAME
        }
        self._client = httpx.AsyncClient(timeout=45.0)

    async def close(self):
        await self._client.aclose()

    async def get_embedding(self, text: str) -> List[float]:
        if not hasattr(self, "_embedding_cache"):
            self._embedding_cache = {}

        if text in self._embedding_cache:
            return self._embedding_cache[text]

        if not self.api_key or "your_openrouter_key" in self.api_key:
            return [0.0] * self.dimension

        url = f"{self.base_url}/embeddings"
        payload = {
            "model": "openai/text-embedding-3-small",
            "input": text
        }
        
        try:
            start_time = time.time()
            response = await self._client.post(url, headers=self.headers, json=payload)
            duration = int((time.time() - start_time) * 1000)
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            
            log_event(logging.INFO, "ai_embedding_generated", "Generated text embedding", duration_ms=duration, model="text-embedding-3-small")
            
            if len(self._embedding_cache) > 1000:
                self._embedding_cache.clear()
            self._embedding_cache[text] = embedding
            
            return embedding
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            return [0.0] * self.dimension

    async def _retry_request(self, func, *args, **kwargs):
        max_retries = 3
        base_delay = 1.0
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                status_code = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
                if attempt < max_retries - 1 and (status_code in [429, 502, 503, 504] or not status_code):
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"AI Service hiccup (attempt {attempt+1}/{max_retries}). Retrying in {delay}s... Error: {e}")
                    await asyncio.sleep(delay)
                    continue
                raise e

    async def summarize_text(self, text: str) -> str:
        async def _call():
            if not self.api_key or "your_openrouter_key" in self.api_key:
                 return f"Reflection Placeholder: {text[:50]}..."

            url = f"{self.base_url}/chat/completions"
            system_prompt = (
                "You are a reflective personal assistant. Summarize the following memory "
                "in a concise, second-brain tone (3-5 sentences). Avoid speculative or generic "
                "language. Stay strictly grounded in the provided text."
            )
            
            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            }

            start_time = time.time()
            response = await self._client.post(url, headers=self.headers, json=payload)
            duration = int((time.time() - start_time) * 1000)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            log_event(logging.INFO, "ai_summary_generated", "Generated reflective summary", duration_ms=duration, model="gemini-2.0-flash")
            return content

        try:
            return await self._retry_request(_call)
        except Exception as e:
            log_event(logging.ERROR, "ai_summary_failed", f"Summarization failed after retries: {str(e)}", status="failed")
            return f"Memory captured: {text[:150]}... [Summary generation failed]"

    async def refine_query(self, query: str) -> str:
        """
        Refines/expands abstract or short queries into richer semantic prompts.
        """
        if len(query.split()) > 5:
            return query  # Skip for long, specific queries

        async def _call():
            if not self.api_key or "your_openrouter_key" in self.api_key:
                return query

            url = f"{self.base_url}/chat/completions"
            system_prompt = (
                "You are a search assistant. Expand the following short/abstract query into "
                "a semantically rich search prompt that captures the underlying intent. "
                "Output ONLY the expanded query, no explanations."
            )
            
            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]
            }

            response = await self._client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        try:
            return await self._retry_request(_call)
        except Exception as e:
            logger.error(f"Query refinement error: {e}")
            return query

    async def extract_topics(self, text: str) -> List[str]:
        """
        Extracts 3-5 relevant keywords/topics from the text.
        """
        async def _call():
            if not self.api_key or "your_openrouter_key" in self.api_key:
                return []

            url = f"{self.base_url}/chat/completions"
            system_prompt = (
                "Extract the top 3-5 keywords or short topics from the following text. "
                "Return them as a comma-separated list. Be concise."
            )
            
            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            }

            response = await self._client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            # Split and clean
            topics = [t.strip() for t in content.split(",") if t.strip()]
            return topics[:5]

        try:
            return await self._retry_request(_call)
        except Exception as e:
            logger.error(f"Topic extraction error: {e}")
            return []

    async def generate_search_summary(self, query: str, memories: List[str]) -> str:
        async def _call():
            if not self.api_key or "your_openrouter_key" in self.api_key:
                return "Unable to synthesize memories without an active AI connection."

            if not memories:
                return "No relevant memories found to reflect upon."

            context = "\n---\n".join(memories)
            system_prompt = (
                "Based ONLY on the retrieved memories provided, synthesize a response to the user's query. "
                "Maintain a reflective, second-brain tone. Be concise (3-5 sentences). "
                "If the memories do not contain the answer, state that you don't recall this clearly "
                "instead of speculating."
            )
            
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}\n\nRetrieved Memories:\n{context}"}
                ]
            }

            response = await self._client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        try:
            return await self._retry_request(_call)
        except Exception as e:
            logger.error(f"Search synthesis error: {e}")
            return "I found some relevant notes, but I'm having trouble synthesizing a reflection right now."

ai_client = AIClient()
