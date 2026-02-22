"""AI-related CLI commands."""

from typing import Optional, Dict, Any
import click
from xpol.cli.utils.display import show_enhanced_progress, format_ai_response
from xpol.cli.commands.base import BaseCommand
from xpol.cli.ai.service import LLMService
from xpol.cli.commands.chat import chat as chat_command

class AICommandBase(BaseCommand):
    """Base class for AI commands."""
    
    def __init__(
        self,
        project_id: Optional[str],
        billing_table_prefix: str,
        location: str,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(project_id, billing_table_prefix, location)
        self.llm_service = LLMService(
            provider=provider,
            api_key=api_key,
            model=model,
        )

class AnalyzeCommand(AICommandBase):
    """AI analysis command implementation."""
    
    def run(self):
        """Run the AI analysis command."""
        show_enhanced_progress("Initializing services...")
        self.init_bigquery()
        
        show_enhanced_progress("Fetching cost data...")
        # Add your data fetching logic here
        
        show_enhanced_progress("Generating AI analysis...")
        # Add your analysis logic here
        
        show_enhanced_progress("Done!", done=True)

class ExplainSpikeCommand(AICommandBase):
    """Explain cost spike command implementation."""
    
    def run(self):
        """Run the explain spike command."""
        show_enhanced_progress("Analyzing cost patterns...")
        self.init_bigquery()
        
        show_enhanced_progress("Identifying cost spikes...")
        # Add spike detection logic here
        
        show_enhanced_progress("Generating explanation...")
        # Add explanation generation logic here
        
        show_enhanced_progress("Done!", done=True)

class PrioritizeCommand(AICommandBase):
    """Prioritize recommendations command implementation."""
    
    def run(self):
        """Run the prioritize command."""
        show_enhanced_progress("Gathering recommendations...")
        self.init_bigquery()
        
        show_enhanced_progress("Analyzing impact...")
        # Add impact analysis logic here
        
        show_enhanced_progress("Prioritizing recommendations...")
        # Add prioritization logic here
        
        show_enhanced_progress("Done!", done=True)

class BudgetSuggestionsCommand(AICommandBase):
    """Budget suggestions command implementation."""
    
    def run(self):
        """Run the budget suggestions command."""
        show_enhanced_progress("Analyzing spending patterns...")
        self.init_bigquery()
        
        show_enhanced_progress("Generating budget suggestions...")
        # Add budget analysis logic here
        
        show_enhanced_progress("Done!", done=True)

class UtilizationCommand(AICommandBase):
    """Resource utilization analysis command implementation."""
    
    def run(self):
        """Run the utilization analysis command."""
        show_enhanced_progress("Gathering resource metrics...")
        self.init_bigquery()
        
        show_enhanced_progress("Analyzing utilization patterns...")
        # Add utilization analysis logic here
        
        show_enhanced_progress("Generating recommendations...")
        # Add recommendation logic here
        
        show_enhanced_progress("Done!", done=True)

@click.group()
def ai():
    """AI-powered cost analysis commands."""
    pass

# Add chat command to AI group
ai.add_command(chat_command, name="chat")

@ai.command()
@BaseCommand.common_options
@click.option("--provider", type=str, help="AI provider to use")
@click.option("--api-key", type=str, help="API key for the AI provider")
@click.option("--model", type=str, help="Model to use for analysis")
@click.pass_context
def analyze(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
) -> None:
    """Generate AI-powered cost analysis."""
    cmd = AnalyzeCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        provider=provider,
        api_key=api_key,
        model=model,
    )
    cmd.run()

@ai.command()
@BaseCommand.common_options
@click.argument("question", required=True)
@click.option("--provider", type=str, help="AI provider to use")
@click.option("--api-key", type=str, help="API key for the AI provider")
@click.option("--model", type=str, help="Model to use for analysis")
@click.pass_context
def ask(
    ctx: click.Context,
    question: str,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
) -> None:
    """Ask questions about your cloud costs."""
    cmd = AICommandBase(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        provider=provider,
        api_key=api_key,
        model=model,
    )
    cmd.init_bigquery()
    answer = cmd.llm_service.ask(question, {})
    format_ai_response(question, answer, provider, model)

@ai.command()
@BaseCommand.common_options
@click.option("--provider", type=str, help="AI provider to use")
@click.option("--api-key", type=str, help="API key for the AI provider")
@click.option("--model", type=str, help="Model to use for analysis")
@click.pass_context
def explain_spike(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
) -> None:
    """Explain sudden changes in cloud costs."""
    cmd = ExplainSpikeCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        provider=provider,
        api_key=api_key,
        model=model,
    )
    cmd.run()

