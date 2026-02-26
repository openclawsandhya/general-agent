"""
LLM Client for connecting to LM Studio API.
"""

from typing import Optional, List
import requests
import json
from .utils.logger import get_logger


logger = get_logger(__name__)


class LLMClient:
    """Client for communicating with LM Studio API (OpenAI-compatible)."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "mistral-7b-instruct",
        timeout: int = 60,
    ):
        """
        Initialize LLM client.
        
        Args:
            base_url: Base URL for LM Studio API
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.api_key = "not-needed"  # LM Studio doesn't require API key for local
        
        logger.info(f"Initialized LLM client: {base_url}, model: {model}")
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System context prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            url = f"{self.base_url}/chat/completions"
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.95,
            }
            
            logger.debug(f"Sending request to {url} with payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract response from OpenAI-compatible format
            generated_text = result["choices"][0]["message"]["content"].strip()
            
            logger.debug(f"Received response: {generated_text[:100]}...")
            
            return generated_text
            
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Failed to connect to LM Studio at {self.base_url}. "
                "Make sure LM Studio is running."
            )
            raise
        except requests.exceptions.Timeout:
            logger.error(f"LLM request timed out after {self.timeout} seconds")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            raise
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if LM Studio is running and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            logger.info("LLM health check passed")
            return True
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False


# Convenience function
def create_llm_client(
    base_url: str = "http://localhost:1234/v1",
    model: str = "mistral-7b-instruct"
) -> LLMClient:
    """Factory function to create LLM client."""
    return LLMClient(base_url=base_url, model=model)
