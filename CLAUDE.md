# YapCut

YapCut is a conversational video editing workflow. The human describes what they want from an edit, Claude reads the transcript, they discuss it, and Claude outputs an FCP XML file with spanned markers (or physical edit points) that Premiere Pro imports.

## How the Workflow Operates

1. Claude reads `EDITORIAL_MEMORY.md` (if it exists) to calibrate to the editor's preferences
2. The human provides a **timecoded transcript** (JSON) and optionally a **YouTube chat log** (JSON)
3. The human briefs Claude: stream context, target output, tone, priority moments, preset selection
4. Claude reads the transcript and understands the content
5. They discuss — Claude proposes segments, the human refines
6. Claude generates an **FCP 7 XML** file with spanned markers on the VOD clipitem
7. Claude runs `python tools/validate_xml.py output/filename.xml` to validate
8. The human imports the XML into Premiere Pro

## The Briefing Conversation

YapCut's core differentiator. Before any markers are generated, the editor briefs Claude on the session. This is not optional.

### Required Information

1. **Timeline framerate** — default 30fps, declare if different
2. **Source media path(s)** — where the files live for XML `<pathurl>` references

### Briefing Topics

1. **Stream context** — Game, session type (solo/squad/collab), anything notable
2. **Target output** — Highlight reel? Full VOD edit? Target runtime?
3. **Tone direction** — "Keep the banter, cut the grinding" / "Tryhard session, focus on peaks"
4. **Priority moments** — Anything the editor remembers being good
5. **What to deprioritize** — "Cut all donation reads" / "I ranted about matchmaking for 15 min, trim it"
6. **Preset selection** — Which editorial preset to load (if any)

### How It Works

Claude has already ingested the transcript before the briefing. During conversation, it references specific moments: "I see a 6-minute section at 1:14:00 where you're discussing vehicle balance — keep, cut, or trim?" The editor responds, Claude incorporates that direction.

Even a 2-minute briefing dramatically improves marker quality versus zero-context generation.

## Operating Modes

### Mode 1: Multicam / ISO (Default)

The editor has multiple source files to sync in Premiere (VOD, cam ISOs, game capture, guest cams, Discord audio). YapCut outputs markers on the VOD timeline. The editor syncs ISOs in Premiere's multicam workflow, then uses markers to guide cutting decisions across all tracks.

**Output:** `yapcut_markers.xml` — FCP XML with spanned marker track on VOD clipitem

### Mode 2: Single Source (Opt-In)

Only one source file, no ISOs. The editor explicitly requests physical edit points: "Just give me a rough cut, no markers."

**Output:** `yapcut_roughcut.xml` — FCP XML with actual clip edits on timeline

## Marker Types

| Color | Label | Meaning |
|-------|-------|---------|
| Green | `KEEP` | Strong recommendation to keep. High-energy, strong dialogue, key moment. |
| Yellow | `MAYBE` | Worth reviewing. Could go either way depending on pacing and total runtime. |
| Red | `CUT` | Explicit cut recommendation. Only used for non-obvious cuts — see CUT Logic below. |
| Blue | `MOMENT` | Standalone moment — potential short, clip, or highlight. Self-contained. Can overlap with KEEP regions. |
| Purple | `CONTEXT` | Not entertaining on its own, but required for a nearby KEEP/MOMENT to make sense. |

## CUT Marker Logic

CUT markers are **rare and high-value**. Unmarked regions are implicitly assumed to be cut-worthy. A physical CUT marker is only generated when:

1. **The segment sounds good in transcript but has a non-obvious reason to cut** — e.g., "This is a 4-minute rant that's nearly identical to one at 1:14:00, but the later one has better delivery and tighter pacing. Skip this one."
2. **A preset rule is explicitly violated** — e.g., "Donation read flagged — preset says cut unless chat spikes. Chat was flat."
3. **A trap the editor might fall into** — content that seems keepable in isolation but hurts the edit structurally (pacing, redundancy, runtime bloat).

