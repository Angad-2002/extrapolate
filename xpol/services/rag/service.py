"""RAG (Retrieval Augmented Generation) service for document-based chat using LangChain."""

import os
import warnings
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime
import shutil
from rich.console import Console
from alive_progress import alive_bar

from xpol.services.rag.config import RAGConfigManager, VectorDBType
from xpol.services.rag.storage import RAGStorageManager
from xpol.services.rag.vector_db import VectorDBManager

console = Console()

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

# Import LangChain dependencies (required)
try:
    from langchain_community.document_loaders import PyPDFLoader
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        # Fallback for older langchain versions
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    # Try new packages first, fall back to deprecated ones
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        warnings.filterwarnings("ignore", message=".*HuggingFaceEmbeddings.*", category=DeprecationWarning)
    
    try:
        # Try langchain-classic first (for langchain 1.x)
        from langchain_classic.chains import RetrievalQA
        from langchain_core.prompts import PromptTemplate
        from langchain_core.messages import HumanMessage
    except ImportError:
        # Fallback to old langchain API (for langchain < 1.0)
        from langchain.chains import RetrievalQA
        from langchain.prompts import PromptTemplate
        try:
            from langchain_core.messages import HumanMessage
        except ImportError:
            HumanMessage = None  # type: ignore
except ImportError as e:
    raise ImportError(
        "LangChain dependencies are required for RAG functionality. "
        "Please install: pip install langchain langchain-community langchain-huggingface"
    ) from e

# Import LangChain LLM providers
LANGCHAIN_LLM_PROVIDERS = {}
try:
    from langchain_groq import ChatGroq
    LANGCHAIN_LLM_PROVIDERS["groq"] = ChatGroq
except ImportError:
    pass

try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_LLM_PROVIDERS["openai"] = ChatOpenAI
except ImportError:
    pass

try:
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_LLM_PROVIDERS["anthropic"] = ChatAnthropic
except ImportError:
    pass


