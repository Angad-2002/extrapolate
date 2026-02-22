"""Groq LLM provider implementation."""

from typing import Dict, Any
from xpol.services.llm.providers.base import BaseLLMProvider

# Check if Groq is available
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None


class GroqProvider(BaseLLMProvider):
    """Groq provider implementation."""
    
    MODELS = {
        "llama-3.3-70b-versatile": {
            "name": "Llama 3.3 70B Versatile",
            "description": "Meta's latest versatile model - best for complex analysis",
            "context_window": 32768,
            "recommended": True
        },
        "llama-3.1-8b-instant": {
            "name": "Llama 3.1 8B Instant", 
            "description": "Fast and efficient - best for quick insights",
            "context_window": 8192,
            "recommended": False
        },
        "llama-3.1-70b-versatile": {
            "name": "Llama 3.1 70B Versatile",
            "description": "High-quality responses for complex tasks",
            "context_window": 131072,
            "recommended": True
        },
        "mixtral-8x7b-32768": {
            "name": "Mixtral 8x7B",
            "description": "Mixture of experts model with excellent reasoning",
            "context_window": 32768,
            "recommended": False
        }
    }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Groq is available."""
        return GROQ_AVAILABLE
    
    @classmethod
    def get_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get available Groq models."""
        return cls.MODELS
    
    def __init__(self, api_key: str, model: str):
        """Initialize Groq provider."""
        if not GROQ_AVAILABLE:
            raise ValueError("Groq package not installed. Install with: pip install groq")
        
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Set it as an environment variable or pass it to the constructor.")
        
        self.client = Groq(api_key=api_key)
        self.model = model
        
        # Validate model
        if model not in self.MODELS:
            print(f"Warning: Model '{model}' not in available models list. Using anyway...")
    
    def call(
        self,
        prompt: str,
        system_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Make a call to Groq API."""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error calling Groq API: {str(e)}")
    
    async def stream(
        self,
        prompt: str,
        system_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """Stream responses from Groq API."""
        try:
            stream = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"Error streaming from Groq API: {str(e)}")

