"""Main TUI Chat Application using Textual framework."""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, RichLog, Label, ListView, ListItem
from textual.message import Message
from textual.screen import Screen, ModalScreen
from textual import work
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import logging

from xpol.cli.ai.service import LLMService
from xpol.services.rag.service import RAGService

# Try to import DashboardData, but make it optional to avoid import chain issues
try:
    from xpol.types import DashboardData
except (ImportError, TypeError):
    # Fallback if types module has issues
    DashboardData = Any  # type: ignore

logger = logging.getLogger(__name__)


class ChatMessage(Static):
    """Minimal chat message (Chabeau-style: no heavy borders, clean wrap)."""
    DEFAULT_CSS = """
    ChatMessage {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border: none;
    }
    ChatMessage.user-message {
        background: transparent;
    }
    ChatMessage.assistant-message {
        background: transparent;
    }
    ChatMessage.system-message {
        background: transparent;
    }
    ChatMessage.error-message {
        background: $error 15%;
        padding: 0 1;
    }
    """
    
    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        **kwargs
    ):
        """Initialize a chat message.
        
        Args:
            role: Message role (user, assistant, system, error)
            content: Message content (supports markdown)
            timestamp: Message timestamp
        """
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        
        # Set CSS class based on role
        self.add_class(f"{role}-message")
    
    def render(self):
        """Render minimal message: role label + content (Chabeau-style, no box)."""
        from rich.console import Group
        role_label = {"user": "You:", "assistant": "Assistant:", "system": "", "error": "Error:"}.get(self.role, "")
        try:
            body = Markdown(self.content, code_theme="monokai")
        except Exception as e:
            logger.warning(f"Failed to render markdown: {e}")
            body = Text(self.content)
        if role_label:
            return Group(Text.from_markup(f"[dim]{role_label}[/]"), body)
        return body

    def update_content(self, content: str) -> None:
        """Update message content (e.g. for streaming)."""
        self.content = content
        self.refresh()


class ChatHistory(ScrollableContainer):
    """Scrollable chat area (Chabeau-style: minimal border, content wraps cleanly)."""
    DEFAULT_CSS = """
    ChatHistory {
        height: 1fr;
        border: none;
        background: $surface;
        padding: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages: List[ChatMessage] = []
    
    def add_message(self, role: str, content: str, timestamp: Optional[datetime] = None) -> None:
        """Add a new message to the chat history."""
        message = ChatMessage(role=role, content=content, timestamp=timestamp)
        self.messages.append(message)
        self.mount(message)
        
        # Auto-scroll to bottom
        self.call_after_refresh(self.scroll_end, animate=False)

    def append_to_last_assistant_content(self, content: str) -> None:
        """Update the last assistant message's content (for streaming)."""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                msg.update_content(content)
                self.call_after_refresh(self.scroll_end, animate=False)
                return
    
    def clear_messages(self) -> None:
        """Clear all messages from history."""
        for msg in self.messages:
            msg.remove()
        self.messages.clear()


class StatusBar(Static):
    """Minimal one-line status (Chabeau-style: no wrap)."""
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $panel;
        border-top: none;
        padding: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "AI Chat"
        self.provider = "Unknown"
        self.model = "Unknown"
        self.is_processing = False
        self.is_streaming = False
        self.session_name = "Default Session"
        self.message_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def render(self) -> Text:
        """Single line status (Chabeau-style, avoids line break)."""
        parts = [f"[dim]{self.mode} · {self.provider} · {self.model}[/]"]
        if self.is_streaming:
            parts.append("[magenta]●[/]")
        elif self.is_processing:
            parts.append("[yellow]…[/]")
        return Text.from_markup("  ".join(parts))
    
    def set_processing(self, processing: bool) -> None:
        """Set processing status."""
        self.is_processing = processing
        self.refresh()

    def set_streaming(self, streaming: bool) -> None:
        """Set streaming status (Chabeau-style indicator)."""
        self.is_streaming = streaming
        self.refresh()
    
    def set_mode(self, mode: str) -> None:
        """Set current mode."""
        self.mode = mode
        self.refresh()
    
    def set_provider_info(self, provider: str, model: str) -> None:
        """Set provider and model information."""
        self.provider = provider
        self.model = model
        self.refresh()
    
    def set_session_name(self, name: str) -> None:
        """Set session name."""
        self.session_name = name
        self.refresh()
    
    def update_stats(self, message_count: int, total_tokens: int, total_cost: float) -> None:
        """Update session statistics."""
        self.message_count = message_count
        self.total_tokens = total_tokens
        self.total_cost = total_cost
        self.refresh()


