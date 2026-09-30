from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

mcp = FastMCP("MyServer", providers=[FileSystemProvider(Path(__file__).parent / "app")])

if __name__ == "__main__":
    mcp.run(transport="http")