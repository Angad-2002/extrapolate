"""Storage management for RAG documents and metadata."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

console = Console()


class RAGStorageManager:
    """Manages document storage and metadata persistence."""
    
    def __init__(self, storage_dir: Path):
        """Initialize storage manager.
        
        Args:
            storage_dir: Base storage directory
        """
        self.storage_dir = Path(storage_dir)
        self.documents_dir = self.storage_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_dir / "documents_metadata.json"
        self._metadata: List[Dict[str, Any]] = []
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load document metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self._metadata = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load metadata: {e}[/]")
                self._metadata = []
        else:
            self._metadata = []
    
    def _save_metadata(self) -> None:
        """Save document metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save metadata: {e}[/]")
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """Get list of all documents.
        
        Returns:
            List of document metadata dictionaries
        """
        return self._metadata.copy()
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID.
        
        Args:
            document_id: Document ID to retrieve
            
        Returns:
            Document metadata dictionary or None if not found
        """
        return next((d for d in self._metadata if d["id"] == document_id), None)
    
    def add_document(self, document_metadata: Dict[str, Any]) -> None:
        """Add a new document to metadata.
        
        Args:
            document_metadata: Document metadata dictionary
        """
        self._metadata.append(document_metadata)
        self._save_metadata()
    
    def remove_document(self, document_id: str) -> bool:
        """Remove a document from metadata.
        
        Args:
            document_id: Document ID to remove
            
        Returns:
            True if document was found and removed, False otherwise
        """
        original_count = len(self._metadata)
        self._metadata = [d for d in self._metadata if d["id"] != document_id]
        
        if len(self._metadata) < original_count:
            self._save_metadata()
            return True
        return False
    
    def get_document_path(self, stored_filename: str) -> Path:
        """Get full path to a stored document file.
        
        Args:
            stored_filename: Stored filename
            
        Returns:
            Full path to document file
        """
        return self.documents_dir / stored_filename
    
    def get_document_details(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Dictionary with document details or None if not found
        """
        doc_info = self.get_document(document_id)
        if not doc_info:
            return None
        
        doc_path = self.get_document_path(doc_info.get("stored_filename", ""))
        file_size = doc_path.stat().st_size if doc_path.exists() else 0
        
        return {
            "id": doc_info.get("id"),
            "filename": doc_info.get("filename"),
            "stored_filename": doc_info.get("stored_filename"),
            "uploaded_at": doc_info.get("uploaded_at"),
            "chunks": doc_info.get("chunks", 0),
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_exists": doc_path.exists(),
            "file_path": str(doc_path) if doc_path.exists() else None
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        total_docs = len(self._metadata)
        total_chunks = sum(doc.get("chunks", 0) for doc in self._metadata)
        
        total_size = 0
        for doc in self._metadata:
            doc_path = self.get_document_path(doc.get("stored_filename", ""))
            if doc_path.exists():
                total_size += doc_path.stat().st_size
        
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_directory": str(self.storage_dir)
        }