class ChatInput(Input):
    """Minimal input (Chabeau-style: short hint, no wrap)."""
    DEFAULT_CSS = """
    ChatInput {
        dock: bottom;
        border: none;
        border-top: solid $panel;
        background: $surface;
        padding: 0 1;
    }
    """
    PLACEHOLDER = "Type a new message (Enter=send Ctrl+C=quit /help)"

    def __init__(self, **kwargs):
        super().__init__(placeholder=self.PLACEHOLDER, **kwargs)


class SessionListItem(ListItem):
    """Custom list item for displaying session information."""
    
    DEFAULT_CSS = """
    SessionListItem {
        height: auto;
        padding: 1 2;
    }
    
    SessionListItem:hover {
        background: $accent 30%;
    }
    
    SessionListItem.-active {
        background: $primary 30%;
        border-left: thick $success;
    }
    """
    
    def __init__(self, session_data: Dict[str, Any], is_current: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.session_data = session_data
        self.is_current = is_current
        if is_current:
            self.add_class("-active")
    
    def render(self) -> Table:
        """Render session information as a table."""
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=3)
        table.add_column(justify="right", ratio=1)
        
        # Session name with current indicator
        name = self.session_data.get("name", "Unknown Session")
        if self.is_current:
            name_text = f"[bold green]▶ {name}[/] [dim](current)[/]"
        else:
            name_text = f"[bold]{name}[/]"
        
        # Stats
        msg_count = self.session_data.get("messages", 0)
        tokens = self.session_data.get("tokens", 0)
        cost = self.session_data.get("cost", 0.0)
        
        stats_text = f"[dim]{msg_count} msgs"
        if tokens > 0:
            stats_text += f" • {tokens:,} tokens"
        if cost > 0:
            stats_text += f" • ${cost:.4f}"
        stats_text += "[/]"
        
        table.add_row(name_text, stats_text)
        return table


