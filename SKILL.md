---
name: programmatic-mcp
description: Convert MCP server tools into programmatically callable scripts. Use when the user wants to call MCP tools from scripts, automate MCP tool calls, chain MCP tools together, or bypass the AI agent for direct tool execution.
---

# Programmatic MCP Tool Calling

Convert any MCP server connected to Claude Code into programmatically callable tools that run from scripts - no AI agent in the loop.

## Concepts

### Normal MCP (AI-mediated)
Claude Code connects to MCP servers and calls tools on your behalf. Every tool call goes through the LLM, consuming tokens and adding latency.

### Programmatic MCP (Script-mediated)
Your script acts as its own MCP client, connecting directly to the MCP server process via the same protocol (JSON-RPC 2.0 over stdio or HTTP). The AI agent is removed from the loop entirely.

```
Normal:       User -> Claude Code -> MCP Client -> MCP Server -> Tool Result -> Claude Code -> User
Programmatic: Your Script -> MCP Client -> MCP Server -> Tool Result -> Your Script
```

### When to Use Programmatic Calling
- Batch operations (calling the same tool 100 times)
- Pipelines (output of tool A feeds into tool B)
- Scheduled jobs (cron, CI/CD)
- Testing MCP servers
- Reducing token usage for repetitive operations

---

## Workflow 1: Convert MCP Server to Programmatic Script

### Step 1: Identify the MCP Server Config

Find the server's configuration. Check these locations:

```bash
# Project-level config
cat .mcp.json

# User-level config (Claude Code)
cat ~/.claude/settings.json

# Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

You need the `command`, `args`, and `env` from the server config. Example:

```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
      "env": {}
    }
  }
}
```

### Step 2: Choose Your Language

**Python (Recommended)** - Uses the official `mcp` SDK:
```bash
pip install mcp
# or
uv pip install mcp
```

**Node.js** - Uses the official `@modelcontextprotocol/sdk`:
```bash
npm install @modelcontextprotocol/sdk
```

### Step 3: Discover Available Tools

Run the discovery script to see what tools the server exposes:

**Python:**
```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def discover():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"\n{tool.name}: {tool.description}")
                if tool.inputSchema:
                    props = tool.inputSchema.get("properties", {})
                    required = tool.inputSchema.get("required", [])
                    for prop_name, prop_info in props.items():
                        req = " (required)" if prop_name in required else ""
                        print(f"  - {prop_name}: {prop_info.get('type', 'any')}{req}")

asyncio.run(discover())
```

### Step 4: Call a Tool Programmatically

**Python:**
```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call_tool(tool_name: str, arguments: dict):
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            for content in result.content:
                print(content.text if hasattr(content, 'text') else content)
            return result

# Example: Read a file
asyncio.run(call_tool("read_file", {"path": "/Users/me/projects/README.md"}))
```

**Node.js:**
```javascript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function callTool(toolName, args) {
  const transport = new StdioClientTransport({
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
  });

  const client = new Client({ name: "my-script", version: "1.0.0" });
  await client.connect(transport);

  const result = await client.callTool({ name: toolName, arguments: args });
  console.log(JSON.stringify(result, null, 2));

  await client.close();
}

callTool("read_file", { path: "/Users/me/projects/README.md" });
```

### Step 5: Disconnect / Cleanup

The MCP server process is managed by the script's connection lifecycle:

- **Python**: The `async with` context managers handle cleanup automatically. When the block exits, the stdio transport closes and the server subprocess is terminated.
- **Node.js**: Call `await client.close()` to disconnect and terminate the server process.
- **No need to modify Claude Code config**: Your script spawns its own server process. Claude Code's MCP connection is completely separate.

If you want to stop Claude Code's connection to the server (independent of your script):
```bash
# Remove from Claude Code
claude mcp remove <server-name>

