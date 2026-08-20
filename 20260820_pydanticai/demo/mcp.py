from fastmcp.client.transports import StdioTransport, StreamableHttpTransport
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

agent = Agent(
    "ollama:qwen3.5:2b",
    toolsets=[
        MCPToolset(
            StdioTransport(command="uv", args=["run", "mcp_demo1.py"]),
        ),
        MCPToolset(
            StreamableHttpTransport("http://localhost:8000/mcp"),
        ),
    ],
)