class SessionSelectionScreen(ModalScreen[Optional[str]]):
    """Modal screen for selecting a chat session."""
    
    DEFAULT_CSS = """
    SessionSelectionScreen {
        align: center middle;
    }
    
    #session-dialog {
        width: 80;
        height: 24;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #session-title {
        width: 100%;
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    #session-list {
        height: 1fr;
        border: solid $accent;
        background: $panel;
        margin: 1 0;
    }
    
    #session-help {
        height: 3;
        content-align: center middle;
        color: $text-muted;
    }
    """
    
    BINDINGS = [
        Binding("escape", "dismiss_none", "Cancel", priority=True),
        Binding("enter", "select_session", "Select", show=True),
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
    ]
    
    def __init__(
        self,
        sessions: List[Dict[str, Any]],
        current_session_id: str,
        **kwargs
    ):
        """Initialize session selection screen.
        
        Args:
            sessions: List of session dictionaries
            current_session_id: ID of currently active session
        """
        super().__init__(**kwargs)
        self.sessions = sessions
        self.current_session_id = current_session_id
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="session-dialog"):
            yield Static("Select Session", id="session-title")
            
            # Create list view with session items
            list_view = ListView(id="session-list")
            list_view.can_focus = True
            yield list_view
            
            yield Static(
                "↑/↓: Navigate  •  Enter: Select  •  Esc: Cancel",
                id="session-help"
            )
    
    def on_mount(self) -> None:
        """Populate the list when mounted."""
        list_view = self.query_one("#session-list", ListView)
        
        # Add session items
        for session in self.sessions:
            is_current = session["id"] == self.current_session_id
            item = SessionListItem(session, is_current=is_current)
            list_view.append(item)
        
        # Focus the list
        list_view.focus()
        
        # Select current session by default
        current_index = next(
            (i for i, s in enumerate(self.sessions) if s["id"] == self.current_session_id),
            0
        )
        if current_index < len(list_view):
            list_view.index = current_index
    
    def action_dismiss_none(self) -> None:
        """Dismiss without selection."""
        self.dismiss(None)
    
    def action_select_session(self) -> None:
        """Select the highlighted session."""
        list_view = self.query_one("#session-list", ListView)
        if list_view.highlighted_child:
            session_item = list_view.highlighted_child
            if isinstance(session_item, SessionListItem):
                session_id = session_item.session_data["id"]
                self.dismiss(session_id)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle double-click or enter on list item."""
        if isinstance(event.item, SessionListItem):
            session_id = event.item.session_data["id"]
            self.dismiss(session_id)



class ChatApp(App):
    """Main TUI Chat Application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    Header {
        background: $panel;
        color: $text;
    }
    Footer {
        background: $surface;
        border-top: none;
        height: 1;
    }
    #main-container {
        height: 1fr;
    }
    """
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True, show=True),
        Binding("ctrl+enter", "send_message", "Send", priority=True, show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=False),
        Binding("ctrl+m", "toggle_mode", "Toggle Mode", show=False),
        Binding("ctrl+n", "new_session", "New Session", show=False),
        Binding("ctrl+s", "show_sessions", "Sessions", show=False),
        Binding("ctrl+i", "show_info", "Info", show=False),
        Binding("ctrl+h", "show_help", "Help", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        rag_service: Optional[RAGService] = None,
        mode: str = "ai",
        **kwargs
    ):
        """Initialize the chat application.
        
        Args:
            llm_service: LLM service for AI responses
            rag_service: RAG service for document chat
            mode: Initial mode ('ai' or 'document')
        """
        super().__init__(**kwargs)
        self.llm_service = llm_service
        self.rag_service = rag_service
        self._mode = mode  # Use private attribute to avoid Textual reactive system
        self.conversation_history: List[Dict[str, str]] = []
        self.dashboard_data: Optional[DashboardData] = None
        
        # Session management
        self.sessions: List[Dict[str, Any]] = []
        self.current_session_id: str = "default"
        self.current_session_name: str = "Default Session"
        
        # Token and cost tracking
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
    
    @property
    def current_mode(self) -> str:
        """Get current chat mode."""
        return self._mode
    
    @current_mode.setter
    def current_mode(self, value: str) -> None:
        """Set current chat mode."""
        self._mode = value
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            yield ChatHistory(id="chat-history")
            yield ChatInput(id="chat-input")
        
        yield StatusBar(id="status-bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app when mounted (Chabeau-style title: app • provider • model)."""
        mode_title = "AI Chat" if self.current_mode == "ai" else "Document Chat"
        if self.llm_service:
            self.title = f"Extrapolate - {mode_title} • {self.llm_service.provider} • {self.llm_service.model}"
        else:
            self.title = f"Extrapolate - {mode_title}"

        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_mode(mode_title)
        status_bar.set_session_name(self.current_session_name)
        if self.llm_service:
            status_bar.set_provider_info(
                self.llm_service.provider,
                self.llm_service.model,
            )
        
        # Initialize with default session
        self.sessions.append({
            "id": self.current_session_id,
            "name": self.current_session_name,
            "messages": 0,
            "tokens": 0,
            "cost": 0.0
        })
        
        # Focus input
        self.query_one("#chat-input", ChatInput).focus()
        
        # Show welcome message
        self._show_welcome_message()
    
    def _show_welcome_message(self) -> None:
        """Minimal welcome (Chabeau-style: one line, no bullets)."""
        chat_history = self.query_one("#chat-history", ChatHistory)
        if self.current_mode == "ai":
            welcome = "Ask about GCP costs or resources. Enter to send, Ctrl+C to quit. Type /help for more."
        else:
            welcome = "Ask questions about your documents. Enter to send, Ctrl+C to quit. Type /help for more."
        chat_history.add_message("system", welcome)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key pressed in input field."""
        # Only handle submission from our chat input
        if event.input.id == "chat-input":
            self.action_send_message()
    
    def action_send_message(self) -> None:
        """Send the current message."""
        chat_input = self.query_one("#chat-input", ChatInput)
        message = chat_input.value.strip()
        
        if not message:
            return
        
        # Clear input
        chat_input.value = ""
        
        # Add user message to history
        chat_history = self.query_one("#chat-history", ChatHistory)
        chat_history.add_message("user", message)
        
        # Process message asynchronously
        self._process_message(message)
    
    @work(exclusive=True, thread=True)
    def _process_message(self, message: str) -> None:
        """Process user message and get AI response (streaming when possible, Chabeau-style)."""
        status_bar = self.query_one("#status-bar", StatusBar)
        chat_history = self.query_one("#chat-history", ChatHistory)

        try:
            use_streaming = (
                (self.current_mode == "ai" and self.llm_service)
                or (
                    self.current_mode == "document"
                    and self.rag_service
                    and self.llm_service
                )
            )
            if use_streaming:
                # Streaming path (Chabeau-style): one assistant message, update in place
                self.call_from_thread(status_bar.set_processing, True)
                self.call_from_thread(status_bar.set_streaming, True)
                self.call_from_thread(chat_history.add_message, "assistant", "…")

                context = ""
                if self.conversation_history:
                    recent = self.conversation_history[-6:]
                    context = "\n\nPrevious conversation:\n" + "\n".join(
                        f"{m['role'].capitalize()}: {m['content']}" for m in recent
                    )

                async def consume_stream() -> str:
                    full: List[str] = []
                    try:
                        if self.current_mode == "document" and self.rag_service:
                            stream = self.rag_service.stream_chat(
                                query=message,
                                provider=self.llm_service.provider_name,
                                model=self.llm_service.model,
                                api_key=self.llm_service.api_key,
                            )
                            async for chunk in stream:
                                full.append(chunk)
                                self.call_from_thread(
                                    chat_history.append_to_last_assistant_content,
                                    "".join(full),
                                )
                        elif self.dashboard_data:
                            stream = self.llm_service.stream_answer_question(
                                message, self.dashboard_data, context=context
                            )
                            async for chunk in stream:
                                full.append(chunk)
                                self.call_from_thread(
                                    chat_history.append_to_last_assistant_content,
                                    "".join(full),
                                )
                        else:
                            prompt = f"{context}\n\nUser: {message}\n\nAssistant:"
                            stream = self.llm_service.stream_chat(prompt)
                            async for chunk in stream:
                                full.append(chunk)
                                self.call_from_thread(
                                    chat_history.append_to_last_assistant_content,
                                    "".join(full),
                                )
                    except Exception as e:
                        raise e
                    return "".join(full)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(consume_stream())
                finally:
                    loop.close()
            else:
                # Non-streaming path (no LLM or no RAG in document mode)
                self.call_from_thread(status_bar.set_processing, True)
                if self.current_mode == "ai":
                    response = self._get_ai_response(message)
                else:
                    response = self._get_document_response(message)
                self.call_from_thread(
                    chat_history.add_message,
                    "assistant",
                    response,
                )

            self.call_from_thread(status_bar.set_streaming, False)
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response})
            self.total_tokens += len(message.split()) * 2 + len(response.split()) * 2
            self.total_cost += self.total_tokens * 0.00001
            self._update_session_stats()

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            self.call_from_thread(status_bar.set_streaming, False)
            error_msg = f"**Error:** {str(e)}\n\nPlease try again or check your configuration."
            self.call_from_thread(
                chat_history.add_message,
                "error",
                error_msg,
            )
        finally:
            self.call_from_thread(status_bar.set_processing, False)
    
    def _get_ai_response(self, message: str) -> str:
        """Get AI response for the message.
        
        Args:
            message: User message
            
        Returns:
            AI response text
        """
        if not self.llm_service:
            raise ValueError("LLM service not configured. Please set up AI provider first.")
        
        # Build context from conversation history
        context = ""
        if self.conversation_history:
            recent = self.conversation_history[-6:]  # Last 3 exchanges
            context = "\n\nPrevious conversation:\n" + "\n".join([
                f"{msg['role'].capitalize()}: {msg['content']}"
                for msg in recent
            ])
        
        # Get response
        if self.dashboard_data:
            return self.llm_service.answer_question(
                message,
                self.dashboard_data,
                context=context
            )
        else:
            # Simple chat without dashboard data
            prompt = f"{context}\n\nUser: {message}\n\nAssistant:"
            return self.llm_service.chat(prompt)
    
    def _get_document_response(self, message: str) -> str:
        """Get document-based response using RAG.
        
        Args:
            message: User message
            
        Returns:
            RAG response text
        """
        if not self.rag_service:
            raise ValueError("RAG service not configured. Please set up document indexing first.")
        if not self.llm_service:
            raise ValueError("LLM service not configured. RAG chat requires an AI provider.")
        
        # RAGService.chat(query, provider, model, api_key) returns {success, answer/sources} or {success, error}
        response = self.rag_service.chat(
            query=message,
            provider=self.llm_service.provider_name,
            model=self.llm_service.model,
            api_key=self.llm_service.api_key,
        )
        if not response.get("success"):
            raise ValueError(response.get("error", "RAG chat failed."))
        return response.get("answer", "")
    
    def action_clear_chat(self) -> None:
        """Clear the chat history."""
        chat_history = self.query_one("#chat-history", ChatHistory)
        chat_history.clear_messages()
        self.conversation_history.clear()
        self._show_welcome_message()
    
    def action_toggle_mode(self) -> None:
        """Toggle between AI chat and document chat modes."""
        # Toggle mode
        self.current_mode = "document" if self.current_mode == "ai" else "ai"
        
        # Update title
        mode_title = "AI Chat" if self.current_mode == "ai" else "Document Chat"
        self.title = f"Extrapolate - {mode_title}"
        
        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_mode(mode_title)
        
        # Clear and show new welcome message
        self.action_clear_chat()
    
    def action_show_help(self) -> None:
        """Show help screen."""
        chat_history = self.query_one("#chat-history", ChatHistory)
        
        help_text = """# Help & Keyboard Shortcuts

