import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { v4 as uuidv4 } from "uuid";

const BRIDGE_DIR = path.join(os.tmpdir(), "yapcut-premiere-bridge");
const POLL_INTERVAL_MS = 200;
const DEFAULT_TIMEOUT_MS = 30_000;
const RAZOR_TIMEOUT_MS = 120_000;
const STALE_AGE_MS = 5 * 60 * 1000; // 5 minutes

export interface BridgeCommand {
  id: string;
  script: string;
}

export interface BridgeResponse {
  id: string;
  result?: string;
  error?: string;
}

/** Ensure bridge directory exists */
export function ensureBridgeDir(): string {
  if (!fs.existsSync(BRIDGE_DIR)) {
    fs.mkdirSync(BRIDGE_DIR, { recursive: true });
  }
  return BRIDGE_DIR;
}

/** Remove stale command/response files older than STALE_AGE_MS */
export function cleanupStaleFiles(): void {
  const dir = ensureBridgeDir();
  const now = Date.now();

  let files: string[];
  try {
    files = fs.readdirSync(dir);
  } catch {
    return;
  }

  for (const file of files) {
    if (!file.endsWith(".json") && !file.endsWith(".tmp")) continue;
    const filePath = path.join(dir, file);
    try {
      const stat = fs.statSync(filePath);
      if (now - stat.mtimeMs > STALE_AGE_MS) {
        fs.unlinkSync(filePath);
      }
    } catch {
      // File may have been deleted by another process
    }
  }
}

/** Write a command file atomically (write .tmp then rename to .json) */
function writeCommandFile(cmd: BridgeCommand): void {
  const dir = ensureBridgeDir();
  const tmpPath = path.join(dir, `command-${cmd.id}.tmp`);
  const finalPath = path.join(dir, `command-${cmd.id}.json`);

  fs.writeFileSync(tmpPath, JSON.stringify(cmd), "utf-8");
  fs.renameSync(tmpPath, finalPath);
}

/** Poll for a response file, return parsed response */
function pollForResponse(id: string, timeoutMs: number): Promise<BridgeResponse> {
  const dir = ensureBridgeDir();
  const responsePath = path.join(dir, `response-${id}.json`);

  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const interval = setInterval(() => {
      if (Date.now() - startTime > timeoutMs) {
        clearInterval(interval);
        // Clean up the command file if it still exists
        const cmdPath = path.join(dir, `command-${id}.json`);
        try { fs.unlinkSync(cmdPath); } catch { /* ignore */ }
        reject(new Error(`Bridge timeout after ${timeoutMs / 1000}s — is the YapCut CEP panel running in Premiere Pro?`));
        return;
      }

      try {
        if (fs.existsSync(responsePath)) {
          const raw = fs.readFileSync(responsePath, "utf-8");
          const response: BridgeResponse = JSON.parse(raw);

          // Clean up response file
          try { fs.unlinkSync(responsePath); } catch { /* ignore */ }

          clearInterval(interval);
          resolve(response);
        }
      } catch {
        // File might be partially written, try again next poll
      }
    }, POLL_INTERVAL_MS);
  });
}

/**
 * Send an ExtendScript string to Premiere Pro via the file bridge.
 * Returns the result string from evalScript.
 */
export async function sendScript(script: string, isRazor = false): Promise<string> {
  const id = uuidv4();
  const timeoutMs = isRazor ? RAZOR_TIMEOUT_MS : DEFAULT_TIMEOUT_MS;

  const cmd: BridgeCommand = { id, script };
  writeCommandFile(cmd);

  const response = await pollForResponse(id, timeoutMs);

  if (response.error) {
    throw new Error(`Premiere ExtendScript error: ${response.error}`);
  }

  return response.result ?? "";
}

/** Get the bridge directory path (for display/diagnostics) */
export function getBridgeDir(): string {
  return BRIDGE_DIR;
}
