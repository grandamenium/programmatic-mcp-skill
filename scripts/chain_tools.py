#!/usr/bin/env python3
"""Chain multiple MCP tool calls together in a pipeline.

This script demonstrates chaining tools from a filesystem MCP server.
Modify the pipeline() function for your use case.

Usage:
    python chain_tools.py <command> [args...]

Example:
    python chain_tools.py npx -y @modelcontextprotocol/server-filesystem /tmp
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def mcp_client(command: str, args: list[str], env: dict | None = None):
    """Reusable MCP client context manager."""
    server_params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def pipeline(command: str, args: list[str]):
    async with mcp_client(command, args) as session:
        # Step 1: List tools to see what's available
        tools = await session.list_tools()
        tool_names = [t.name for t in tools.tools]
        print(f"Available tools: {tool_names}\n")

        # Step 2: List the root directory
        if "list_directory" in tool_names:
            dir_result = await session.call_tool("list_directory", {"path": args[-1]})
            entries = dir_result.content[0].text if dir_result.content else ""
            print(f"Directory listing:\n{entries}\n")

            # Step 3: Read any .txt or .md files found
            if "read_file" in tool_names:
                for line in entries.split("\n"):
                    name = line.strip().lstrip("[FILE] ").lstrip("[DIR] ")
                    if name.endswith((".txt", ".md")):
                        path = f"{args[-1]}/{name}"
                        try:
                            read_result = await session.call_tool("read_file", {"path": path})
                            content = read_result.content[0].text if read_result.content else ""
                            print(f"--- {name} ({len(content)} chars) ---")
                            print(content[:500])
                            print()
                        except Exception as e:
                            print(f"Could not read {name}: {e}")

        print("Pipeline complete.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    asyncio.run(pipeline(command, args))


if __name__ == "__main__":
    main()
