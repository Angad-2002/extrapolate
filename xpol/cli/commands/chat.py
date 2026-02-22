"""Chat command for direct TUI access."""

import click
from rich.console import Console

console = Console()


@click.command("chat")
@click.option(
    "--mode",
    type=click.Choice(["ai", "document"], case_sensitive=False),
    default="ai",
    help="Chat mode: 'ai' for AI chat or 'document' for document chat",
)
@click.option(
    "--load-data/--no-load-data",
    default=True,
    help="Load dashboard data for AI analysis (AI mode only)",
)
@click.pass_context
def chat(ctx: click.Context, mode: str, load_data: bool) -> None:
    """Launch interactive chat TUI.
    
    Start a full-screen terminal chat interface with AI or document chat capabilities.
    
    Examples:
    
        # Start AI chat with dashboard data
        xpol ai chat
        
        # Start AI chat without loading dashboard data
        xpol ai chat --no-load-data
        
        # Start document chat (requires RAG setup)
        xpol ai chat --mode document
    """
    from xpol.cli.ai.service import get_llm_service
    from xpol.cli.tui.chat_app import run_chat_app
    from xpol.cli.constants import EX_OK, EX_CONFIG, EX_GENERAL
    
    try:
        # Get LLM service
        llm_service = get_llm_service()
        if not llm_service:
            console.print("[red]AI service not configured.[/]")
            console.print("[yellow]Please set up AI provider first:[/]")
            console.print("  - Run: xpol setup --interactive")
            console.print("  - Or set environment variables: AI_PROVIDER, OPENAI_API_KEY (or GROQ_API_KEY, ANTHROPIC_API_KEY)")
            ctx.obj["exit_code"] = EX_CONFIG
            return
        
        console.print(f"[green]✓[/] AI service ready: {llm_service.provider} / {llm_service.model}")
        
        # Prepare services based on mode
        rag_service = None
        dashboard_data = None
        
        if mode == "document":
            # Document chat mode - setup RAG
            from xpol.cli.interactive.workflows.rag import get_rag_service
            
            console.print("[cyan]Setting up document chat...[/]")
            rag_service = get_rag_service()
            
            if not rag_service:
                console.print("[red]RAG service not available.[/]")
                console.print("[yellow]Please install vector database packages:[/]")
                console.print("  - ChromaDB: pip install langchain-chroma")
                console.print("  - Qdrant: pip install langchain-qdrant qdrant-client")
                console.print("  - FAISS: pip install faiss-cpu")
                ctx.obj["exit_code"] = EX_CONFIG
                return
            
            # Check if documents are uploaded
            documents = rag_service.get_documents()
            if not documents:
                console.print("[yellow]Warning: No documents uploaded yet.[/]")
                console.print("[dim]You can still chat, but responses will be limited.[/]")
                console.print("[dim]Upload documents using: xpol ai rag upload[/]")
            else:
                console.print(f"[green]✓[/] {len(documents)} document(s) loaded")
        
        elif mode == "ai" and load_data:
            # AI chat mode with dashboard data
            from xpol.cli.interactive.utils.context import prompt_common_context, apply_logging_from_context
            from xpol.core import DashboardRunner
            from xpol.utils.visualizations import print_progress, print_error
            
            console.print("[cyan]Loading dashboard data for AI analysis...[/]")
            
            try:
                # Collect context
                ctx_data = prompt_common_context(include_logging=False)
                
                # Initialize runner
                runner = DashboardRunner(
                    project_id=ctx_data["project_id"],
                    billing_dataset=ctx_data["billing_dataset"],
                    billing_table_prefix="gcp_billing_export_v1",
                    regions=ctx_data["regions"],
                    location=ctx_data["location"],
                    hide_project_id=ctx_data["hide_project_id"]
                )
                
                # Run analysis
                print_progress("Analyzing GCP resources...")
                dashboard_data = runner.run()
                print_progress("Analysis complete", done=True)
                
                console.print("[green]✓[/] Dashboard data loaded successfully")
                
            except Exception as e:
                print_error(f"Failed to load dashboard data: {str(e)}")
                console.print("[yellow]Continuing without dashboard data...[/]")
                dashboard_data = None
        
        # Launch chat TUI
        console.print("\n[bold green]Launching chat interface...[/]")
        console.print("[dim]Press Ctrl+C to exit[/]\n")
        
        run_chat_app(
            llm_service=llm_service,
            rag_service=rag_service,
            mode=mode,
            dashboard_data=dashboard_data
        )
        
        ctx.obj["exit_code"] = EX_OK
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat session ended[/]")
        ctx.obj["exit_code"] = EX_OK
    except Exception as e:
        console.print(f"\n[red]Error:[/] {str(e)}")
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Chat command failed: {str(e)}", exc_info=True)
        ctx.obj["exit_code"] = EX_GENERAL

