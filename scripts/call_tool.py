#!/usr/bin/env python3
"""Call a single MCP tool programmatically.

Usage:
    python call_tool.py <tool_name> '<json_args>' -- <command> [args...]

Examples:
    python call_tool.py read_file '{"path": "/tmp/test.txt"}' -- npx -y @modelcontextprotocol/server-filesystem /tmp
    python call_tool.py list_directory '{"path": "/tmp"}' -- npx -y @modelcontextprotocol/server-filesystem /tmp
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call_tool(tool_name: str, arguments: dict, command: str, args: list[str]):
    server_params = StdioServerParameters(command=command, args=args, env=None)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(tool_name, arguments=arguments)

            if result.isError:
                print(f"ERROR: Tool call failed", file=sys.stderr)
                for content in result.content:
                    text = content.text if hasattr(content, "text") else str(content)
                    print(text, file=sys.stderr)
                sys.exit(1)

            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)
                else:
                    print(json.dumps(content.model_dump(), indent=2))


def main():
    if "--" not in sys.argv:
        print(__doc__)
        sys.exit(1)

    sep = sys.argv.index("--")
    before = sys.argv[1:sep]
    after = sys.argv[sep + 1 :]

    if len(before) < 2 or len(after) < 1:
        print(__doc__)
        sys.exit(1)

    tool_name = before[0]
    arguments = json.loads(before[1])
    command = after[0]
    args = after[1:]

    asyncio.run(call_tool(tool_name, arguments, command, args))


if __name__ == "__main__":
    main()
