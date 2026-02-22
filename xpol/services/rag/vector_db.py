"""Vector database management and abstraction."""

import os
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, Literal, Type, Any as AnyType
from rich.console import Console

console = Console()

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

# Supported vector database types
VectorDBType = Literal["chroma", "qdrant", "faiss"]

# Import vector store implementations (optional, with fallbacks)
VECTOR_STORES: Dict[str, Type[AnyType]] = {}

# ChromaDB
try:
    try:
        from langchain_chroma import Chroma
    except ImportError:
        from langchain_community.vectorstores import Chroma
        warnings.filterwarnings("ignore", message=".*Chroma.*", category=DeprecationWarning)
    VECTOR_STORES["chroma"] = Chroma
except ImportError:
    pass

# Qdrant
try:
    try:
        from langchain_qdrant import QdrantVectorStore
        VECTOR_STORES["qdrant"] = QdrantVectorStore
    except ImportError:
        try:
            from langchain_qdrant import Qdrant
            VECTOR_STORES["qdrant"] = Qdrant
        except ImportError:
            from langchain_community.vectorstores import Qdrant
            VECTOR_STORES["qdrant"] = Qdrant
except ImportError:
    pass

# FAISS
try:
    from langchain_community.vectorstores import FAISS
    VECTOR_STORES["faiss"] = FAISS
except ImportError:
    pass


class VectorDBManager:
    """Manages vector database operations."""
    
    def __init__(
        self,
        vector_db_type: VectorDBType,
        vector_db_config: Dict[str, Any],
        storage_dir: Path,
        embeddings: AnyType
    ):
        """Initialize vector database manager.
        
        Args:
            vector_db_type: Type of vector database
            vector_db_config: Vector database configuration
            storage_dir: Storage directory for vector database
            embeddings: Embeddings model instance
        """
        self.vector_db_type = vector_db_type
        self.vector_db_config = vector_db_config
        self.storage_dir = storage_dir
        self.embeddings = embeddings
        self.vector_store = None
        
        if vector_db_type not in VECTOR_STORES:
            available = list(VECTOR_STORES.keys())
            raise ValueError(
                f"Vector database '{vector_db_type}' not available. "
                f"Available: {available}. "
                f"Install required packages: "
                f"chroma: pip install langchain-chroma, "
                f"qdrant: pip install langchain-qdrant qdrant-client, "
                f"faiss: pip install faiss-cpu"
            )
    
    def create_vector_store(self) -> AnyType:
        """Create and return a vector store instance.
        
        Returns:
            Vector store instance
        """
        VectorStoreClass = VECTOR_STORES[self.vector_db_type]
        
        if self.vector_db_type == "chroma":
            chroma_path = str(self.storage_dir / "chroma_db")
            return VectorStoreClass(
                persist_directory=chroma_path,
                embedding_function=self.embeddings,
                collection_name="xpol_documents"
            )
        
        elif self.vector_db_type == "qdrant":
            collection_name = self.vector_db_config.get("collection_name", "xpol_documents")
            url = self.vector_db_config.get("url", os.getenv("QDRANT_URL", "http://localhost:6333"))
            api_key = self.vector_db_config.get("api_key", os.getenv("QDRANT_API_KEY"))
            
            # Check if using new API (QdrantVectorStore)
            try:
                from langchain_qdrant import QdrantVectorStore
                using_new_api = VectorStoreClass == QdrantVectorStore
            except ImportError:
                using_new_api = False
            
            # Helper function to try creating Qdrant store and handle missing collection
            def try_create_qdrant(**kwargs):
                try:
                    return VectorStoreClass(**kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "not found" in error_msg or "collection" in error_msg:
                        # Collection doesn't exist yet - return None, will be created on first upload
                        console.print(f"[dim]Qdrant collection '{collection_name}' doesn't exist yet. It will be created when you upload your first document.[/]")
                        return None
                    # Re-raise other errors
                    raise
            
            # For local Qdrant
            if url.startswith("file://") or not url.startswith("http"):
                path = url.replace("file://", "") if url.startswith("file://") else url
                if not path:
                    path = str(self.storage_dir / "qdrant_db")
                
                if using_new_api:
                    # New API: Use QdrantClient with path
                    from qdrant_client import QdrantClient
                    client = QdrantClient(path=path)
                    return try_create_qdrant(
                        client=client,
                        collection_name=collection_name,
                        embedding=self.embeddings
                    )
                else:
                    # Old API: Try different initialization methods
                    try:
                        from qdrant_client import QdrantClient
                        client = QdrantClient(path=path)
                        return try_create_qdrant(
                            client=client,
                            collection_name=collection_name,
                            embeddings=self.embeddings
                        )
                    except (TypeError, AttributeError):
                        # If client parameter doesn't work, try location
                        try:
                            return try_create_qdrant(
                                location=path,
                                collection_name=collection_name,
                                embeddings=self.embeddings
                            )
                        except TypeError:
                            # Last resort: try with url pointing to local path
                            return try_create_qdrant(
                                url=f"file://{path}",
                                collection_name=collection_name,
                                embeddings=self.embeddings
                            )
            else:
                # Remote Qdrant
                if using_new_api:
                    from qdrant_client import QdrantClient
                    client = QdrantClient(url=url, api_key=api_key) if api_key else QdrantClient(url=url)
                    return try_create_qdrant(
                        client=client,
                        collection_name=collection_name,
                        embedding=self.embeddings
                    )
                else:
                    # Old API
                    if api_key:
                        return try_create_qdrant(
                            url=url,
                            collection_name=collection_name,
                            embeddings=self.embeddings,
                            api_key=api_key
                        )
                    else:
                        return try_create_qdrant(
                            url=url,
                            collection_name=collection_name,
                            embeddings=self.embeddings
                        )
        
        elif self.vector_db_type == "faiss":
            faiss_path = str(self.storage_dir / "faiss_db")
            # Try to load existing index, otherwise return None (will be created on first upload)
            index_path = Path(faiss_path)
            if index_path.exists() and (index_path / "index.faiss").exists():
                return VectorStoreClass.load_local(
                    folder_path=faiss_path,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                # Return None - will be created when first document is uploaded
                return None
        
        else:
            raise ValueError(f"Unsupported vector database type: {self.vector_db_type}")
    
    def persist(self) -> None:
        """Persist vector store to disk (if applicable)."""
        if self.vector_store is None:
            return
        
        if self.vector_db_type == "chroma":
            # ChromaDB auto-persists when using persist_directory, no explicit persist() needed
            pass
        elif self.vector_db_type == "faiss":
            faiss_path = str(self.storage_dir / "faiss_db")
            self.vector_store.save_local(faiss_path)
        # Qdrant persists automatically
    
    @staticmethod
    def get_available_stores() -> list[str]:
        """Get list of available vector store types.
        
        Returns:
            List of available vector store type names
        """
        return list(VECTOR_STORES.keys())
    
    def get_info(self) -> Dict[str, Any]:
        """Get vector database information.
        
        Returns:
            Dictionary with vector DB information
        """
        return {
            "type": self.vector_db_type,
            "config": self.vector_db_config.copy(),
            "available_stores": self.get_available_stores(),
            "is_available": self.vector_db_type in VECTOR_STORES
        }
