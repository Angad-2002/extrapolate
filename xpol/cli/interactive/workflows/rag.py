"""RAG (Retrieval Augmented Generation) interactive workflows."""

from pathlib import Path
from typing import Optional
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.table import Table
from xpol.services.rag.service import RAGService
from xpol.cli.ai.service import get_llm_service

console = Console()

# Global RAG service instance
_rag_service: Optional[RAGService] = None

def get_rag_service(reload: bool = False) -> Optional[RAGService]:
    """Get or create RAG service instance.
    
    Args:
        reload: If True, reload the service even if it exists
        
    Returns:
        RAGService instance or None if initialization fails
    """
    global _rag_service
    if _rag_service is None or reload:
        try:
            _rag_service = RAGService()
        except Exception as e:
            console.print(f"[red]Failed to initialize RAG service: {e}[/]")
            return None
    return _rag_service

def refresh_rag_service() -> Optional[RAGService]:
    """Refresh the RAG service instance (reload with new config)."""
    return get_rag_service(reload=True)

def run_rag_chat_interactive() -> None:
    """Run RAG-based chat with uploaded documents using TUI."""
    from xpol.cli.tui.chat_app import run_chat_app
    
    llm_service = get_llm_service()
    if not llm_service:
        console.print("[red]AI service not available. Please configure AI settings first.[/]")
        return
    
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available. Install required packages for your vector database:[/]")
        console.print("[yellow]  ChromaDB: pip install langchain-chroma[/]")
        console.print("[yellow]  Qdrant: pip install langchain-qdrant qdrant-client[/]")
        console.print("[yellow]  FAISS: pip install faiss-cpu[/]")
        return
    
    # Check if any documents are uploaded
    documents = rag_service.get_documents()
    if not documents:
        console.print("[yellow]No documents uploaded yet. Please upload PDFs first.[/]")
        return
    
    console.print("[bold cyan]Starting Document Chat TUI...[/]")
    console.print(f"[dim]Using {len(documents)} uploaded document(s) for context[/]")
    console.print(f"[dim]Provider: {llm_service.provider} | Model: {llm_service.model}[/]")
    console.print()
    
    try:
        # Launch TUI chat interface in document mode
        console.print("[bold green]Launching chat interface...[/]")
        console.print("[dim]Press Ctrl+C in the chat to return to menu[/]")
        console.print()
        
        run_chat_app(
            llm_service=llm_service,
            rag_service=rag_service,
            mode="document",
            dashboard_data=None
        )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Returning to menu...[/]")
    except Exception as e:
        console.print(f"[red]TUI error: {str(e)}[/]")
        console.print("[yellow]Returning to menu...[/]")

def run_upload_document_interactive() -> None:
    """Upload a PDF document interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available. Install required packages for your vector database:[/]")
        console.print("[yellow]  ChromaDB: pip install langchain-chroma[/]")
        console.print("[yellow]  Qdrant: pip install langchain-qdrant qdrant-client[/]")
        console.print("[yellow]  FAISS: pip install faiss-cpu[/]")
        return
    
    console.print("[bold cyan]Upload Document[/]")
    console.print()
    
    # Get file path
    file_path = inquirer.filepath(
        message="Enter path to PDF file:",
    ).execute()
    
    if not file_path:
        return
    
    # Validate file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        console.print(f"[red]Error: File does not exist: {file_path}[/]")
        return
    
    try:
        console.print("[dim]Processing PDF...[/]")
        result = rag_service.upload_pdf(file_path)
        
        if result.get("success"):
            console.print(f"[green]✓[/] Document uploaded successfully!")
            console.print()
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Field", style="cyan", width=20)
            table.add_column("Value", style="green")
            
            table.add_row("Filename", result.get('filename', 'N/A'))
            table.add_row("Chunks", str(result.get('chunks', 0)))
            table.add_row("Document ID", result.get('document_id', 'N/A'))
            
            console.print(table)
            console.print()
        else:
            error = result.get("error", "Unknown error")
            console.print(f"[red]✗[/] Upload failed: {error}")
    except Exception as e:
        console.print(f"[red]Error uploading document: {str(e)}[/]")

def run_list_documents_interactive() -> None:
    """List uploaded documents."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    documents = rag_service.get_documents()
    
    if not documents:
        console.print("[yellow]No documents uploaded yet.[/]")
        return
    
    console.print(f"[bold cyan]Uploaded Documents ({len(documents)}):[/]")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=15)
    table.add_column("Filename", style="green")
    table.add_column("Chunks", justify="right", width=10)
    table.add_column("Uploaded", style="dim", width=20)
    
    for doc in documents:
        table.add_row(
            doc.get("id", "N/A"),
            doc.get("filename", "N/A"),
            str(doc.get("chunks", 0)),
            doc.get("uploaded_at", "N/A")[:16] if doc.get("uploaded_at") else "N/A"
        )
    
    console.print(table)
    console.print()

