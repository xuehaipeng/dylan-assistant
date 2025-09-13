"""
Simple test script for Dylan Assistant
"""
import asyncio
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv()

console = Console()


async def test_workflow():
    """Test the workflow directly without API"""
    from src.workflows.assistant import AssistantWorkflow
    
    console.print(Panel(
        "[bold cyan]Dylan Assistant Test[/bold cyan]\n"
        "Testing workflow components directly",
        title="Test Suite",
        border_style="cyan"
    ))
    
    # Initialize workflow
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing workflow...", total=None)
        
        workflow = AssistantWorkflow()
        
        progress.update(task, description="Workflow ready!")
    
    # Test queries
    test_messages = [
        "帮我查一下日照去泰安是否有高铁动车",
        "What's the weather in Beijing?",
        "Calculate 123 * 456",
        "What time is it now?",
        "Search for Python LangGraph tutorials"
    ]
    
    for message in test_messages:
        console.print(f"\n[bold cyan]Query:[/bold cyan] {message}")
        
        response_parts = []
        
        try:
            async for chunk in workflow.run(message):
                if chunk["type"] == "token":
                    response_parts.append(chunk["content"])
                elif chunk["type"] == "tool_start":
                    console.print(f"[yellow]→ Using tool: {chunk['tool']}[/yellow]")
                elif chunk["type"] == "tool_end":
                    console.print(f"[green]✓ Tool completed[/green]")
            
            response = "".join(response_parts)
            console.print(Panel(
                response,
                title="Response",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        
        # Small delay between queries
        await asyncio.sleep(1)


async def test_mcp_integration():
    """Test MCP integration directly"""
    from src.integrations.mcp_integration import MCPToolManager
    
    console.print("\n[bold]Testing MCP Integration[/bold]")
    
    mcp_manager = MCPToolManager()
    
    # Test AMap query
    query = "帮我查一下北京到上海的高铁时刻表"
    console.print(f"\n[cyan]MCP Query:[/cyan] {query}")
    
    result = await mcp_manager.query(query)
    console.print(Panel(result, title="MCP Result", border_style="yellow"))


async def test_api_server():
    """Test API server endpoints"""
    import httpx
    
    console.print("\n[bold]Testing API Endpoints[/bold]")
    
    api_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        try:
            response = await client.get(f"{api_url}/health")
            if response.status_code == 200:
                console.print("[green]✓ Health check passed[/green]")
                console.print(f"  {response.json()}")
            else:
                console.print("[red]✗ Health check failed[/red]")
        except httpx.ConnectError:
            console.print("[yellow]⚠ API server not running[/yellow]")
            console.print("  Start the server with: python -m src.api.main")
            return
        
        # Test chat endpoint
        test_message = "Hello, how are you?"
        console.print(f"\n[cyan]Testing chat:[/cyan] {test_message}")
        
        response = await client.post(
            f"{api_url}/api/v1/chat",
            json={"message": test_message, "stream": False}
        )
        
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Response:[/green] {data['response']}")
        else:
            console.print(f"[red]Error: {response.status_code}[/red]")


async def main():
    """Run all tests"""
    console.print(Panel(
        "[bold]Dylan Assistant Test Suite[/bold]\n"
        "Testing all components",
        title="🧪 Tests",
        border_style="bold cyan"
    ))
    
    # Test workflow
    await test_workflow()
    
    # Test MCP
    await test_mcp_integration()
    
    # Test API (if server is running)
    await test_api_server()
    
    console.print("\n[bold green]✓ All tests completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())