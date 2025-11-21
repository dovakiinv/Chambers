from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, TextArea
from textual.containers import Vertical
from textual import events
from rich.markdown import Markdown
import asyncio
from typing import List, Dict
from .config import config
from .database import init_db, create_session, save_message, get_session_messages
from .coordinator import TurnCoordinator

class ChatInput(TextArea):
    """Custom TextArea that submits on Enter, inserts newline on Shift+Enter."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.show_line_numbers = False

    async def _on_key(self, event: events.Key) -> None:
        # Check for Submit triggers
        if event.key in ("ctrl+enter", "ctrl+s", "ctrl+j"): 
            # Note: ctrl+j is often the code for ctrl+enter in terminals
            event.stop()
            app = self.app
            if isinstance(app, ChambersApp):
                await app.submit_message(self.text)
                self.clear()
        
        # Check for explicit Newline (if strictly overriding)
        elif event.key == "enter":
            # Let default TextArea behavior handle it (which is newline)
            pass
            
        else:
            await super()._on_key(event)

class ChambersApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    RichLog {
        height: 1fr;
        border: solid green;
        background: $surface;
    }
    ChatInput {
        dock: bottom;
        height: 3;  /* Fixed height for input line */
        border: solid blue;
    }
    """
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+d", "toggle_dark", "Dark/Light"),
    ]

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.coordinator = None
        self.conversation_history: List[Dict[str, str]] = []

    async def on_mount(self) -> None:
        """Initialize DB, Session, and Coordinator on startup."""
        log = self.query_one(RichLog)
        
        # Debug Config Loading
        log.write("[dim]Checking keys...[/dim]")
        keys_status = []
        if config.anthropic_api_key: keys_status.append("Claude: [green]FOUND[/green]")
        else: keys_status.append("Claude: [red]MISSING[/red]")
        
        if config.google_api_key: keys_status.append("Gemini: [green]FOUND[/green]")
        else: keys_status.append("Gemini: [red]MISSING[/red]")
        
        if config.xai_api_key: keys_status.append("Grok: [green]FOUND[/green]")
        else: keys_status.append("Grok: [red]MISSING[/red]")
        
        log.write("Keys: " + " | ".join(keys_status))
        
        await init_db()
        self.session_id = await create_session()
        log.write(f"[bold green]Session Started:[/bold green] {self.session_id}")
        
        self.coordinator = TurnCoordinator(self.session_id)
        try:
            log.write("[yellow]Initializing Council...[/yellow]")
            await self.coordinator.initialize()
            log.write("[green]Council Ready.[/green]")
        except Exception as e:
            log.write(f"[bold red]Council Init Failed:[/bold red] {e}")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(markup=True, wrap=True)
        yield ChatInput()
        yield Footer()

    async def submit_message(self, text: str) -> None:
        """Handle user input submission."""
        if not text.strip() or not self.coordinator:
            return

        user_msg = text.strip()
        
        log = self.query_one(RichLog)
        
        # 1. Update UI & State
        log.write(f"[bold blue]Vinga:[/bold blue] {user_msg}")
        self.conversation_history.append({"role": "user", "content": user_msg})
        await save_message(self.session_id, "Vinga", user_msg)

        # 2. Streaming Callback
        current_speaker = None
        line_buffer = ""
        
        async def stream_callback(speaker, chunk):
            nonlocal current_speaker, line_buffer
            
            if speaker != current_speaker:
                if line_buffer:
                    log.write(line_buffer)
                    line_buffer = ""
                log.write(f"\n\n[bold yellow]🤖 {speaker.upper()}:[/bold yellow]")
                current_speaker = speaker
            
            line_buffer += chunk
            if "\n" in line_buffer:
                lines = line_buffer.split("\n")
                for line in lines[:-1]:
                    log.write(line)
                line_buffer = lines[-1]

        # 3. Trigger Round
        responses = await self.coordinator.run_round(
            self.conversation_history, 
            stream_callback=stream_callback
        )
        
        if line_buffer:
            log.write(line_buffer)
        
        # 4. Finalize
        for resp in responses:
            if resp["success"]:
                await save_message(self.session_id, resp["speaker"], resp["content"])

def main():
    app = ChambersApp()
    app.run()

if __name__ == "__main__":
    main()
