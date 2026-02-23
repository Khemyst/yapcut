import { sendScript } from "./bridge.js";

// ── ExtendScript generators ────────────────────────────────────────────
// ALL scripts must be ES3 compatible: no arrow functions, no let/const,
// no template literals, no Array.prototype.map/filter/forEach.

function makeGetSequenceInfoScript(): string {
  return `
(function() {
  var seq = app.project.activeSequence;
  if (!seq) return JSON.stringify({ error: "No active sequence" });

  var frTicks = parseFloat(seq.getSettings().videoFrameRate.ticks);
  var fps = Math.round(254016000000 / frTicks * 100) / 100;

  var result = {
    name: seq.name,
    duration: seq.end,
    videoTrackCount: seq.videoTracks.numTracks,
    audioTrackCount: seq.audioTracks.numTracks,
    frameSizeH: seq.frameSizeHorizontal,
    frameSizeV: seq.frameSizeVertical,
    fps: fps,
    timebaseTicks: seq.getSettings().videoFrameRate.ticks
  };
  return JSON.stringify(result);
})()`;
}

function makeGetMarkersScript(): string {
  return `
(function() {
  var seq = app.project.activeSequence;
  if (!seq) return JSON.stringify({ error: "No active sequence" });

  var clip = seq.videoTracks[0].clips[0];
  if (!clip) return JSON.stringify({ error: "No clip on V1" });

  var markers = clip.projectItem.getMarkers();
  if (!markers || markers.numMarkers === 0) {
    return JSON.stringify({ markers: [], count: 0 });
  }

  var result = [];
  var marker = markers.getFirstMarker();
  while (marker) {
    var startTicks = parseFloat(marker.start.ticks);
    var endTicks = parseFloat(marker.end.ticks);
    var startSecs = startTicks / 254016000000;
    var endSecs = endTicks / 254016000000;

    result.push({
      name: marker.name,
      comment: marker.comments,
      startSeconds: Math.round(startSecs * 100) / 100,
      endSeconds: Math.round(endSecs * 100) / 100,
      startTicks: marker.start.ticks,
      endTicks: marker.end.ticks
    });
    marker = markers.getNextMarker(marker);
  }
  return JSON.stringify({ markers: result, count: result.length });
})()`;
}

function makeColorMarkersScript(): string {
  // Colors from proven premiere_marker_razor.jsx
  return `
(function() {
  var COLOR = {
    "KEEP": 0,
    "REACTION": 0,
    "CONTEXT": 2,
    "MAYBE": 4,
    "CUT": 1,
    "MOMENT": 6
  };
  var DEFAULT_COLOR = 3;

  var seq = app.project.activeSequence;
  if (!seq) return JSON.stringify({ error: "No active sequence" });

  var clip = seq.videoTracks[0].clips[0];
  if (!clip) return JSON.stringify({ error: "No clip on V1" });

  var markers = clip.projectItem.getMarkers();
  if (!markers || markers.numMarkers === 0) {
    return JSON.stringify({ error: "No markers found on clip" });
  }

  var colorCount = 0;
  var errors = [];
  var marker = markers.getFirstMarker();

  while (marker) {
    var name = marker.name || "";
    var m = name.match(/^\\[([A-Z]+)\\]/);
    var prefix = m ? m[1] : null;
    var colorIdx = (prefix && COLOR[prefix] !== undefined) ? COLOR[prefix] : DEFAULT_COLOR;

    try {
      marker.setColorByIndex(colorIdx, 65535);
      colorCount++;
    } catch(e) {
      errors.push(name + ": " + e.message);
    }

    marker = markers.getNextMarker(marker);
  }

  return JSON.stringify({
    colored: colorCount,
    errors: errors
  });
})()`;
}