## General Commands

- **Enter** or **Ctrl+Enter** - Send message
- **Ctrl+L** - Clear chat history
- **Ctrl+M** - Toggle between AI Chat and Document Chat modes
- **Ctrl+N** - Create new session
- **Ctrl+S** - View all sessions
- **Ctrl+I** - Show session info (tokens, cost, stats)
- **Ctrl+H** - Show this help screen
- **Ctrl+C** - Exit application
- **Escape** - Cancel current operation

## Session Management

**Create New Session:**
- Press `Ctrl+N` to start a fresh conversation
- Previous session is automatically saved
- Switch between sessions any time

**View Sessions:**
- Press `Ctrl+S` to see all sessions
- Shows message count, tokens, and cost per session
- Current session is highlighted

**Session Info:**
- Press `Ctrl+I` to see detailed stats
- View total tokens used and cost
- Check provider and model information

## Token & Cost Tracking

The status bar shows real-time statistics:
- **Message Count**: Number of exchanges in current session
- **Total Tokens**: Cumulative tokens used
- **Total Cost**: Estimated cost (based on token usage)

Example status bar:
```
AI Chat • Session 14:30 | ✓ Ready | openai | gpt-4o • 5 msgs • 2,450 tokens • $0.0245
```

## AI Chat Mode