def run_delete_document_interactive() -> None:
    """Delete a document interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    documents = rag_service.get_documents()
    
    if not documents:
        console.print("[yellow]No documents to delete.[/]")
        return
    
    # Let user select document to delete
    choices = [
        Choice(value=doc['id'], name=f"{doc['filename']} ({doc['id']})")
        for doc in documents
    ]
    choices.append(Choice(value="cancel", name="Cancel"))
    
    choice = inquirer.select(
        message="Select document to delete:",
        choices=choices
    ).execute()
    
    if choice == "cancel":
        return
    
    # Confirm deletion
    confirm = inquirer.confirm(
        message="Are you sure you want to delete this document?",
        default=False
    ).execute()
    
    if confirm:
        if rag_service.delete_document(choice):
            console.print("[green]✓[/] Document deleted successfully.")
        else:
            console.print("[red]✗[/] Failed to delete document.")
    else:
        console.print("[yellow]Deletion cancelled.[/]")

def run_vector_db_config_interactive() -> None:
    """Configure vector database interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    console.print("[bold cyan]Vector Database Configuration[/]")
    console.print()
    
    # Show current configuration
    db_info = rag_service.get_vector_db_info()
    console.print(f"[dim]Current: {db_info['type'].upper()}[/]")
    if db_info['config']:
        console.print(f"[dim]Config: {db_info['config']}[/]")
    console.print()
    
    # Select vector database type
    available_stores = db_info['available_stores']
    if not available_stores:
        console.print("[red]No vector databases available. Please install required packages:[/]")
        console.print("[yellow]  ChromaDB: pip install langchain-chroma[/]")
        console.print("[yellow]  Qdrant: pip install langchain-qdrant qdrant-client[/]")
        console.print("[yellow]  FAISS: pip install faiss-cpu[/]")
        return
    
    choices = [
        Choice(value=db, name=db.upper()) 
        for db in available_stores
    ]
    choices.append(Choice(value="cancel", name="Cancel"))
    
    selected_db = inquirer.select(
        message="Select vector database:",
        choices=choices
    ).execute()
    
    if selected_db == "cancel":
        return
    
    # Configure based on selected database
    config = {}
    
    if selected_db == "qdrant":
        # Qdrant configuration
        url = inquirer.text(
            message="Qdrant URL (leave empty for local, or enter http://host:port or file://path):",
            default=""
        ).execute()
        
        if url:
            config["url"] = url
            if url.startswith("http"):
                api_key = inquirer.secret(
                    message="Qdrant API Key (optional, press Enter to skip):",
                    default=""
                ).execute()
                if api_key:
                    config["api_key"] = api_key
        else:
            # Local Qdrant - use default path
            config["url"] = ""
        
        collection_name = inquirer.text(
            message="Collection name (default: xpol_documents):",
            default="xpol_documents"
        ).execute()
        if collection_name:
            config["collection_name"] = collection_name
    
    # Save configuration
    try:
        if rag_service.update_vector_db_config(
            vector_db_type=selected_db,
            vector_db_config=config if config else None
        ):
            console.print(f"[green]✓[/] Configuration saved successfully!")
            console.print("[yellow]Note: You may need to restart or re-upload documents for changes to take full effect.[/]")
            
            # Ask if user wants to reload service
            reload = inquirer.confirm(
                message="Reload RAG service with new configuration now?",
                default=True
            ).execute()
            
            if reload:
                refresh_rag_service()
                console.print("[green]✓[/] RAG service reloaded.")
        else:
            console.print("[red]✗[/] Failed to save configuration.")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/]")