**Do NOT generate CUT markers for:** dead air, loading screens, menu navigation, matchmaking, or any obviously dead content. These are implicit cuts. Marking them is noise.

## Marker XML Schema

Markers are injected **inside the primary VOD `<clipitem>`**, not at the sequence level. This ensures markers travel with the clip if the editor nudges the VOD track during multicam sync.

### XML Node Structure

```xml
<clipitem id="v-clip-001">
  <name>Primary_VOD_Track</name>

  <marker>
    <name>[KEEP] Insane Squad Wipe</name>
    <comment>Chat density spiked 400%. High-energy comms, clean mechanics. Vocal energy peak on isolated mic confirms genuine reaction.</comment>
    <in>4500</in>
    <out>5850</out>
  </marker>

  <marker>
    <name>[CUT] Redundant Loadout Rant</name>
    <comment>You make this exact point about weapon balance again at 01:14:00, but the later one has better delivery and tighter pacing. Skip this one.</comment>
    <in>8100</in>
    <out>8950</out>
  </marker>

  <marker>
    <name>[MOMENT] Sniper No-Scope Reaction</name>
    <comment>Standalone 22-second clip. Clean setup, mechanical peak, strong vocal reaction. Works as a Short independent of surrounding KEEP context.</comment>
    <in>12000</in>
    <out>13500</out>
  </marker>

  <marker>
    <name>[CONTEXT] Squad Callout Before Push</name>
    <comment>Sets up the squad wipe at 02:32. Without this 8-second callout, the audience won't understand why the push was coordinated.</comment>
    <in>4200</in>
    <out>4440</out>
  </marker>

</clipitem>
```

### Key Details

- **`<in>` and `<out>` tags** create spanned markers (visual blocks on the timeline), not point markers. Values are in **frames**, not seconds. Convert: `frame = int(seconds * timebase)`
- **`[PREFIX]` in `<name>`** enables filtering in Premiere's Markers panel — type `[KEEP]` to see only keepers
- **`<comment>` tag** maps to Premiere's marker Description field — double-click any marker to read Claude's reasoning
- **Clip-level attachment** ensures markers survive timeline nudges during multicam sync

**CRITICAL:** If Claude outputs seconds instead of frames in marker `<in>`/`<out>` tags, the import will produce zero-duration point markers. This is a hard failure. Always convert to frames.

## Editorial Presets

Markdown files encoding editorial style for specific content types. Loaded by name during the briefing.

### Location

```
yapcut/presets/
├── battlefield-campaign.md   # BF6 campaign — actor reacting to own performance
├── battlefam.md              # Interview show — cast/crew conversations
├── shorts.md                 # 30-60s vertical content extraction
├── teaser.md                 # 60-120s pre-roll intro from best VOD moments
└── chill-stream.md           # Comedy-first multiplayer with friends
```

### Usage

"Load battlefield-campaign" during the briefing. Presets are starting points, not rigid rules. The briefing conversation overrides any preset default:
- "Use chill-stream but more aggressive cuts than usual"
- "Load shorts but cap at 30 seconds instead of 60"

### Preset Contents

