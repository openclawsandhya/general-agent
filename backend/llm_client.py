"""
LLM Client for LM Studio (OpenAI-compatible API).

CPU-optimised for local Mixtral inference:
  - httpx.AsyncClient (async) + httpx.Client (sync)
  - 180 second timeout — required for CPU inference
  - 2 retries with exponential backoff
  - LRU cache (50 entries) avoids re-running identical prompts
  - NO stream field in payload — causes 400 on Mixtral/LM Studio
  - Structured logging: model, latency, errors with stack traces
  - Never raises to callers — always returns string (text or fallback)
"""

import os
import time
import json
import asyncio
import hashlib
import traceback
from typing import Optional, List, Dict, Any

import httpx
from dotenv import load_dotenv
from .utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# LRU response cache (size 50) — avoids repeating slow CPU inference
# ---------------------------------------------------------------------------
_CACHE: Dict[str, str] = {}
_CACHE_KEYS: List[str] = []
_CACHE_MAX = 50

def _cache_get(key: str) -> Optional[str]:
    return _CACHE.get(key)

def _cache_put(key: str, value: str) -> None:
    if key in _CACHE:
        _CACHE_KEYS.remove(key)
    elif len(_CACHE_KEYS) >= _CACHE_MAX:
        _CACHE.pop(_CACHE_KEYS.pop(0), None)
    _CACHE[key] = value
    _CACHE_KEYS.append(key)

