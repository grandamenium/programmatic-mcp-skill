#!/usr/bin/env node
/**
 * Call a single MCP tool programmatically using Node.js.
 *
 * Usage:
 *   node call_tool.js <tool_name> '<json_args>' -- <command> [args...]
 *
 * Examples:
 *   node call_tool.js read_file '{"path": "/tmp/test.txt"}' -- npx -y @modelcontextprotocol/server-filesystem /tmp
 *   node call_tool.js list_directory '{"path": "/tmp"}' -- npx -y @modelcontextprotocol/server-filesystem /tmp
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function callTool(toolName, args, command, commandArgs) {
  const transport = new StdioClientTransport({
    command,
    args: commandArgs,
  });

  const client = new Client({ name: "call-tool-script", version: "1.0.0" });
  await client.connect(transport);

  try {
    const result = await client.callTool({ name: toolName, arguments: args });
    for (const content of result.content) {
      if (content.type === "text") {
        console.log(content.text);
      } else {
        console.log(JSON.stringify(content, null, 2));
      }
    }
  } finally {
    await client.close();
  }
}

// Parse CLI args
const argv = process.argv.slice(2);
const sepIndex = argv.indexOf("--");

if (sepIndex === -1 || sepIndex < 2) {
  console.log("Usage: node call_tool.js <tool_name> '<json_args>' -- <command> [args...]");
  process.exit(1);
}

const toolName = argv[0];
const toolArgs = JSON.parse(argv[1]);
const command = argv[sepIndex + 1];
const commandArgs = argv.slice(sepIndex + 2);

callTool(toolName, toolArgs, command, commandArgs).catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
