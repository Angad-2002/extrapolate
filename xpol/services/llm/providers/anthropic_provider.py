"""Anthropic LLM provider implementation."""

from typing import Dict, Any
from xpol.services.llm.providers.base import BaseLLMProvider

# Check if Anthropic is available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider implementation."""
    
    MODELS = {
        "claude-3-5-sonnet-20241022": {
            "name": "Claude 3.5 Sonnet",
            "description": "Latest Claude model with enhanced capabilities",
            "context_window": 200000,
            "recommended": True
        },
        "claude-3-5-haiku-20241022": {
            "name": "Claude 3.5 Haiku",
            "description": "Fast and efficient Claude model",
            "context_window": 200000,
            "recommended": True
        },
        "claude-3-opus-20240229": {
            "name": "Claude 3 Opus",
            "description": "Most capable Claude model",
            "context_window": 200000,
            "recommended": False
        },
        "claude-3-sonnet-20240229": {
            "name": "Claude 3 Sonnet",
            "description": "Balanced performance and speed",
            "context_window": 200000,
            "recommended": False
        }
    }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Anthropic is available."""
        return ANTHROPIC_AVAILABLE
    
    @classmethod
    def get_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get available Anthropic models."""
        return cls.MODELS
    
    def __init__(self, api_key: str, model: str):
        """Initialize Anthropic provider."""
        if not ANTHROPIC_AVAILABLE:
            raise ValueError("Anthropic package not installed. Install with: pip install anthropic")
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it as an environment variable or pass it to the constructor.")
        
        self.client = anthropic.Anthropic(api_key=api_key)
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
        """Make a call to Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Error calling Anthropic API: {str(e)}")
    
    async def stream(
        self,
        prompt: str,
        system_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """Stream responses from Anthropic API."""
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            ) as stream:
                for text_event in stream.text_stream:
                    yield text_event
        except Exception as e:
            raise Exception(f"Error streaming from Anthropic API: {str(e)}")