@ai.command()
@BaseCommand.common_options
@click.option("--provider", type=str, help="AI provider to use")
@click.option("--api-key", type=str, help="API key for the AI provider")
@click.option("--model", type=str, help="Model to use for analysis")
@click.pass_context
def prioritize(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
) -> None:
    """Prioritize cost optimization recommendations."""
    cmd = PrioritizeCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        provider=provider,
        api_key=api_key,
        model=model,
    )
    cmd.run()

@ai.command()
@BaseCommand.common_options
@click.option("--provider", type=str, help="AI provider to use")
@click.option("--api-key", type=str, help="API key for the AI provider")
@click.option("--model", type=str, help="Model to use for analysis")
@click.pass_context
def budget_suggestions(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
) -> None:
    """Get AI-powered budget recommendations."""
    cmd = BudgetSuggestionsCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        provider=provider,
        api_key=api_key,
        model=model,
    )
    cmd.run()

@ai.command()
@BaseCommand.common_options
@click.option("--provider", type=str, help="AI provider to use")
@click.option("--api-key", type=str, help="API key for the AI provider")
@click.option("--model", type=str, help="Model to use for analysis")
@click.pass_context
def utilization(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
) -> None:
    """Analyze resource utilization and get optimization suggestions."""
    cmd = UtilizationCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        provider=provider,
        api_key=api_key,
        model=model,
    )
    cmd.run()

# RAG (Retrieval Augmented Generation) subcommands
@ai.group(name="rag")
def rag_group():
    """Document chat and RAG commands."""
    pass

@rag_group.command(name="chat")
@click.pass_context
def rag_chat(ctx: click.Context) -> None:
    """Start document chat with RAG (interactive TUI)."""
    from xpol.cli.interactive.workflows.rag import run_rag_chat_interactive
    from xpol.cli.ai.service import get_llm_service
    from xpol.cli.constants import EX_OK, EX_CONFIG
    
    llm_service = get_llm_service()
    if not llm_service:
        click.echo("AI service not configured. Please run: xpol setup --interactive")
        ctx.obj["exit_code"] = EX_CONFIG
        return
    
    try:
        run_rag_chat_interactive()
        ctx.obj["exit_code"] = EX_OK
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"RAG chat failed: {str(e)}", exc_info=True)
        ctx.obj["exit_code"] = 1

@rag_group.command(name="upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def rag_upload(ctx: click.Context, file_path: str) -> None:
    """Upload a PDF document for RAG indexing."""
    from xpol.cli.interactive.workflows.rag import get_rag_service
    from rich.console import Console
    from xpol.cli.constants import EX_OK
    
    console = Console()
    rag_service = get_rag_service()
    
    if not rag_service:
        console.print("[red]RAG service not available. Install required packages.[/]")
        ctx.obj["exit_code"] = 1
        return
    
    try:
        console.print(f"[cyan]Uploading document: {file_path}[/]")
        result = rag_service.upload_pdf(file_path)
        
        if result.get("success"):
            console.print(f"[green]✓ Document uploaded successfully![/]")
            console.print(f"  - Chunks: {result.get('chunks', 0)}")
            console.print(f"  - Document ID: {result.get('document_id', 'N/A')}")
        else:
            console.print(f"[red]✗ Upload failed: {result.get('error', 'Unknown error')}[/]")
            ctx.obj["exit_code"] = 1
            return
        
        ctx.obj["exit_code"] = EX_OK
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/]")
        ctx.obj["exit_code"] = 1

@rag_group.command(name="list")
@click.pass_context
def rag_list(ctx: click.Context) -> None:
    """List uploaded documents."""
    from xpol.cli.interactive.workflows.rag import run_list_documents_interactive
    from xpol.cli.constants import EX_OK
    
    try:
        run_list_documents_interactive()
        ctx.obj["exit_code"] = EX_OK
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.obj["exit_code"] = 1

@rag_group.command(name="stats")
@click.pass_context
def rag_stats(ctx: click.Context) -> None:
    """Show RAG system statistics."""
    from xpol.cli.interactive.workflows.rag import run_statistics_interactive
    from xpol.cli.constants import EX_OK
    
    try:
        run_statistics_interactive()
        ctx.obj["exit_code"] = EX_OK
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.obj["exit_code"] = 1
