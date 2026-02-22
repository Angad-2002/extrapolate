# Extrapolate TUI Chat Interface

A modern Terminal User Interface (TUI) for interactive AI chat with your GCP cost data and documents.

## Features

### 🤖 AI Chat Mode
- **Real-time Chat**: Interactive conversations with AI about your GCP costs
- **Dashboard Integration**: Automatically loads GCP billing data for contextual analysis
- **Conversation History**: Maintains context across multiple questions
- **Markdown Rendering**: Beautiful formatting with syntax highlighting

### 📚 Document Chat Mode
- **RAG Integration**: Chat with your uploaded documents using Retrieval Augmented Generation
- **Vector Search**: Fast and accurate document retrieval
- **Multi-document Support**: Query across all uploaded PDFs
- **Source Citations**: View relevant document excerpts

### ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Send message |
| `Ctrl+L` | Clear chat history |
| `Ctrl+M` | Toggle between AI and Document chat modes |
| `Ctrl+N` | Create new session |
| `Ctrl+S` | View all sessions |
| `Ctrl+I` | Show session info (tokens/cost) |
| `Ctrl+H` | Show help screen |
| `Ctrl+C` | Exit application |
| `Escape` | Cancel current operation |

### 📊 Session Management

**Multiple Sessions:**
- Create new sessions with `Ctrl+N` for different topics
- Each session maintains its own conversation history
- Switch between sessions easily

**Session Tracking:**
- View all sessions with `Ctrl+S`
- See message count, tokens, and cost per session
- Current session highlighted in list

**Real-time Stats:**
- Token usage tracked automatically
- Cost calculated based on token count
- Stats displayed in status bar

### 💰 Token & Cost Tracking

The status bar shows live statistics:

```
AI Chat • Session 14:30 | ✓ Ready | groq | llama-3.3-70b • 5 msgs • 2,450 tokens • $0.0245
```

- **Messages**: Number of exchanges in current session
- **Tokens**: Total tokens used
- **Cost**: Estimated cost (based on token usage)

Press `Ctrl+I` for detailed session information.


## Usage

### Quick Start

```bash
# Start AI chat with dashboard data
xpol ai chat

# Start AI chat without loading dashboard data  
xpol ai chat --no-load-data

# Start document chat
xpol ai chat --mode document
```

### Interactive Mode

From the interactive menu:

```bash
# Start interactive menu
xpol setup --interactive

# Then select:
# AI Tools & Analysis > AI Chat (TUI) 
# or
# AI Tools & Analysis > Document Chat (RAG)
```

### RAG Commands

```bash
# Upload a PDF document
xpol ai rag upload path/to/document.pdf

# List uploaded documents
xpol ai rag list

# Search documents
xpol ai rag search "your query here"

# View statistics
xpol ai rag stats

# Start document chat TUI
xpol ai rag chat
```

## Configuration

### AI Provider Setup

The TUI requires an AI provider to be configured. Set up using:

```bash
# Interactive setup
xpol setup --interactive

# Or set environment variables
export AI_PROVIDER=openai  # or groq, anthropic
export OPENAI_API_KEY=your-key-here
export AI_MODEL=gpt-4o
```

### Supported Providers

- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5
- **Groq**: Llama 3, Mixtral
- **Anthropic**: Claude 3 (Opus, Sonnet, Haiku)

### Vector Databases (for Document Chat)

Install one of the following for RAG support:

```bash
# ChromaDB (recommended for local use)
pip install langchain-chroma

# Qdrant (for production)
pip install langchain-qdrant qdrant-client

# FAISS (for simple deployments)
pip install faiss-cpu
```

## Architecture

### Components

- **ChatApp**: Main TUI application using Textual framework
- **ChatMessage**: Individual message widget with markdown support
- **ChatHistory**: Scrollable message container
- **StatusBar**: Real-time status and provider information
- **ChatInput**: Multi-line input widget

### Design Principles

Inspired by `crustly` and `chabeau`, the TUI combines:
- **Markdown rendering** from Rich library
- **Syntax highlighting** for code blocks (Monokai theme)
- **Smooth scrolling** with automatic scroll-to-bottom
- **Theme support** with customizable colors
- **Keyboard-first UX** for terminal power users

## Examples

### AI Chat Examples

Ask questions like:
- "What are my top spending services?"
- "Show me cost trends over the last 30 days"
- "Which projects are over budget?"
- "Suggest cost optimization opportunities"

### Document Chat Examples

Query your documents:
- "What is our cloud migration strategy?"
- "Summarize the security requirements"
- "What are the cost optimization recommendations?"

## Troubleshooting

### TUI doesn't start

Check your Python version and dependencies:

```bash
python --version  # Should be 3.9+
pip install textual rich
```

### AI responses are slow

- Use faster models like `gpt-3.5-turbo` or `llama-3.1-8b-instant`
- Reduce dashboard data loading with `--no-load-data`

### Document chat returns no results

- Ensure documents are uploaded: `xpol ai rag list`
- Re-upload documents if needed: `xpol ai rag upload path/to/doc.pdf`
- Check vector database configuration

## Advanced Usage

### Custom Themes

The TUI uses Textual's built-in theming. Create a custom CSS file:

```css
/* custom_theme.css */
Screen {
    background: #1e1e2e;
}

ChatMessage.user-message {
    background: #89b4fa;
    border: tall #74c7ec;
}

ChatMessage.assistant-message {
    background: #a6e3a1;
    border: tall #94e2d5;
}
```

### Programmatic Access

Use the TUI programmatically:

```python
from xpol.cli.tui.chat_app import run_chat_app
from xpol.cli.ai.service import LLMService

llm_service = LLMService()
run_chat_app(
    llm_service=llm_service,
    mode="ai",
    dashboard_data=your_data
)
```

## Contributing

Contributions are welcome! The TUI is designed to be extensible:

1. Add new message types in `ChatMessage`
2. Create custom widgets by extending `Static`
3. Add keyboard shortcuts in `ChatApp.BINDINGS`
4. Implement new chat modes by extending `_process_message`

## License

MIT License - see LICENSE file for details.

## Related Projects

- **crustly**: Rust TUI AI coding assistant
- **chabeau**: Terminal chatbot with OpenAI API
- **textual**: Python TUI framework
- **rich**: Terminal formatting library