In AI Chat mode, you can:
- Ask questions about your GCP costs and resources
- Get cost optimization recommendations
- Analyze spending trends and patterns
- Receive budget suggestions

**Example Questions:**
- "What are my top 5 most expensive services?"
- "Show cost breakdown by project"
- "Suggest ways to reduce cloud costs"

## Document Chat Mode

In Document Chat mode, you can:
- Query indexed documents using natural language
- Get contextual answers from your documentation
- Search across multiple document sources

**Requirements:**
- Documents must be indexed first using the RAG service
- Use the `xpol ai rag upload` command to index documents

## Configuration

To configure AI providers and models:
1. Exit to main menu (Ctrl+C)
2. Select "Configuration & Setup"
3. Choose "Configure AI Settings"

Or set environment variables:
- `AI_PROVIDER` - openai, groq, or anthropic
- `OPENAI_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY`
- `AI_MODEL` - Model name

## Tips & Tricks

1. **Session Organization**: Create a new session for each topic or project
2. **Cost Monitoring**: Check `Ctrl+I` regularly to track token usage
3. **Quick Switch**: Use `Ctrl+M` to toggle between AI and Document modes
4. **Clear When Stuck**: Use `Ctrl+L` to start fresh in current session
5. **Multiple Topics**: Use `Ctrl+N` to separate different conversations

