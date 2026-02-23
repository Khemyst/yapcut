/* YapCut CEP Bridge — polls bridge dir, executes ExtendScript, writes responses */
/* global CSInterface */

(function () {
  "use strict";

  var cs = new CSInterface();
  var fs = require("fs");
  var path = require("path");
  var os = require("os");

  var BRIDGE_DIR = path.join(os.tmpdir(), "yapcut-premiere-bridge");
  var POLL_INTERVAL = 250; // ms

  var pollTimer = null;
  var commandCount = 0;
  var errorCount = 0;

  // ── DOM refs ───────────────────────────────────────────────────────

  var statusDot = document.getElementById("statusDot");
  var statusText = document.getElementById("statusText");
  var bridgeDirEl = document.getElementById("bridgeDir");
  var cmdCountEl = document.getElementById("cmdCount");
  var errCountEl = document.getElementById("errCount");
  var logArea = document.getElementById("logArea");
  var btnStart = document.getElementById("btnStart");
  var btnStop = document.getElementById("btnStop");

  // ── Logging ────────────────────────────────────────────────────────

  function log(msg, cls) {
    var entry = document.createElement("div");
    entry.className = "log-entry" + (cls ? " " + cls : "");
    var now = new Date();
    var ts = pad2(now.getHours()) + ":" + pad2(now.getMinutes()) + ":" + pad2(now.getSeconds());
    entry.textContent = "[" + ts + "] " + msg;
    logArea.appendChild(entry);
    logArea.scrollTop = logArea.scrollHeight;
  }

  function pad2(n) {
    return (n < 10 ? "0" : "") + n;
  }

  window.clearLog = function () {
    logArea.innerHTML = "";
  };

  // ── Atomic file write (write .tmp then rename) ─────────────────────

  function atomicWriteJSON(filePath, data) {
    var tmpPath = filePath + ".tmp";
    fs.writeFileSync(tmpPath, JSON.stringify(data), "utf-8");
    fs.renameSync(tmpPath, filePath);
  }

  // ── Ensure bridge dir exists ───────────────────────────────────────

  function ensureBridgeDir() {
    if (!fs.existsSync(BRIDGE_DIR)) {
      fs.mkdirSync(BRIDGE_DIR, { recursive: true });
    }
    // Truncate path for display
    var display = BRIDGE_DIR;
    if (display.length > 35) {
      display = "..." + display.slice(-32);
    }
    bridgeDirEl.textContent = display;
    bridgeDirEl.title = BRIDGE_DIR;
  }

  // ── Process a single command file ──────────────────────────────────

  function processCommandFile(filename) {
    var cmdPath = path.join(BRIDGE_DIR, filename);
    var raw, cmd;

    try {
      raw = fs.readFileSync(cmdPath, "utf-8");
      cmd = JSON.parse(raw);
    } catch (e) {
      log("Failed to read command: " + filename + " — " + e.message, "err");
      errorCount++;
      errCountEl.textContent = errorCount;
      // Remove bad file
      try { fs.unlinkSync(cmdPath); } catch (_) {}
      return;
    }

    var id = cmd.id;
    var script = cmd.script;

    if (!id || !script) {
      log("Invalid command (missing id or script): " + filename, "err");
      try { fs.unlinkSync(cmdPath); } catch (_) {}
      return;
    }

    commandCount++;
    cmdCountEl.textContent = commandCount;

    // Extract a short label from the script for logging
    var label = id.substring(0, 8);
    log("Executing command " + label + "...", "cmd");

    // Delete command file before executing (so we don't re-process on next poll)
    try { fs.unlinkSync(cmdPath); } catch (_) {}

    // Execute via evalScript
    cs.evalScript(script, function (result) {
      var responsePath = path.join(BRIDGE_DIR, "response-" + id + ".json");

      if (result === "EvalScript error.") {
        log("ExtendScript error for " + label, "err");
        errorCount++;
        errCountEl.textContent = errorCount;
        atomicWriteJSON(responsePath, { id: id, error: "EvalScript error — check ExtendScript syntax" });
      } else {
        log("Response for " + label + " (" + (result ? result.length : 0) + " chars)", "ok");
        atomicWriteJSON(responsePath, { id: id, result: result || "" });
      }
    });
  }

  // ── Poll loop ──────────────────────────────────────────────────────

  function poll() {
    var files;
    try {
      files = fs.readdirSync(BRIDGE_DIR);
    } catch (e) {
      // Bridge dir may have been deleted
      ensureBridgeDir();
      return;
    }

    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      if (f.indexOf("command-") === 0 && f.indexOf(".json") === f.length - 5) {
        processCommandFile(f);
      }
    }
  }

  // ── Start / Stop ──────────────────────────────────────────────────

  window.startPolling = function () {
    if (pollTimer) return;

    ensureBridgeDir();
    pollTimer = setInterval(poll, POLL_INTERVAL);

    statusDot.className = "status-dot polling";
    statusText.textContent = "Polling";
    btnStart.disabled = true;
    btnStop.disabled = false;
    btnStart.classList.add("active");

    log("Bridge polling started — " + BRIDGE_DIR, "ok");
  };

  window.stopPolling = function () {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }

    statusDot.className = "status-dot stopped";
    statusText.textContent = "Stopped";
    btnStart.disabled = false;
    btnStop.disabled = true;
    btnStart.classList.remove("active");

    log("Bridge polling stopped", "err");
  };

  // ── Auto-start on panel load ───────────────────────────────────────

  ensureBridgeDir();
  log("YapCut Bridge CEP panel loaded", "ok");
  window.startPolling();

})();
