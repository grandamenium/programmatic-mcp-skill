# Programmatic MCP Tool Calling

A Claude Code skill that teaches you how to convert MCP server tools (normally called by an AI agent) into programmatically callable scripts - no AI in the loop required.

## What This Solves

When you connect an MCP server to Claude Code, tools are only accessible through the AI agent. This skill shows you how to call those same tools directly from Python/Node.js scripts, enabling:

- **Batch operations** - Call tools in loops without burning tokens
- **Chained pipelines** - Pass output from one tool as input to another
- **Scheduled automation** - Run MCP tools from cron jobs
- **Testing** - Validate MCP server behavior without an AI agent

## Quick Start

1. Install the skill in Claude Code
2. Run `/programmatic-mcp` and follow the guided workflow
3. Choose your MCP server and transport method
4. Get a working script that calls tools programmatically

## Installation

### As a Claude Code Skill

```bash
# Clone into your global skills directory
git clone https://github.com/jamesgoldbach/programmatic-mcp-skill.git ~/.claude/skills/programmatic-mcp
```

Or copy `SKILL.md` into `~/.claude/skills/programmatic-mcp/SKILL.md`.

### Helper Scripts

The `scripts/` directory contains ready-to-use templates:

- `scripts/call_tool.py` - Python MCP client for calling tools
- `scripts/call_tool.js` - Node.js MCP client for calling tools
- `scripts/chain_tools.py` - Python example of chaining multiple tool calls
- `scripts/discover_tools.py` - List all tools from an MCP server

## How It Works

MCP servers communicate via JSON-RPC 2.0 over stdio or HTTP. Normally, Claude Code acts as the MCP client. These scripts act as their own MCP client, connecting directly to the server process and calling tools programmatically.

```
Normal:     Claude Code -> MCP Client -> MCP Server -> Tool
Programmatic: Your Script -> MCP Client -> MCP Server -> Tool
```

## Requirements

- Python 3.11+ with `mcp` package, OR Node.js 18+ with `@modelcontextprotocol/sdk`
- The MCP server you want to call (same one configured in Claude Code)

## License

MIT