function makeRazorAtBoundariesScript(timebase: number): string {
  // Directly based on proven premiere_marker_razor.jsx razor logic
  return `
(function() {
  app.enableQE();

  var TIMEBASE = ${timebase};

  function pad2(n) {
    return (n < 10 ? "0" : "") + n;
  }

  function secondsToTimecode(secs) {
    var totalFrames = Math.round(secs * TIMEBASE);
    var h = Math.floor(totalFrames / (TIMEBASE * 3600));
    totalFrames %= (TIMEBASE * 3600);
    var m = Math.floor(totalFrames / (TIMEBASE * 60));
    totalFrames %= (TIMEBASE * 60);
    var s = Math.floor(totalFrames / TIMEBASE);
    var f = totalFrames % TIMEBASE;
    return pad2(h) + ":" + pad2(m) + ":" + pad2(s) + ":" + pad2(f);
  }

  function ticksToSeconds(ticks) {
    return parseFloat(ticks) / 254016000000;
  }

  var seq = app.project.activeSequence;
  var qeSeq = qe.project.getActiveSequence();

  if (!seq || !qeSeq) return JSON.stringify({ error: "No active sequence" });

  var clip = seq.videoTracks[0].clips[0];
  if (!clip) return JSON.stringify({ error: "No clip on V1" });

  var markers = clip.projectItem.getMarkers();
  if (!markers || markers.numMarkers === 0) {
    return JSON.stringify({ error: "No markers found on clip" });
  }

  var editPointSet = {};
  var marker = markers.getFirstMarker();

  while (marker) {
    var startSecs = ticksToSeconds(marker.start.ticks);
    var endSecs = ticksToSeconds(marker.end.ticks);
    var startTC = secondsToTimecode(startSecs);
    var endTC = secondsToTimecode(endSecs);
    editPointSet[startTC] = startSecs;
    editPointSet[endTC] = endSecs;
    marker = markers.getNextMarker(marker);
  }

  var editPoints = [];
  for (var tc in editPointSet) {
    editPoints.push({ tc: tc, secs: editPointSet[tc] });
  }
  editPoints.sort(function(a, b) { return a.secs - b.secs; });

  var seqDurSecs = ticksToSeconds(seq.end);
  var filtered = [];
  for (var fi = 0; fi < editPoints.length; fi++) {
    if (editPoints[fi].secs > 0.5 && editPoints[fi].secs < (seqDurSecs - 0.5)) {
      filtered.push(editPoints[fi]);
    }
  }
  editPoints = filtered;

  var numVT = qeSeq.numVideoTracks;
  var numAT = qeSeq.numAudioTracks;
  var cutOk = 0;
  var cutFail = 0;

  for (var i = 0; i < editPoints.length; i++) {
    var tc = editPoints[i].tc;
    var ticks = String(Math.round(editPoints[i].secs * 254016000000));
    seq.setPlayerPosition(ticks);

    for (var vi = 0; vi < numVT; vi++) {
      try {
        qeSeq.getVideoTrackAt(vi).razor(tc);
        cutOk++;
      } catch(e) {
        cutFail++;
      }
    }

    for (var ai = 0; ai < numAT; ai++) {
      try {
        qeSeq.getAudioTrackAt(ai).razor(tc);
        cutOk++;
      } catch(e) {
        cutFail++;
      }
    }

    if (i % 10 === 9) {
      $.sleep(100);
    }
  }

  return JSON.stringify({
    editPoints: editPoints.length,
    razorOk: cutOk,
    razorFail: cutFail,
    videoTracks: numVT,
    audioTracks: numAT
  });
})()`;
}

function makeGetTrackInfoScript(): string {
  return `
(function() {
  var seq = app.project.activeSequence;
  if (!seq) return JSON.stringify({ error: "No active sequence" });

  var tracks = [];

  for (var vi = 0; vi < seq.videoTracks.numTracks; vi++) {
    var vt = seq.videoTracks[vi];
    var clips = [];
    for (var ci = 0; ci < vt.clips.numItems; ci++) {
      var c = vt.clips[ci];
      clips.push({
        name: c.name,
        startTicks: c.start.ticks,
        endTicks: c.end.ticks
      });
    }
    tracks.push({
      name: "V" + (vi + 1),
      type: "video",
      clipCount: vt.clips.numItems,
      clips: clips
    });
  }

  for (var ai = 0; ai < seq.audioTracks.numTracks; ai++) {
    var at = seq.audioTracks[ai];
    var aClips = [];
    for (var aci = 0; aci < at.clips.numItems; aci++) {
      var ac = at.clips[aci];
      aClips.push({
        name: ac.name,
        startTicks: ac.start.ticks,
        endTicks: ac.end.ticks
      });
    }
    tracks.push({
      name: "A" + (ai + 1),
      type: "audio",
      clipCount: at.clips.numItems,
      clips: aClips
    });
  }

  return JSON.stringify({ tracks: tracks });
})()`;
}

// ── Tool dispatcher ────────────────────────────────────────────────────

export async function executeTool(
  name: string,
  args: Record<string, unknown>
): Promise<string> {
  let script: string;
  let isRazor = false;

  switch (name) {
    case "get_sequence_info":
      script = makeGetSequenceInfoScript();
      break;
    case "get_markers":
      script = makeGetMarkersScript();
      break;
    case "color_markers":
      script = makeColorMarkersScript();
      break;
    case "razor_at_boundaries": {
      const timebase = typeof args.timebase === "number" ? args.timebase : 30;
      script = makeRazorAtBoundariesScript(timebase);
      isRazor = true;
      break;
    }
    case "get_track_info":
      script = makeGetTrackInfoScript();
      break;
    default:
      throw new Error(`Unknown tool: ${name}`);
  }

  return sendScript(script, isRazor);
}