Each preset defines:
- **Target runtime** — approximate final length or compression ratio
- **Marker density target** — markers per hour of source (calibrates Claude's "budget")
- **Content priority stack** — ranked list of what to keep vs. cut
- **Implicit CUT zones** — content types that should never be marked, just ignored
- **Title/game-specific rules** — mechanics unique to the game being played
- **Short extraction rules** — MOMENT flagging criteria
- **Audio priority rules** — how vocal energy and audio clarity factor into keep/cut decisions

## YouTube Chat Integration

Chat is a signal, not a directive.

- **Message density spikes** — sudden bursts indicate something happened. Strong highlight correlation.
- **Sentiment clustering** — "LOL"/"LMAO"/caps-lock = comedy. "???"/"NO WAY" = surprise. "F" spam = fail (funny or boring, context-dependent).
- **Chat as tiebreaker** — ambiguous transcript moment + high chat activity = tip toward KEEP. Ambiguous moment + dead chat = tip toward MAYBE.
- **Chat context in marker comments** — include in `<comment>` so the editor sees "chat was popping here."

Chat JSON location: `input/chat.json`

Chat is optional — YapCut works on transcript + briefing alone if no chat log is provided. Chat is additive, never required.

## Style Memory (EDITORIAL_MEMORY.md)

An evolving file that captures the editor's actual preferences based on real editorial decisions. Claude reads this at session start to calibrate marker generation.

- **Auto-populated** by `tools/diff_analysis.py` after the editor exports an EDL from Premiere. The diff script compares proposed marker regions against the EDL (the definitive record of what survived the edit) and appends behavioral insights.
- **Manual notes** can be added anytime — e.g., "Stop flagging donation reads unless chat goes crazy during one."
- **Cold start:** First session, `EDITORIAL_MEMORY.md` doesn't exist. YapCut operates on briefing + preset only. Memory builds organically.

## Project Structure

```
yapcut/
├── CLAUDE.md                    # This file — project knowledge base
├── EDITORIAL_MEMORY.md          # Evolving style memory (auto + manual)
├── presets/
│   ├── battlefield-campaign.md
│   ├── battlefam.md
│   ├── shorts.md
│   ├── teaser.md
│   └── chill-stream.md
├── tools/
│   ├── validate_xml.py          # FCP XML validator
│   ├── chat_pull.py             # YouTube chat log fetcher
│   ├── diff_analysis.py         # EDL vs. markers comparison engine
│   └── generate_xml.py          # XML generation helper
├── input/
│   ├── transcript.json          # From transcription tool (Stage 2)
│   └── chat.json                # YouTube chat (when available)
└── output/
    └── yapcut_markers.xml       # Generated marker track (or roughcut.xml)
```

## Input Transcript Format

Transcripts come from a separate transcription tool (Stage 2 output). The JSON schema:

```json
{
  "language": "en-us",
  "segments": [
    {
      "start": 1.56,          // seconds from start of source media
      "duration": 21.9,       // segment duration in seconds
      "speaker": "uuid-here", // references speakers[] array
      "language": "en-us",
      "words": [
        {
          "start": 1.56,           // word start time in seconds
          "duration": 0.54,        // word duration in seconds
          "confidence": 0.88,      // transcription confidence 0-1
          "eos": false,            // end of sentence flag
          "tags": [],              // e.g. ["disfluency"]
          "text": "Hello,",        // the word text
          "type": "word"           // token type
        }
      ]
    }
  ],
  "speakers": [
    {
      "id": "uuid-here",
      "name": "Unknown"     // speaker label
    }
  ]
}
```

Key details:
- All timestamps are in **seconds** (float), not frames
- `eos: true` marks sentence boundaries — useful for finding natural cut points
- `tags: ["disfluency"]` marks filler words/stutters
- Segments group words by speaker turn and natural pauses
- A single speaker may have many segments (they represent pauses/breaks, not unique speakers)

## FCP 7 XML Schema (xmeml v5)

Premiere Pro imports FCP 7 XML (not FCPX). The format uses `xmeml version="5"` as the root element.

### Critical Concepts

- **All time values in the XML are in frames**, not seconds. Convert: `frame = seconds * timebase`
- **timebase**: The frame rate denominator. For 29.97fps: timebase=30, ntsc=TRUE. For 30fps: timebase=30, ntsc=FALSE
- **`start`/`end`**: Position on the sequence timeline (in frames)
- **`in`/`out`**: Trim points within the source media (in frames)
- **`file` elements**: Referenced by ID. Define once with full details, then reference by ID only in subsequent clipitems

### Minimal Valid Sequence

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="5">
  <sequence id="seq-001">
    <name>Rough Cut</name>
    <duration>{total_frames}</duration>
    <rate>
      <timebase>30</timebase>
      <ntsc>TRUE</ntsc>
    </rate>
    <media>
      <video>
        <track>
          <clipitem id="v-clip-001">
            <name>Clip 1</name>
            <duration>{source_total_frames}</duration>
            <rate>
              <timebase>30</timebase>
              <ntsc>TRUE</ntsc>
            </rate>
            <start>{timeline_start_frame}</start>
            <end>{timeline_end_frame}</end>
            <in>{source_in_frame}</in>
            <out>{source_out_frame}</out>
            <file id="file-001">
              <name>source.mp4</name>
              <pathurl>file:///C:/Users/jaywa.NEUTRON/Videos/Streams/source.mp4</pathurl>
              <duration>{source_total_frames}</duration>
              <rate>
                <timebase>30</timebase>
                <ntsc>TRUE</ntsc>
              </rate>
              <media>
                <video>
                  <samplecharacteristics>
                    <width>1920</width>
                    <height>1080</height>
                  </samplecharacteristics>
                </video>
                <audio>
                  <samplecharacteristics>
                    <depth>16</depth>
                    <samplerate>48000</samplerate>
                  </samplecharacteristics>
                </audio>
              </media>
            </file>
          </clipitem>
        </track>
      </video>
      <audio>
        <track>
          <clipitem id="a-clip-001">
            <name>Clip 1</name>
            <duration>{source_total_frames}</duration>
            <rate>
              <timebase>30</timebase>
              <ntsc>TRUE</ntsc>
            </rate>
            <start>{timeline_start_frame}</start>
            <end>{timeline_end_frame}</end>
            <in>{source_in_frame}</in>
            <out>{source_out_frame}</out>
            <file id="file-001"/>
          </clipitem>
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>
```

### Rules for Generating XML

1. **One video track, one audio track minimum** — both referencing the same source file
2. **Clipitems on the timeline must not overlap** — `end` of one clip = `start` of next
3. **File element defined once** with full details (pathurl, duration, media characteristics), then referenced by `id` only in subsequent clips
4. **pathurl uses forward slashes** and `file:///` prefix. Spaces must be URL-encoded (`%20`)
5. **Rate block** must appear in sequence, each clipitem, and the file element
6. **Video and audio clipitems must be paired** — same `start`/`end`/`in`/`out` values for linked clips

### Time Conversion

```
frame_number = int(time_in_seconds * timebase)
```

When `ntsc=TRUE` and `timebase=30`, the actual rate is 29.97fps but frame numbers still use 30 as the multiplier. The NLE handles the pulldown internally.

## Media Path Conventions

- Source media lives at: `C:\Users\jaywa.NEUTRON\Documents\heyJayWalker\Streams\`
- In XML pathurl format: `file:///C:/Users/jaywa.NEUTRON/Documents/heyJayWalker/Streams/`
- URL-encode spaces and special characters in filenames
- The human will specify which source file to reference for each edit session
- Generated XML goes in `output/` with descriptive filenames

## Editorial Guidelines

- Default to cutting on sentence boundaries (`eos: true`) for cleaner edits
- Prefer leaving ~0.5s padding before/after cut points for breathing room
- When selecting highlights, favor segments with high word confidence scores
- Flag disfluencies (`tags: ["disfluency"]`) but don't auto-remove — let the human decide
- Presets extend these base guidelines with content-type-specific rules

## Generating a Marker Edit

When the human asks for an edit:

1. Read `EDITORIAL_MEMORY.md` if it exists
2. Load the requested preset if specified
3. Read and understand the full transcript
4. Read `input/chat.json` if available
5. Conduct the briefing conversation
6. Propose marker regions with types, timestamps, and reasoning
7. Discuss and refine with the human
8. Generate the FCP XML with markers inside the VOD clipitem
9. Save to `output/` and run `python tools/validate_xml.py output/filename.xml`
10. Share validation results and file path

## Validation

Run the validator before delivering any XML:

```bash
python tools/validate_xml.py output/my_edit.xml
```

The validator checks both marker-mode and rough-cut-mode XML: XML well-formedness, required FCP elements, structural integrity, timeline continuity.
