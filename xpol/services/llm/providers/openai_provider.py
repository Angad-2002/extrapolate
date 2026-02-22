"""OpenAI LLM provider implementation."""

from typing import Dict, Any
from xpol.services.llm.providers.base import BaseLLMProvider

# Check if OpenAI is available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""
    
    MODELS = {
        "gpt-4o": {
            "name": "GPT-4o",
            "description": "Latest GPT-4 model with vision capabilities",
            "context_window": 128000,
            "recommended": True
        },
        "gpt-4o-mini": {
            "name": "GPT-4o Mini",
            "description": "Faster and cheaper GPT-4 variant",
            "context_window": 128000,
            "recommended": True
        },
        "gpt-4-turbo": {
            "name": "GPT-4 Turbo",
            "description": "High-performance GPT-4 model",
            "context_window": 128000,
            "recommended": False
        },
        "gpt-3.5-turbo": {
            "name": "GPT-3.5 Turbo",
            "description": "Fast and cost-effective model",
            "context_window": 16385,
            "recommended": False
        }
    }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenAI is available."""
        return OPENAI_AVAILABLE
    
    @classmethod
    def get_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get available OpenAI models."""
        return cls.MODELS
    
    def __init__(self, api_key: str, model: str):
        """Initialize OpenAI provider."""
        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI package not installed. Install with: pip install openai")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found. Set it as an environment variable or pass it to the constructor.")
        
        self.client = openai.OpenAI(api_key=api_key)
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
        """Make a call to OpenAI API."""
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
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    async def stream(
        self,
        prompt: str,
        system_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """Stream responses from OpenAI API."""
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
            raise Exception(f"Error streaming from OpenAI API: {str(e)}")