def run_rag_settings_interactive() -> None:
    """Configure RAG settings (chunk size, overlap, retriever k) interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return

    settings = rag_service.get_rag_settings()
    console.print("[bold cyan]RAG Settings (Chunk & Retrieval)[/]")
    console.print()
    console.print(f"[dim]Current: chunk_size={settings['chunk_size']}, chunk_overlap={settings['chunk_overlap']}, retriever_k={settings['retriever_k']}[/]")
    console.print("[dim]Note: Chunk settings apply to new uploads only. Retriever k applies to chat and search.[/]")
    console.print()

    chunk_size_str = inquirer.text(
        message="Chunk size (256-2000, characters per chunk):",
        default=str(settings["chunk_size"])
    ).execute()

    chunk_overlap_str = inquirer.text(
        message="Chunk overlap (0-500, must be < chunk size):",
        default=str(settings["chunk_overlap"])
    ).execute()

    retriever_k_str = inquirer.text(
        message="Retriever k (number of chunks to retrieve, 1-50):",
        default=str(settings["retriever_k"])
    ).execute()

    try:
        chunk_size = int(chunk_size_str.strip()) if chunk_size_str.strip() else None
        chunk_overlap = int(chunk_overlap_str.strip()) if chunk_overlap_str.strip() else None
        retriever_k = int(retriever_k_str.strip()) if retriever_k_str.strip() else None
    except ValueError:
        console.print("[red]Invalid number(s). Settings unchanged.[/]")
        return

    if rag_service.update_rag_settings(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        retriever_k=retriever_k,
    ):
        console.print("[green]✓[/] RAG settings saved.")
        console.print("[yellow]Reload the RAG service for chunk/retriever changes to take effect.[/]")
        reload = inquirer.confirm(
            message="Reload RAG service with new settings now?",
            default=True
        ).execute()
        if reload:
            refresh_rag_service()
            console.print("[green]✓[/] RAG service reloaded.")
    else:
        console.print("[red]✗[/] Failed to save RAG settings.")

def run_document_search_interactive() -> None:
    """Search documents interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    # Check if any documents are uploaded
    documents = rag_service.get_documents()
    if not documents:
        console.print("[yellow]No documents uploaded yet. Please upload PDFs first.[/]")
        return
    
    console.print("[bold cyan]Document Search[/]")
    console.print(f"[dim]Searching across {len(documents)} document(s)[/]")
    console.print()
    
    while True:
        query = inquirer.text(
            message="Enter search query (or type 'back' to return):",
        ).execute()
        
        if not query.strip():
            continue
        
        if query.lower().strip() == 'back':
            break
        
        try:
            # Get number of results
            top_k = inquirer.number(
                message="Number of results (default: 5):",
                default=5,
                min_allowed=1,
                max_allowed=20
            ).execute()
            
            console.print(f"[dim]Searching for: {query}[/]")
            results = rag_service.search(query, top_k=int(top_k))
            
            if results:
                console.print(f"\n[green]Found {len(results)} result(s):[/]")
                console.print()
                
                for i, result in enumerate(results, 1):
                    text = result.get("text", "")
                    metadata = result.get("metadata", {})
                    filename = metadata.get("filename", "Unknown")
                    
                    console.print(f"[bold cyan]{i}.[/] [green]{filename}[/]")
                    if metadata.get("document_id"):
                        console.print(f"   [dim]Document ID: {metadata['document_id']}[/]")
                    console.print(f"   {text[:200]}{'...' if len(text) > 200 else ''}")
                    console.print()
            else:
                console.print("[yellow]No results found.[/]")
                console.print()
            
        except Exception as e:
            console.print(f"[red]Error searching: {str(e)}[/]")
            console.print()

def run_document_details_interactive() -> None:
    """View document details interactively."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    documents = rag_service.get_documents()
    if not documents:
        console.print("[yellow]No documents uploaded yet.[/]")
        return
    
    # Let user select document
    choices = [
        Choice(value=doc['id'], name=f"{doc['filename']} ({doc['id']})")
        for doc in documents
    ]
    choices.append(Choice(value="cancel", name="Cancel"))
    
    choice = inquirer.select(
        message="Select document to view details:",
        choices=choices
    ).execute()
    
    if choice == "cancel":
        return
    
    details = rag_service.get_document_details(choice)
    if not details:
        console.print("[red]Document not found.[/]")
        return
    
    console.print(f"\n[bold cyan]Document Details[/]")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    table.add_row("ID", details.get("id", "N/A"))
    table.add_row("Filename", details.get("filename", "N/A"))
    table.add_row("Uploaded", details.get("uploaded_at", "N/A")[:19] if details.get("uploaded_at") else "N/A")
    table.add_row("Chunks", str(details.get("chunks", 0)))
    table.add_row("File Size", f"{details.get('file_size_mb', 0)} MB ({details.get('file_size', 0)} bytes)")
    table.add_row("File Exists", "✓ Yes" if details.get("file_exists") else "✗ No")
    if details.get("file_path"):
        table.add_row("File Path", details["file_path"])
    
    console.print(table)
    console.print()

def run_statistics_interactive() -> None:
    """Show RAG system statistics."""
    rag_service = get_rag_service()
    if not rag_service:
        console.print("[red]RAG service not available.[/]")
        return
    
    stats = rag_service.get_statistics()
    db_info = rag_service.get_vector_db_info()
    
    console.print(f"\n[bold cyan]RAG System Statistics[/]")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Value", style="green")
    
    table.add_row("Total Documents", str(stats.get("total_documents", 0)))
    table.add_row("Total Chunks", str(stats.get("total_chunks", 0)))
    table.add_row("Total Size", f"{stats.get('total_size_mb', 0)} MB")
    table.add_row("Vector Database", stats.get("vector_db_type", "N/A").upper())
    table.add_row("DB Available", "✓ Yes" if stats.get("vector_db_available") else "✗ No")
    table.add_row("Storage Directory", stats.get("storage_directory", "N/A"))
    
    console.print(table)
    console.print()

