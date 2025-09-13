"""
Example client for testing SSE streaming API
"""
import asyncio
import json
from typing import AsyncIterator
import httpx
from httpx_sse import aconnect_sse
import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


async def stream_chat(message: str, api_url: str = "http://localhost:8000") -> AsyncIterator[dict]:
    """
    Stream chat responses from the API
    
    Args:
        message: User message
        api_url: API base URL
        
    Yields:
        Parsed SSE events
    """
    async with httpx.AsyncClient(timeout=60) as client:
        # Send chat request
        request_data = {
            "message": message,
            "stream": True
        }
        
        async with aconnect_sse(
            client,
            "POST",
            f"{api_url}/api/v1/chat",
            json=request_data,
            headers={"Content-Type": "application/json"}
        ) as event_source:
            async for sse in event_source.aiter_sse():
                if sse.data:
                    try:
                        data = json.loads(sse.data)
                        yield {"event": sse.event, "data": data}
                    except json.JSONDecodeError:
                        console.print(f"[red]Failed to parse: {sse.data}[/red]")


async def display_streaming_response(message: str):
    """Display streaming response with rich formatting"""
    console.print(f"\n[bold cyan]You:[/bold cyan] {message}\n")
    console.print("[bold green]Assistant:[/bold green]")
    
    accumulated_response = []
    
    with Live(console=console, refresh_per_second=10) as live:
        async for event in stream_chat(message):
            event_type = event["event"]
            data = event["data"]
            
            if event_type == "token":
                # Accumulate tokens
                accumulated_response.append(data["content"])
                # Update live display
                live.update(
                    Panel(
                        "".join(accumulated_response),
                        border_style="green",
                        padding=(1, 2)
                    )
                )
            
            elif event_type == "tool_start":
                console.print(f"\n[yellow]🔧 Using tool: {data['tool']}[/yellow]")
                if data.get("args"):
                    console.print(f"   Args: {data['args']}")
            
            elif event_type == "tool_end":
                console.print(f"[green]✓ Tool completed: {data['tool']}[/green]")
            
            elif event_type == "error":
                console.print(f"\n[red]❌ Error: {data['error']}[/red]")
                break
            
            elif event_type == "done":
                console.print("\n[dim]Stream complete[/dim]")
                break


async def test_non_streaming(message: str, api_url: str = "http://localhost:8000"):
    """Test non-streaming API endpoint"""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{api_url}/api/v1/chat",
            json={"message": message, "stream": False}
        )
        
        if response.status_code == 200:
            data = response.json()
            console.print(f"\n[bold green]Response:[/bold green]\n{data['response']}")
            console.print(f"\n[dim]Session ID: {data['session_id']}[/dim]")
        else:
            console.print(f"[red]Error: {response.status_code} - {response.text}[/red]")


@click.command()
@click.option("--message", "-m", help="Message to send", required=True)
@click.option("--api-url", default="http://localhost:8000", help="API URL")
@click.option("--stream/--no-stream", default=True, help="Enable streaming")
def main(message: str, api_url: str, stream: bool):
    """Test the Dylan Assistant API"""
    if stream:
        asyncio.run(display_streaming_response(message))
    else:
        asyncio.run(test_non_streaming(message, api_url))


if __name__ == "__main__":
    # Example usage:
    # python client_example.py -m "帮我查一下北京到上海的高铁"
    # python client_example.py -m "What's the weather in Beijing?"
    # python client_example.py -m "Search for Python tutorials"
    main()