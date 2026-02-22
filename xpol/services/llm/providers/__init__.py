"""LLM provider implementations."""

from .base import BaseLLMProvider
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

# Provider registry
PROVIDERS = {
    "groq": {
        "class": GroqProvider,
        "name": "Groq",
        "description": "Fast inference with open-source models",
    },
    "openai": {
        "class": OpenAIProvider,
        "name": "OpenAI",
        "description": "Industry-leading AI models",
    },
    "anthropic": {
        "class": AnthropicProvider,
        "name": "Anthropic Claude",
        "description": "Advanced AI with strong reasoning capabilities",
    },
}

def get_available_providers():
    """Get available provider configurations."""
    available = {}
    for key, config in PROVIDERS.items():
        provider_class = config["class"]
        available[key] = {
            "name": config["name"],
            "description": config["description"],
            "available": provider_class.is_available(),
            "models": provider_class.get_models(),
        }
    return available

def get_available_models(provider: str = None):
    """Get available models for a provider or all providers."""
    if provider:
        if provider not in PROVIDERS:
            raise ValueError(f"Invalid provider '{provider}'")
        return PROVIDERS[provider]["class"].get_models()
    
    # Return all models from all providers
    all_models = {}
    providers_config = get_available_providers()
    for prov, info in providers_config.items():
        for model_id, model_info in info["models"].items():
            all_models[f"{prov}:{model_id}"] = {
                **model_info,
                "provider": prov,
                "provider_name": info["name"]
            }
    return all_models

__all__ = [
    "BaseLLMProvider",
    "GroqProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "PROVIDERS",
    "get_available_providers",
    "get_available_models",
]

