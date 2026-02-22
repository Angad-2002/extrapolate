"""Configuration management for RAG service."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Literal
from rich.console import Console

console = Console()

# Supported vector database types
VectorDBType = Literal["chroma", "qdrant", "faiss"]


class RAGConfigManager:
    """Manages RAG service configuration."""
    
    def __init__(self, storage_dir: Path):
        """Initialize configuration manager.
        
        Args:
            storage_dir: Directory where configuration is stored
        """
        self.storage_dir = Path(storage_dir)
        self.config_file = self.storage_dir / "vector_db_config.json"
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load vector DB config: {e}[/]")
                return {}
        return {}
    
    def save(
        self, 
        vector_db_type: VectorDBType,
        vector_db_config: Dict[str, Any]
    ) -> bool:
        """Save configuration to file.
        
        Args:
            vector_db_type: Vector database type
            vector_db_config: Vector database configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = {
                "vector_db_type": vector_db_type,
                "vector_db_config": vector_db_config
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save vector DB config: {e}[/]")
            return False
    
    def get_vector_db_type(
        self, 
        override: Optional[VectorDBType] = None
    ) -> VectorDBType:
        """Get vector database type with priority handling.
        
        Priority: 1) override, 2) saved config, 3) environment variable, 4) default
        
        Args:
            override: Override value (highest priority)
            
        Returns:
            Vector database type
        """
        if override:
            return override.lower()  # type: ignore
        
        saved_config = self.load()
        saved_type = saved_config.get("vector_db_type")
        
        if saved_type:
            return saved_type.lower()  # type: ignore
        
        env_type = os.getenv("RAG_VECTOR_DB", "chroma")
        return env_type.lower()  # type: ignore
    
    def get_vector_db_config(
        self,
        override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get vector database configuration.
        
        Priority: 1) override, 2) saved config, 3) empty dict
        
        Args:
            override: Override configuration (highest priority)
            
        Returns:
            Vector database configuration dictionary
        """
        if override is not None:
            return override
        
        saved_config = self.load()
        return saved_config.get("vector_db_config", {})

    # Default RAG settings (chunking and retrieval)
    RAG_SETTINGS_DEFAULTS: Dict[str, Any] = {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "retriever_k": 5,
    }

    RAG_SETTINGS_LIMITS: Dict[str, tuple] = {
        "chunk_size": (256, 2000),
        "chunk_overlap": (0, 500),
        "retriever_k": (1, 50),
    }

    def get_rag_settings(self) -> Dict[str, Any]:
        """Get RAG settings (chunk size, overlap, retriever k) with defaults.

        Returns:
            Dictionary with chunk_size, chunk_overlap, retriever_k.
            Missing or invalid values are replaced with defaults.
        """
        settings_file = self.storage_dir / "rag_settings.json"
        out = dict(self.RAG_SETTINGS_DEFAULTS)
        if settings_file.exists():
            try:
                with open(settings_file, "r") as f:
                    data = json.load(f)
                for key in self.RAG_SETTINGS_DEFAULTS:
                    if key in data and data[key] is not None:
                        low, high = self.RAG_SETTINGS_LIMITS[key]
                        if key == "chunk_overlap":
                            # overlap must be < chunk_size
                            cap = out.get("chunk_size", data.get("chunk_size", 1000))
                            val = max(low, min(high, int(data[key])))
                            out[key] = min(val, cap - 1)
                        else:
                            out[key] = max(low, min(high, int(data[key])))
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load RAG settings: {e}[/]")
        return out

    def save_rag_settings(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        retriever_k: Optional[int] = None,
    ) -> bool:
        """Save RAG settings to file. Omitted values are left unchanged.

        Args:
            chunk_size: Chunk size in characters (256-2000).
            chunk_overlap: Overlap between chunks (0-500, must be < chunk_size).
            retriever_k: Number of chunks to retrieve (1-50).

        Returns:
            True if successful, False otherwise.
        """
        settings_file = self.storage_dir / "rag_settings.json"
        current = self.get_rag_settings()
        if chunk_size is not None:
            low, high = self.RAG_SETTINGS_LIMITS["chunk_size"]
            current["chunk_size"] = max(low, min(high, int(chunk_size)))
        if chunk_overlap is not None:
            low, high = self.RAG_SETTINGS_LIMITS["chunk_overlap"]
            val = max(low, min(high, int(chunk_overlap)))
            current["chunk_overlap"] = min(val, current["chunk_size"] - 1)
        if retriever_k is not None:
            low, high = self.RAG_SETTINGS_LIMITS["retriever_k"]
            current["retriever_k"] = max(low, min(high, int(retriever_k)))
        try:
            with open(settings_file, "w") as f:
                json.dump(current, f, indent=2)
            return True
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save RAG settings: {e}[/]")
            return False