class RAGService:
    """Service for RAG-based document Q&A using LangChain."""
    
    def __init__(
        self, 
        storage_dir: Optional[Path] = None,
        vector_db_type: Optional[VectorDBType] = None,
        vector_db_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize RAG service with LangChain.
        
        Args:
            storage_dir: Directory to store vector database and documents
            vector_db_type: Type of vector database to use ("chroma", "qdrant", "faiss")
                          Defaults to environment variable RAG_VECTOR_DB or "chroma"
            vector_db_config: Optional configuration dict for vector database
                            (e.g., {"url": "http://localhost:6333"} for Qdrant)
        """
        # Initialize storage directory
        if storage_dir is None:
            storage_dir = Path.home() / ".xpol" / "rag"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize modular components
        self.config_manager = RAGConfigManager(self.storage_dir)
        self.storage_manager = RAGStorageManager(self.storage_dir)
        
        # Get vector database configuration
        self.vector_db_type = self.config_manager.get_vector_db_type(vector_db_type)
        self.vector_db_config = self.config_manager.get_vector_db_config(vector_db_config)
        
        # RAG settings (chunk size, overlap, retriever k) - loaded in _initialize_langchain
        self.retriever_k = 5
        
        # Initialize LangChain components
        self.embeddings = None
        self.text_splitter = None
        self.qa_chain = None
        self.llm = None
        
        # Track current LLM configuration to detect changes
        self._current_provider = None
        self._current_model = None
        self._current_api_key = None
        
        # Initialize vector database manager and LangChain
        self._initialize_langchain()
    
    def _initialize_langchain(self):
        """Initialize LangChain components."""
        try:
            # Load RAG settings (chunk size, overlap, retriever k)
            rag_settings = self.config_manager.get_rag_settings()
            self.retriever_k = rag_settings["retriever_k"]
            
            # Initialize embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Initialize text splitter from configurable settings
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=rag_settings["chunk_size"],
                chunk_overlap=rag_settings["chunk_overlap"],
                length_function=len,
            )
            
            # Initialize vector database manager
            self.vector_db_manager = VectorDBManager(
                vector_db_type=self.vector_db_type,
                vector_db_config=self.vector_db_config,
                storage_dir=self.storage_dir,
                embeddings=self.embeddings
            )
            
            # Create vector store
            self.vector_store = self.vector_db_manager.create_vector_store()
            
            db_name = self.vector_db_type.upper()
            console.print(f"[dim]Initialized LangChain RAG service with {db_name}[/]")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LangChain RAG service: {e}") from e
    
    def _initialize_llm(self, provider: str, model: str, api_key: str):
        """Initialize LangChain LLM for QA chain.
        
        Args:
            provider: LLM provider name (groq, openai, anthropic)
            model: Model name
            api_key: API key for the provider
        """
        if provider not in LANGCHAIN_LLM_PROVIDERS:
            raise ValueError(
                f"LangChain provider '{provider}' not available. "
                f"Available: {list(LANGCHAIN_LLM_PROVIDERS.keys())}. "
                f"Install: pip install langchain-{provider}"
            )
        
        try:
            llm_class = LANGCHAIN_LLM_PROVIDERS[provider]
            
            # Initialize LLM with provider-specific parameters
            # Try 'model' first (newer API), fall back to 'model_name' (older API)
            if provider == "groq":
                try:
                    self.llm = llm_class(
                        model=model,
                        groq_api_key=api_key,
                        temperature=0.6
                    )
                except TypeError:
                    # Fall back to model_name for older versions
                    self.llm = llm_class(
                        model_name=model,
                        groq_api_key=api_key,
                        temperature=0.6
                    )
            elif provider == "openai":
                try:
                    self.llm = llm_class(
                        model=model,
                        openai_api_key=api_key,
                        temperature=0.6
                    )
                except TypeError:
                    self.llm = llm_class(
                        model_name=model,
                        openai_api_key=api_key,
                        temperature=0.6
                    )
            elif provider == "anthropic":
                try:
                    self.llm = llm_class(
                        model=model,
                        anthropic_api_key=api_key,
                        temperature=0.6
                    )
                except TypeError:
                    self.llm = llm_class(
                        model_name=model,
                        anthropic_api_key=api_key,
                        temperature=0.6
                    )
            
            # Create QA chain
            prompt_template = """Use the following pieces of context from uploaded documents to answer the user's question. 
If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {question}

Provide a clear, accurate answer based on the context. Use markdown formatting for better readability when helpful."""
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Ensure vector store is initialized (for FAISS)
            if self.vector_store is None:
                raise RuntimeError(
                    "Vector store not initialized. Please upload at least one document first."
                )
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(
                    search_kwargs={"k": self.retriever_k}
                ),
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LangChain LLM: {e}") from e
    
    def get_vector_db_info(self) -> Dict[str, Any]:
        """Get current vector database information.
        
        Returns:
            Dictionary with vector DB type, config, and availability status
        """
        return self.vector_db_manager.get_info()
    
    def get_rag_settings(self) -> Dict[str, Any]:
        """Get current RAG settings (chunk size, overlap, retriever k)."""
        return self.config_manager.get_rag_settings()
    
    def update_rag_settings(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        retriever_k: Optional[int] = None,
    ) -> bool:
        """Save RAG settings. Reload the RAG service for changes to take effect."""
        return self.config_manager.save_rag_settings(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            retriever_k=retriever_k,
        )
    
    def update_vector_db_config(
        self, 
        vector_db_type: Optional[VectorDBType] = None,
        vector_db_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update vector database configuration.
        
        Args:
            vector_db_type: New vector database type
            vector_db_config: New vector database configuration
            
        Returns:
            True if successful, False otherwise
        """
        if vector_db_type is not None:
            # Validate vector DB type
            from xpol.services.rag.vector_db import VectorDBManager
            available = VectorDBManager.get_available_stores()
            if vector_db_type not in available:
                raise ValueError(
                    f"Vector database '{vector_db_type}' not available. "
                    f"Available: {available}."
                )
            self.vector_db_type = vector_db_type
        
        if vector_db_config is not None:
            self.vector_db_config.update(vector_db_config)
        
        # Save configuration
        return self.config_manager.save(self.vector_db_type, self.vector_db_config)
    
    def upload_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Upload and process a PDF file using LangChain.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with upload status and document info
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return {"success": False, "error": f"File not found: {pdf_path}"}
        
        if pdf_path.suffix.lower() != '.pdf':
            return {"success": False, "error": "Only PDF files are supported"}
        
        try:
            # Use alive-progress with 6 steps total
            with alive_bar(6, title="Processing PDF") as bar:
                # Step 1: Copy PDF to documents directory
                bar.text("Copying file...")
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                doc_filename = f"{pdf_path.stem}_{timestamp}.pdf"
                doc_path = self.storage_manager.get_document_path(doc_filename)
                shutil.copy2(pdf_path, doc_path)
                bar()
                
                # Step 2: Load PDF using LangChain
                bar.text("Loading PDF...")
                loader = PyPDFLoader(str(doc_path))
                documents = loader.load()
                bar()
                
                # Step 3: Split documents
                bar.text("Splitting text into chunks...")
                chunks = self.text_splitter.split_documents(documents)
                bar()
                
                if not chunks:
                    doc_path.unlink()
                    return {"success": False, "error": "Could not extract text from PDF"}
                
                # Step 4: Add metadata to chunks
                bar.text("Adding metadata...")
                document_id = f"doc_{timestamp}"
                for chunk in chunks:
                    chunk.metadata["document_id"] = document_id
                    chunk.metadata["source"] = str(doc_path)
                    chunk.metadata["filename"] = pdf_path.name
                bar()
                
                # Step 5: Add to vector store (create if needed for FAISS or Qdrant)
                bar.text("Creating embeddings and adding to vector store...")
                if self.vector_store is None:
                    # Initialize vector store with first document
                    from xpol.services.rag.vector_db import VECTOR_STORES
                    VectorStoreClass = VECTOR_STORES[self.vector_db_type]
                    
                    if self.vector_db_type == "faiss":
                        self.vector_store = VectorStoreClass.from_documents(
                            chunks,
                            self.embeddings
                        )
                    elif self.vector_db_type == "qdrant":
                        # Create Qdrant collection using from_documents
                        collection_name = self.vector_db_config.get("collection_name", "xpol_documents")
                        url = self.vector_db_config.get("url", os.getenv("QDRANT_URL", ""))
                        api_key = self.vector_db_config.get("api_key", os.getenv("QDRANT_API_KEY"))
                        
                        # Check if using new API (QdrantVectorStore)
                        try:
                            from langchain_qdrant import QdrantVectorStore
                            using_new_api = VectorStoreClass == QdrantVectorStore
                        except ImportError:
                            using_new_api = False
                        
                        if using_new_api:
                            # New API (QdrantVectorStore) - pass connection parameters directly
                            if url.startswith("file://") or not url.startswith("http"):
                                path = url.replace("file://", "") if url.startswith("file://") else url
                                if not path:
                                    path = str(self.storage_dir / "qdrant_db")
                                self.vector_store = VectorStoreClass.from_documents(
                                    chunks,
                                    embedding=self.embeddings,
                                    path=path,
                                    collection_name=collection_name
                                )
                            else:
                                # Remote Qdrant - use url and api_key parameters
                                if api_key:
                                    self.vector_store = VectorStoreClass.from_documents(
                                        chunks,
                                        embedding=self.embeddings,
                                        url=url,
                                        api_key=api_key,
                                        collection_name=collection_name
                                    )
                                else:
                                    self.vector_store = VectorStoreClass.from_documents(
                                        chunks,
                                        embedding=self.embeddings,
                                        url=url,
                                        collection_name=collection_name
                                    )
                        else:
                            # Old API uses 'embeddings' parameter and accepts a client object
                            from qdrant_client import QdrantClient
                            if url.startswith("file://") or not url.startswith("http"):
                                path = url.replace("file://", "") if url.startswith("file://") else url
                                if not path:
                                    path = str(self.storage_dir / "qdrant_db")
                                client = QdrantClient(path=path)
                            else:
                                client = QdrantClient(url=url, api_key=api_key) if api_key else QdrantClient(url=url)
                            
                            self.vector_store = VectorStoreClass.from_documents(
                                chunks,
                                embeddings=self.embeddings,
                                client=client,
                                collection_name=collection_name
                            )
                else:
                    self.vector_store.add_documents(chunks)
                
                bar()
                
                # Step 6: Persist vector store
                bar.text("Saving to database...")
                self.vector_db_manager.vector_store = self.vector_store
                self.vector_db_manager.persist()
                bar()
            
            # Save metadata using storage manager
            doc_metadata = {
                "id": document_id,
                "filename": pdf_path.name,
                "stored_filename": doc_filename,
                "uploaded_at": datetime.now().isoformat(),
                "chunks": len(chunks)
            }
            self.storage_manager.add_document(doc_metadata)
            
            return {
                "success": True,
                "document_id": document_id,
                "filename": pdf_path.name,
                "chunks": len(chunks),
                "metadata": doc_metadata
            }
        except Exception as e:
            return {"success": False, "error": f"Error processing PDF: {str(e)}"}
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for relevant document chunks using LangChain.
        
        Args:
            query: Search query
            top_k: Number of results to return (default: configured retriever_k)
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            if self.vector_store is None:
                return []
            
            k = top_k if top_k is not None else self.retriever_k
            retriever = self.vector_store.as_retriever(search_kwargs={"k": k})
            docs = retriever.get_relevant_documents(query)
            
            chunks = []
            for doc in docs:
                chunks.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata or {},
                    "distance": 0.0  # LangChain doesn't return distance by default
                })
            return chunks
        except Exception as e:
            console.print(f"[yellow]Error searching: {e}[/]")
            return []
    
    def chat(self, query: str, provider: str, model: str, api_key: str) -> Dict[str, Any]:
        """Chat with documents using LangChain QA chain.
        
        Args:
            query: User question
            provider: LLM provider (groq, openai, anthropic)
            model: Model name
            api_key: API key for the provider
            
        Returns:
            Dictionary with answer and sources
        """
        try:
            # Check if we need to re-initialize LLM (if not initialized or config changed)
            needs_reinit = (
                not self.qa_chain or
                self._current_provider != provider or
                self._current_model != model or
                self._current_api_key != api_key
            )
            
            if needs_reinit:
                self._initialize_llm(provider, model, api_key)
                # Update tracked configuration
                self._current_provider = provider
                self._current_model = model
                self._current_api_key = api_key
            
            # Ensure vector store is initialized (for FAISS)
            if self.vector_store is None:
                return {
                    "success": False,
                    "error": "No documents uploaded yet. Please upload documents first."
                }
            
            # Run QA chain
            result = self.qa_chain.invoke({"query": query})
            
            # Extract sources
            sources = []
            if result.get("source_documents"):
                for doc in result["source_documents"]:
                    sources.append({
                        "text": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "metadata": doc.metadata or {}
                    })
            
            return {
                "success": True,
                "answer": result.get("result", ""),
                "sources": sources
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error in LangChain chat: {str(e)}"
            }
    
    async def stream_chat(
        self, query: str, provider: str, model: str, api_key: str
    ) -> AsyncIterator[str]:
        """Stream chat with documents using RAG (yields answer text chunks).
        
        Args:
            query: User question
            provider: LLM provider (groq, openai, anthropic)
            model: Model name
            api_key: API key for the provider
            
        Yields:
            Text chunks of the answer as they are generated
        """
        if HumanMessage is None:
            raise RuntimeError(
                "Streaming requires langchain_core. Install: pip install langchain-core"
            )
        try:
            needs_reinit = (
                not self.qa_chain
                or self._current_provider != provider
                or self._current_model != model
                or self._current_api_key != api_key
            )
            if needs_reinit:
                self._initialize_llm(provider, model, api_key)
                self._current_provider = provider
                self._current_model = model
                self._current_api_key = api_key
            
            if self.vector_store is None:
                raise ValueError(
                    "No documents uploaded yet. Please upload documents first."
                )
            
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": self.retriever_k}
            )
            docs = retriever.invoke(query)
            context = "\n\n".join(doc.page_content for doc in docs)
            
            prompt_template = """Use the following pieces of context from uploaded documents to answer the user's question. 
If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {question}

Provide a clear, accurate answer based on the context. Use markdown formatting for better readability when helpful."""
            prompt = prompt_template.format(context=context, question=query)
            
            async for chunk in self.llm.astream([HumanMessage(content=prompt)]):
                content = getattr(chunk, "content", None) or ""
                if isinstance(content, str) and content:
                    yield content
        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(f"Error streaming RAG chat: {e}") from e
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """Get list of uploaded documents.
        
        Returns:
            List of document metadata
        """
        return self.storage_manager.get_documents()
    
    def get_document_details(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific document.
        
        Args:
            document_id: Document ID to get details for
            
        Returns:
            Dictionary with document details or None if not found
        """
        return self.storage_manager.get_document_details(document_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about the RAG system.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.storage_manager.get_statistics()
        db_info = self.get_vector_db_info()
        
        stats.update({
            "vector_db_type": db_info["type"],
            "vector_db_available": db_info["is_available"]
        })
        
        return stats
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful
        """
        try:
            # Get document info before deletion
            doc_info = self.storage_manager.get_document(document_id)
            
            # Remove from metadata using storage manager
            if not self.storage_manager.remove_document(document_id):
                return False
            
            # Remove from vector store based on type
            try:
                if self.vector_db_type == "chroma":
                    # ChromaDB: Use direct client for metadata-based deletion
                    from chromadb import PersistentClient
                    from chromadb.config import Settings
                    
                    chroma_path = str(self.storage_dir / "chroma_db")
                    chroma_client = PersistentClient(
                        path=chroma_path,
                        settings=Settings(anonymized_telemetry=False)
                    )
                    collection = chroma_client.get_collection("xpol_documents")
                    
                    # Get all IDs for this document
                    results = collection.get(
                        where={"document_id": document_id}
                    )
                    if results['ids']:
                        collection.delete(ids=results['ids'])
                
                elif self.vector_db_type == "qdrant":
                    # Qdrant: Use filter to delete by metadata
                    try:
                        # Get all document IDs with this document_id in metadata
                        retriever = self.vector_store.as_retriever(search_kwargs={"k": 1000})
                        # Search for documents with this document_id
                        from qdrant_client import QdrantClient
                        from qdrant_client.models import Filter, FieldCondition, MatchValue
                        
                        url = self.vector_db_config.get("url", os.getenv("QDRANT_URL", "http://localhost:6333"))
                        api_key = self.vector_db_config.get("api_key", os.getenv("QDRANT_API_KEY"))
                        collection_name = self.vector_db_config.get("collection_name", "xpol_documents")
                        
                        if url.startswith("file://") or not url.startswith("http"):
                            path = url.replace("file://", "") if url.startswith("file://") else url
                            if not path:
                                path = str(self.storage_dir / "qdrant_db")
                            client = QdrantClient(path=path)
                        else:
                            client = QdrantClient(url=url, api_key=api_key)
                        
                        # Delete points with matching document_id
                        client.delete(
                            collection_name=collection_name,
                            points_selector=Filter(
                                must=[
                                    FieldCondition(
                                        key="document_id",
                                        match=MatchValue(value=document_id)
                                    )
                                ]
                            )
                        )
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not delete from Qdrant: {e}[/]")
                
                elif self.vector_db_type == "faiss":
                    # FAISS doesn't support deletion, so we need to rebuild the index
                    # This is inefficient but necessary for FAISS
                    console.print("[yellow]FAISS doesn't support deletion. Rebuilding index...[/]")
                    
                    # Get all remaining documents from metadata
                    remaining_docs = []
                    for doc_meta in self.storage_manager.get_documents():
                        doc_path = self.storage_manager.get_document_path(doc_meta.get("stored_filename", ""))
                        if doc_path.exists():
                                try:
                                    loader = PyPDFLoader(str(doc_path))
                                    docs = loader.load()
                                    chunks = self.text_splitter.split_documents(docs)
                                    for chunk in chunks:
                                        chunk.metadata["document_id"] = doc_meta["id"]
                                        chunk.metadata["source"] = str(doc_path)
                                        chunk.metadata["filename"] = doc_meta.get("filename", "")
                                    remaining_docs.extend(chunks)
                                except Exception as e:
                                    console.print(f"[yellow]Warning: Could not reload document {doc_meta['id']}: {e}[/]")
                    
                    # Rebuild FAISS index
                    if remaining_docs:
                        from xpol.services.rag.vector_db import VECTOR_STORES
                        faiss_path = str(self.storage_dir / "faiss_db")
                        FAISSClass = VECTOR_STORES["faiss"]
                        self.vector_store = FAISSClass.from_documents(
                            remaining_docs,
                            self.embeddings
                        )
                        self.vector_store.save_local(faiss_path)
                    else:
                        # No documents left, set to None (will be recreated on next upload)
                        self.vector_store = None
                        # Remove FAISS directory
                        faiss_path = Path(self.storage_dir / "faiss_db")
                        if faiss_path.exists():
                            shutil.rmtree(faiss_path)
                
            except Exception as e:
                console.print(f"[yellow]Warning: Could not delete from vector store: {e}[/]")
            
            # Remove file
            if doc_info and "stored_filename" in doc_info:
                doc_path = self.storage_manager.get_document_path(doc_info["stored_filename"])
                if doc_path.exists():
                    doc_path.unlink()
            
            return True
        except Exception as e:
            console.print(f"[yellow]Error deleting document: {e}[/]")
            return False