## Support

For more information, visit: https://github.com/your-repo/extrapolate

Press **Ctrl+L** to return to chat.
"""
        
        chat_history.add_message("system", help_text)
    
    def action_cancel(self) -> None:
        """Cancel current operation."""
        # Could be used to stop processing if needed
        pass
    
    def action_new_session(self) -> None:
        """Create a new chat session."""
        import uuid
        from datetime import datetime
        
        # Generate new session
        session_id = str(uuid.uuid4())[:8]
        session_name = f"Session {datetime.now().strftime('%H:%M')}"
        
        # Save current session
        self._save_current_session()
        
        # Create new session
        self.current_session_id = session_id
        self.current_session_name = session_name
        self.total_tokens = 0
        self.total_cost = 0.0
        
        # Add to sessions list
        self.sessions.append({
            "id": session_id,
            "name": session_name,
            "messages": 0,
            "tokens": 0,
            "cost": 0.0
        })
        
        # Clear and show new session
        self.action_clear_chat()
        
        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_session_name(session_name)
        status_bar.update_stats(0, 0, 0.0)
        
        # Show notification
        chat_history = self.query_one("#chat-history", ChatHistory)
        chat_history.add_message("system", f"**New session created:** {session_name}")
    
    def action_show_sessions(self) -> None:
        """Show session selection screen."""
        if not self.sessions:
            chat_history = self.query_one("#chat-history", ChatHistory)
            chat_history.add_message("system", "No sessions available.")
            return
        
        # Push the session selection screen
        self.push_screen(
            SessionSelectionScreen(self.sessions, self.current_session_id),
            self._handle_session_selection
        )
    
    def _handle_session_selection(self, session_id: Optional[str]) -> None:
        """Handle session selection from the modal.
        
        Args:
            session_id: Selected session ID, or None if cancelled
        """
        if session_id is None or session_id == self.current_session_id:
            return
        
        # Find the selected session
        selected_session = next(
            (s for s in self.sessions if s["id"] == session_id),
            None
        )
        
        if not selected_session:
            return
        
        # Save current session
        self._save_current_session()
        
        # Load new session (for now, just switch - full persistence would load from DB)
        self.current_session_id = session_id
        self.current_session_name = selected_session["name"]
        self.total_tokens = selected_session.get("tokens", 0)
        self.total_cost = selected_session.get("cost", 0.0)
        
        # Clear chat and update UI
        self.action_clear_chat()
        
        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_session_name(self.current_session_name)
        status_bar.update_stats(
            selected_session.get("messages", 0),
            self.total_tokens,
            self.total_cost
        )
        
        # Show notification
        chat_history = self.query_one("#chat-history", ChatHistory)
        chat_history.add_message(
            "system",
            f"**Switched to session:** {self.current_session_name}"
        )
    
    def action_show_info(self) -> None:
        """Show current session information."""
        chat_history = self.query_one("#chat-history", ChatHistory)
        
        info_md = f"# Session Information\n\n"
        info_md += f"**Session:** {self.current_session_name}\n"
        info_md += f"**Mode:** {self.current_mode.title()} Chat\n\n"
        
        info_md += f"## Statistics\n\n"
        info_md += f"- **Messages:** {len(self.conversation_history) // 2}\n"
        info_md += f"- **Total Tokens:** {self.total_tokens:,}\n"
        info_md += f"- **Total Cost:** ${self.total_cost:.4f}\n\n"
        
        info_md += f"## Provider Information\n\n"
        if self.llm_service:
            info_md += f"- **Provider:** {self.llm_service.provider}\n"
            info_md += f"- **Model:** {self.llm_service.model}\n"
        else:
            info_md += "- No LLM service configured\n"
        
        if self.dashboard_data:
            info_md += f"\n## Dashboard Data\n\n"
            info_md += f"- **Loaded:** Yes\n"
            info_md += f"- **Project ID:** {self.dashboard_data.project_id}\n"
            info_md += f"- **Billing Month:** {self.dashboard_data.billing_month}\n"
            info_md += f"- **Current Cost:** ${self.dashboard_data.current_month_cost:.2f}\n"
            info_md += f"- **Services:** {len(self.dashboard_data.service_costs)} services monitored\n"
            info_md += f"- **Potential Savings:** ${self.dashboard_data.total_potential_savings:.2f}\n"
        
        chat_history.add_message("system", info_md)
    
    def _save_current_session(self) -> None:
        """Save current session state."""
        # Find and update current session in list
        for session in self.sessions:
            if session["id"] == self.current_session_id:
                session["messages"] = len(self.conversation_history) // 2
                session["tokens"] = self.total_tokens
                session["cost"] = self.total_cost
                break
    
    def _update_session_stats(self) -> None:
        """Update session statistics in status bar."""
        status_bar = self.query_one("#status-bar", StatusBar)
        message_count = len(self.conversation_history) // 2
        status_bar.update_stats(message_count, self.total_tokens, self.total_cost)
        
        # Update session in list
        for session in self.sessions:
            if session["id"] == self.current_session_id:
                session["messages"] = message_count
                session["tokens"] = self.total_tokens
                session["cost"] = self.total_cost
                break
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def set_dashboard_data(self, data: DashboardData) -> None:
        """Set dashboard data for AI analysis.
        
        Args:
            data: Dashboard data object
        """
        self.dashboard_data = data


def run_chat_app(
    llm_service: Optional[LLMService] = None,
    rag_service: Optional[RAGService] = None,
    mode: str = "ai",
    dashboard_data: Optional[DashboardData] = None
) -> None:
    """Run the chat TUI application.
    
    Args:
        llm_service: LLM service instance
        rag_service: RAG service instance
        mode: Initial mode ('ai' or 'document')
        dashboard_data: Optional dashboard data for AI analysis
    """
    app = ChatApp(
        llm_service=llm_service,
        rag_service=rag_service,
        mode=mode
    )
    
    if dashboard_data:
        app.set_dashboard_data(dashboard_data)
    
    app.run()