def _cache_key(model: str, messages: List[Dict], temperature: float) -> str:
    raw = json.dumps({"m": model, "msgs": messages, "t": temperature}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


class LLMClient:
    """
    HTTP client for LM Studio OpenAI-compatible endpoint.

    Both async and sync interfaces are provided.
    Call signature is fully backward compatible with all callers:
      - generate_response(messages=[...])            async
      - generate_response(prompt="...", system_prompt="...")   async legacy
      - generate_response_sync(...)                  sync (planner/controller)
    """

    FALLBACK = (
        "I'm experiencing a temporary inference delay. "
        "Please retry in a moment."
    )

    def __init__(
        self,
        base_url: Optional[str] = None,
        model:    Optional[str] = None,
        timeout:  Optional[int] = None,
    ):
        self.base_url   = (base_url or os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")).rstrip("/")
        self.model      = model   or os.getenv("LLM_MODEL",    "phi-3.1-mini-4k-instruct")
        self.timeout    = int(timeout or os.getenv("LLM_TIMEOUT",    120))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", 256))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0.7))
        self.max_retries = 2

        self._chat_url   = f"{self.base_url}/chat/completions"
        self._models_url = f"{self.base_url}/models"

        logger.info(
            f"[LLMClient] Ready | model={self.model} | "
            f"url={self.base_url} | timeout={self.timeout}s | max_tokens={self.max_tokens}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_messages(
        self,
        prompt: Optional[str],
        system_prompt: Optional[str],
        messages: Optional[List[Dict[str, str]]],
    ) -> List[Dict[str, str]]:
        if messages is not None:
            return messages
        if prompt is None:
            raise ValueError("Either 'messages' or 'prompt' required.")
        out: List[Dict[str, str]] = []
        if system_prompt:
            out.append({"role": "system", "content": system_prompt})
        out.append({"role": "user", "content": prompt})
        return out

    def _payload(self, messages: List[Dict], temperature: float, max_tokens: int) -> Dict:
        # NOTE: "stream" key intentionally omitted — LM Studio returns 400 with stream=False on some models
        return {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }

    def _parse(self, result: Dict) -> str:
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Bad LLM response structure: {exc} | raw={result}") from exc

    # ------------------------------------------------------------------
    # Async generate_response
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        prompt:        Optional[str]              = None,
        system_prompt: Optional[str]              = None,
        messages:      Optional[List[Dict[str,str]]] = None,
        temperature:   Optional[float]            = None,
        max_tokens:    Optional[int]              = None,
    ) -> str:
        """
        Async LLM call. Returns text or FALLBACK — never raises.
        Accepts messages=[...] or prompt=/system_prompt= (legacy).
        """
        temp      = temperature if temperature is not None else self.temperature
        max_tok   = max_tokens  if max_tokens  is not None else self.max_tokens
        msgs      = self._make_messages(prompt, system_prompt, messages)
        key       = _cache_key(self.model, msgs, temp)

        hit = _cache_get(key)
        if hit:
            logger.info("[LLMClient] Cache hit (async)")
            return hit

        payload     = self._payload(msgs, temp, max_tok)
        last_error  = None

        for attempt in range(1, self.max_retries + 1):
            t0 = time.monotonic()
            try:
                logger.info(
                    f"[LLMClient] Async attempt {attempt}/{self.max_retries} "
                    f"-> POST {self._chat_url} (timeout={self.timeout}s)"
                )
                logger.debug(f"[LLMClient] Payload: {json.dumps(payload, ensure_ascii=False)[:300]}")

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        self._chat_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                latency = time.monotonic() - t0
                text    = self._parse(data)
                _cache_put(key, text)
                logger.info(
                    f"[LLMClient] OK | latency={latency:.2f}s | "
                    f"chars={len(text)} | model={self.model}"
                )
                return text

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    f"[LLMClient] Attempt {attempt} TIMEOUT after {self.timeout}s — "
                    f"model={self.model} | consider shortening the prompt"
                )
            except httpx.ConnectError as exc:
                last_error = exc
                logger.error(
                    f"[LLMClient] Attempt {attempt} CONNECTION REFUSED "
                    f"at {self.base_url} — is LM Studio running?"
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.error(
                    f"[LLMClient] Attempt {attempt} HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:400]}"
                )
            except (json.JSONDecodeError, RuntimeError) as exc:
                last_error = exc
                logger.error(f"[LLMClient] Attempt {attempt} PARSE ERROR: {exc}")
                logger.debug(traceback.format_exc())
                break   # Identical request will fail again
            except Exception as exc:
                last_error = exc
                logger.error(f"[LLMClient] Attempt {attempt} UNEXPECTED: {type(exc).__name__}: {exc}")
                logger.debug(traceback.format_exc())

            if attempt < self.max_retries:
                wait = max(2, 2 ** (attempt - 1))
                logger.info(f"[LLMClient] Retrying in {wait}s...")
                await asyncio.sleep(wait)

        logger.error(f"[LLMClient] All async attempts failed. Last: {last_error}")
        return f"LLM_ERROR: {type(last_error).__name__}: {last_error}"

    async def complete(self, prompt: str) -> str:
        """
        Single-string LLM call — convenience alias for generate_response(prompt=...).

        The caller is responsible for embedding any system instructions directly
        inside the prompt string. Returns raw text — never raises.

        Args:
            prompt: Full prompt string (may include role instructions inline).

        Returns:
            Raw LLM response text, or an LLM_ERROR string on failure.
        """
        return await self.generate_response(prompt=prompt)

    # ------------------------------------------------------------------
    # Sync generate_response_sync
    # ------------------------------------------------------------------

    def generate_response_sync(
        self,
        prompt:        Optional[str]              = None,
        system_prompt: Optional[str]              = None,
        messages:      Optional[List[Dict[str,str]]] = None,
        temperature:   Optional[float]            = None,
        max_tokens:    Optional[int]              = None,
    ) -> str:
        """
        Sync LLM call for Planner/AgentController (non-async callers).
        Returns text or FALLBACK — never raises.
        """
        temp    = temperature if temperature is not None else self.temperature
        max_tok = max_tokens  if max_tokens  is not None else self.max_tokens
        msgs    = self._make_messages(prompt, system_prompt, messages)
        key     = _cache_key(self.model, msgs, temp)

        hit = _cache_get(key)
        if hit:
            logger.info("[LLMClient] Cache hit (sync)")
            return hit

        payload    = self._payload(msgs, temp, max_tok)
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            t0 = time.monotonic()
            try:
                logger.info(
                    f"[LLMClient] Sync attempt {attempt}/{self.max_retries} "
                    f"-> POST {self._chat_url} (timeout={self.timeout}s)"
                )
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        self._chat_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                latency = time.monotonic() - t0
                text    = self._parse(data)
                _cache_put(key, text)
                logger.info(
                    f"[LLMClient] OK (sync) | latency={latency:.2f}s | "
                    f"chars={len(text)} | model={self.model}"
                )
                return text

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(f"[LLMClient] Sync attempt {attempt} TIMEOUT after {self.timeout}s.")
            except httpx.ConnectError as exc:
                last_error = exc
                logger.error(f"[LLMClient] Sync attempt {attempt} CONNECTION REFUSED at {self.base_url}.")
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.error(
                    f"[LLMClient] Sync attempt {attempt} HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:400]}"
                )
            except (json.JSONDecodeError, RuntimeError) as exc:
                last_error = exc
                logger.error(f"[LLMClient] Sync attempt {attempt} PARSE ERROR: {exc}")
                break
            except Exception as exc:
                last_error = exc
                logger.error(f"[LLMClient] Sync attempt {attempt} UNEXPECTED: {type(exc).__name__}: {exc}")
                logger.debug(traceback.format_exc())

            if attempt < self.max_retries:
                wait = max(2, 2 ** (attempt - 1))
                logger.info(f"[LLMClient] Retrying sync in {wait}s...")
                time.sleep(wait)

        logger.error(f"[LLMClient] All sync attempts failed. Last: {last_error}")
        return f"LLM_ERROR: {type(last_error).__name__}: {last_error}"

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """
        Check LM Studio reachability and verify model is listed.
        Returns dict: {available, model_loaded, model_name, error}
        """
        result: Dict[str, Any] = {
            "available":    False,
            "model_loaded": False,
            "model_name":   self.model,
            "error":        None,
        }
        try:
            with httpx.Client(timeout=6) as client:
                resp = client.get(self._models_url)
                resp.raise_for_status()

            result["available"] = True
            ids = [m.get("id", "") for m in resp.json().get("data", [])]
            loaded = any(self.model in i or i in self.model for i in ids)
            result["model_loaded"] = loaded

            if loaded:
                logger.info(f"[LLMClient] Health OK — '{self.model}' is listed")
            else:
                result["error"] = f"'{self.model}' not found. Available: {ids}"
                logger.warning(f"[LLMClient] Health WARNING — {result['error']}")

        except httpx.ConnectError:
            result["error"] = f"Cannot connect to {self.base_url}"
            logger.error(f"[LLMClient] Health FAIL — connection refused")
        except httpx.TimeoutException:
            result["error"] = "Health check timed out"
            logger.error("[LLMClient] Health FAIL — timeout")
        except Exception as exc:
            result["error"] = str(exc)
            logger.error(f"[LLMClient] Health FAIL — {exc}")

        return result


# Kept for backward compat with backend/__init__.py
def create_llm_client(
    base_url: str = "http://localhost:1234/v1",
    model:    str = "phi-3.1-mini-4k-instruct",
) -> LLMClient:
    return LLMClient(base_url=base_url, model=model)