# Or delete from .mcp.json / settings.json manually
```

---

## Workflow 2: Chain Multiple Tool Calls Together

Once you can call tools programmatically, you can chain them - passing output from one tool as input to the next.

### Pattern: Sequential Pipeline

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def chain_tools():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: List directory
            dir_result = await session.call_tool("list_directory", {"path": "/Users/me/projects"})
            files = [c.text for c in dir_result.content]
            print(f"Found files: {files}")

            # Step 2: Read each file and collect contents
            for file_info in files:
                # Parse filenames from the directory listing
                filename = file_info.strip()
                if filename.endswith(".md"):
                    read_result = await session.call_tool("read_file", {
                        "path": f"/Users/me/projects/{filename}"
                    })
                    content = read_result.content[0].text
                    print(f"\n--- {filename} ({len(content)} chars) ---")
                    print(content[:200])

asyncio.run(chain_tools())
```

### Pattern: Cross-Server Chaining

Call tools from different MCP servers in the same script:

```python
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def cross_server_chain():
    exit_stack = AsyncExitStack()

    async with exit_stack:
        # Connect to server A (filesystem)
        fs_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
        )
        fs_read, fs_write = await exit_stack.enter_async_context(stdio_client(fs_params))
        fs_session = await exit_stack.enter_async_context(ClientSession(fs_read, fs_write))
        await fs_session.initialize()

        # Connect to server B (e.g. a database server)
        db_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sqlite", "/Users/me/data.db"],
        )
        db_read, db_write = await exit_stack.enter_async_context(stdio_client(db_params))
        db_session = await exit_stack.enter_async_context(ClientSession(db_read, db_write))
        await db_session.initialize()

        # Chain: Read file from server A, then query server B with the content
        file_result = await fs_session.call_tool("read_file", {"path": "/Users/me/projects/query.sql"})
        sql_query = file_result.content[0].text

        db_result = await db_session.call_tool("read_query", {"query": sql_query})
        print(db_result.content[0].text)

asyncio.run(cross_server_chain())
```

### Pattern: Batch Operations with Error Handling

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def batch_operations(items: list[dict]):
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            results = []
            for item in items:
                try:
                    result = await session.call_tool(item["tool"], item["args"])
                    results.append({"status": "ok", "result": result.content})
                except Exception as e:
                    results.append({"status": "error", "error": str(e)})
                    print(f"Failed {item['tool']}: {e}")

            return results

# Batch read multiple files
operations = [
    {"tool": "read_file", "args": {"path": "/Users/me/projects/README.md"}},
    {"tool": "read_file", "args": {"path": "/Users/me/projects/package.json"}},
    {"tool": "read_file", "args": {"path": "/Users/me/projects/tsconfig.json"}},
]
asyncio.run(batch_operations(operations))
```

---

## Reusable MCP Client Wrapper

For repeated use, wrap the connection logic:

```python
import asyncio
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


async def main():
    async with mcp_client("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]) as session:
        tools = await session.list_tools()
        print(f"Available: {[t.name for t in tools.tools]}")

        result = await session.call_tool("list_directory", {"path": "/tmp"})
        print(result.content[0].text)

asyncio.run(main())
```

---

## Troubleshooting

### "Server process exited"
The MCP server command failed to start. Verify the command works manually:
```bash
npx -y @modelcontextprotocol/server-filesystem /tmp
```

### "Tool not found"
Run the discovery script first to see exact tool names. Names are case-sensitive.

### Environment variables missing
Pass env vars through the StdioServerParameters:
```python
server_params = StdioServerParameters(
    command="npx",
    args=["-y", "my-mcp-server"],
    env={"API_KEY": "your-key", "PATH": os.environ["PATH"]}
)
```
Note: You typically need to include `PATH` in the env dict so the subprocess can find executables.

### Connection hangs
Some MCP servers require specific initialization. Check if the server needs environment variables or config files to be present.

---

## Reference Links

- [MCP Specification](https://modelcontextprotocol.io/specification/latest)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [mcptools CLI](https://github.com/f/mcptools) - Shell-level MCP tool calling
- [PTC-MCP](https://github.com/gallanoe/ptc-mcp) - Batched programmatic calls via Claude Code
