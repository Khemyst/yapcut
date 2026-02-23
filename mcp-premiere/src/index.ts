#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { executeTool } from "./tools.js";
import { ensureBridgeDir, cleanupStaleFiles, getBridgeDir } from "./bridge.js";

const server = new McpServer({
  name: "yapcut-premiere",
  version: "1.0.0",
});

// Helper: execute a tool and format the MCP response
async function handleTool(name: string, args: Record<string, unknown>) {
  try {
    const result = await executeTool(name, args);

    let parsed: unknown;
    try {
      parsed = JSON.parse(result);
    } catch {
      parsed = null;
    }

    if (parsed && typeof parsed === "object" && parsed !== null && "error" in parsed) {
      return {
        content: [{ type: "text" as const, text: JSON.stringify(parsed, null, 2) }],
        isError: true,
      };
    }

    return {
      content: [{ type: "text" as const, text: parsed ? JSON.stringify(parsed, null, 2) : result }],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text" as const, text: JSON.stringify({ error: message }, null, 2) }],
      isError: true,
    };
  }
}

// Register tools

server.tool(
  "get_sequence_info",
  "Get info about the active Premiere Pro sequence: name, duration, track counts, frame size",
  async () => handleTool("get_sequence_info", {})
);

server.tool(
  "get_markers",
  "Get all markers from the first clip on V1 of the active sequence. Returns marker names, comments, and time positions.",
  async () => handleTool("get_markers", {})
);

server.tool(
  "color_markers",
  "Color all markers on V1 clip by their [PREFIX] type. KEEP/REACTION=Green, CUT=Red, CONTEXT=Purple, MAYBE=Yellow, MOMENT=Blue.",
  async () => handleTool("color_markers", {})
);

// Use registerTool to declare the timebase parameter schema for MCP clients.
// The deprecated tool() 4-arg overload triggers TS2589 (deep type instantiation)
// with Zod schemas in MCP SDK v1.26, so registerTool is the correct API anyway.
const razorInputSchema = { timebase: z.number().describe("Sequence frame rate timebase (default: 30 for 29.97fps)") };
server.registerTool(
  "razor_at_boundaries",
  {
    description: "Razor-cut ALL tracks at every marker in/out boundary on V1 clip. Creates physical edit points at every marker start and end.",
    inputSchema: razorInputSchema,
  },
  // @ts-expect-error — TS2589 deep instantiation on ToolCallback<typeof razorInputSchema>
  async (args: { timebase: number }) => handleTool("razor_at_boundaries", args)
);

server.tool(
  "get_track_info",
  "Get detailed track info: clip counts and clip names/positions for all video and audio tracks in the active sequence.",
  async () => handleTool("get_track_info", {})
);

async function main() {
  ensureBridgeDir();
  cleanupStaleFiles();

  const bridgeDir = getBridgeDir();
  process.stderr.write(`[yapcut-premiere] MCP server starting\n`);
  process.stderr.write(`[yapcut-premiere] Bridge directory: ${bridgeDir}\n`);

  const transport = new StdioServerTransport();
  await server.connect(transport);

  process.stderr.write(`[yapcut-premiere] MCP server connected via stdio\n`);
}

main().catch((error) => {
  process.stderr.write(`[yapcut-premiere] Fatal error: ${error}\n`);
  process.exit(1);
});
