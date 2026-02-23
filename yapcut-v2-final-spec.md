# YapCut v2 — Complete Architecture Spec

> Consolidated spec reflecting all refinements from Claude + Gemini 3.1 Pro collaboration.
> This document extends the existing v1 CLAUDE.md. It does not replace the v1 foundations.

---

## Core Architecture: Non-Destructive Marker Tracks

YapCut v2 outputs **spanned marker tracks** by default, not physical edit points. Markers are non-destructive annotations on the VOD timeline that guide the editor without committing any cuts.

### Why Markers

- Preserves sync between all ISO files (VOD, cam, game, guest, Discord audio)
- Editor retains full creative control — markers are suggestions, not decisions
- Enables multicam workflow in Premiere (sync ISOs first, then act on markers)
- Allows the editor to disagree with any recommendation without undoing structural edits
- Makes style memory tracking possible (compare marker suggestions vs. final EDL)

### Marker Types

| Color | Label | Meaning |
|-------|-------|---------|
| Green | `KEEP` | Strong recommendation to keep. High-energy, strong dialogue, key moment. |
| Yellow | `MAYBE` | Worth reviewing. Could go either way depending on pacing and total runtime. |
| Red | `CUT` | Explicit cut recommendation. **Only used for non-obvious cuts** — see CUT Logic below. |
| Blue | `MOMENT` | Standalone moment — potential short, clip, or highlight. Self-contained. Can overlap with KEEP regions. |
| Purple | `CONTEXT` | Not entertaining on its own, but required for a nearby KEEP/MOMENT to make sense. |

### CUT Marker Logic (Sparse by Design)

CUT markers are **rare and high-value**. Unmarked regions are implicitly assumed to be cut-worthy. A physical CUT marker is only generated when:

1. **The segment sounds good in transcript but has a non-obvious reason to cut** — e.g., "This is a 4-minute rant that's nearly identical to one at 1:14:00, but the later one has better delivery and tighter pacing. Skip this one."
2. **A preset rule is explicitly violated** — e.g., "Donation read flagged — preset says cut unless chat spikes. Chat was flat."
3. **A trap the editor might fall into** — content that seems keepable in isolation but hurts the edit structurally (pacing, redundancy, runtime bloat).

**Do NOT generate CUT markers for:** dead air, loading screens, menu navigation, matchmaking, or any obviously dead content. These are implicit cuts. Marking them is noise.

### Marker Metadata

Each marker carries:
- `label`: The marker type prefix in the name field
- `reasoning`: 1-2 sentence explanation in the comment field
- `transcript_excerpt`: (when relevant) Key dialogue referenced in the reasoning
- `chat_signal`: (when available) Chat activity context
- `confidence`: Internal weighting (not exported to XML, used for marker density budgeting)

---

## FCP XML Schema: Spanned Markers on Clip Items

### Timebase Declaration

**CRITICAL:** The editor must declare their timeline framerate during the briefing conversation. Default is **30fps** (standard OBS output). All `<in>` and `<out>` values are in **frames**, not seconds.

**Conversion rule:** `frame = int(seconds * timebase)`

If Claude Code outputs seconds instead of frames in marker tags, the import will produce zero-duration point markers. This is a hard failure.

### Marker Attachment

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
    <comment>You make this exact point about weapon balance again at 01:14:00, but the later version has better delivery and tighter pacing. Skip this one.</comment>
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

### Why This Syntax

- **`<in>` and `<out>` tags** create spanned markers (visual blocks on the timeline), not point markers
- **`[PREFIX]` in `<name>`** enables filtering in Premiere's Markers panel — type `[KEEP]` to see only keepers
- **`<comment>` tag** maps to Premiere's marker Description field — double-click any marker to read Claude's reasoning
- **Clip-level attachment** ensures markers survive timeline nudges during multicam sync

---

## Operating Modes

### Mode 1: Multicam / ISO (Default)

The editor has multiple source files to sync in Premiere:
- VOD (primary timeline — OBS combined output, pulled from YouTube)
- JAY_CAM (isolated camera + mic via OBS Source Record)
- GAME_ (isolated game capture)
- GUEST1_CAM, GUEST2_CAM, etc.
- Discord/voice chat audio ISOs

YapCut outputs markers on the VOD timeline. Editor syncs ISOs in Premiere's multicam workflow, then uses markers to guide cutting decisions across all tracks.

**Output:** `yapcut_markers.xml` — FCP XML with spanned marker track on VOD clipitem

### Mode 2: Single Source (Opt-In)

Only one source file, no ISOs. Editor explicitly requests physical edit points: "Just give me a rough cut, no markers."

**Output:** `yapcut_roughcut.xml` — FCP XML with actual clip edits on timeline

---

## The Briefing Conversation

YapCut's core differentiator. Before any markers are generated, the editor briefs Claude Code on the session. This is not optional.

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

Claude Code has already ingested the transcript before the briefing. During conversation, it references specific moments: "I see a 6-minute section at 1:14:00 where you're discussing vehicle balance — keep, cut, or trim?" The editor responds, Claude incorporates that direction.

Even a 2-minute briefing dramatically improves marker quality versus zero-context generation.

---

## Editorial Presets

Markdown files encoding editorial style for specific content types. Loaded by name during the briefing.

### Location

```
yapcut/
├── presets/
│   ├── battlefield-highlights.md
│   ├── full-vod-edit.md
│   ├── shorts-extraction.md
│   ├── battlefam-episode.md
│   └── chill-stream.md
```

### Preset Contents

Each preset defines:
- **Target runtime** — approximate final length or compression ratio
- **Marker density target** — markers per hour of source (calibrates Claude's "budget")
- **Content priority stack** — ranked list of what to keep vs. cut
- **Implicit CUT zones** — content types that should never be marked, just ignored
- **Title/game-specific rules** — mechanics unique to the game being played
- **Short extraction rules** — MOMENT flagging criteria
- **Audio priority rules** — how vocal energy and audio clarity factor into keep/cut decisions

### Preset Usage

Presets are starting points, not rigid rules. The briefing conversation overrides any preset default:
- "Load battlefield-highlights"
- "Use full-vod but target 20 minutes instead of 30"
- "Start with chill-stream but more aggressive cuts than usual"

### Sample Preset: `battlefield-highlights.md`

```markdown
# YAPCUT PRESET: Battlefield Highlights (BF6 / Large-Scale Shooters)

## Target Output
- Format: YouTube VOD Highlight Reel
- Ratio: Compress 2-4 hours into 20-30 minutes
- Marker Density Target: 20-25 markers per hour of source material

## Content Priority Stack (Highest to Lowest)
1. Clutch Moments / Squad Wipes — intense firefights, objective pushes, multi-kills
2. High-Energy Comms — banter, callouts, funny arguments with squadmates
3. Sniper / High-Skill Kills — long-range, vehicle takedowns with infantry, mechanical highlights
4. Funny Fails / "Battlefield Moments" — physics glitches, chaos, unexpected deaths
5. Contextual Lulls — brief quiet moments before a big fight (CONTEXT tags, use sparingly)

## Implicit CUT Zones (Do NOT Flag)
- Menu navigation, loadouts, matchmaking, loading screens
- Empty map traversal unless accompanied by top-tier squad banter
- Donation/sub reads unless interrupted by gameplay or causing a major reaction
- Repetitive spawn-die loops unless the mounting frustration is comedic

## Title-Specific Rules (Battlefield)
- Infantry vs. Vehicle: Bias toward boots-on-the-ground infantry momentum for sustained
  sequences. Vehicles are premium for single-moment spectacle only (C5 ambush, helicopter
  takedown, squad tank kill). A 3-minute tank run is boring. A 10-second tank explosion
  is a MOMENT.
- Objective Play: Flag captures/arms only if they resolve a tense firefight. Uncontested
  caps are implicit cuts.

## Short Extraction (MOMENT flags)
- Aggressive MOMENT flagging for this content type
- Target: self-contained 15-60 second clips with clear setup, peak, and reaction
- MOMENT flags are independent of surrounding KEEP markers — a MOMENT can live inside
  a KEEP region. Both recommendations are valid simultaneously.

## Audio Priority Rules
- Vocal clarity and energy are part of the keep/cut calculus
- A mechanically impressive moment with dead comms = MAYBE
- The same moment with strong vocal reaction = KEEP
- Isolated mic energy always trumps game audio energy for editorial decisions
```

---

## YouTube Chat Integration

### Data Source

YouTube Data API v3 `liveChatMessages` endpoint. Chat replay available via video ID after stream ends. Since both the VOD and chat are pulled from YouTube, their timecodes are natively locked — no OBS-to-Live drift concerns.

### Collection

A utility script (or VapoRise post-stream task) pulls the chat log and saves as JSON:

```json
{
  "video_id": "abc123",
  "messages": [
    {
      "timestamp_ms": 145000,
      "author": "username",
      "message": "LMAOOO",
      "is_member": false,
      "is_moderator": false
    }
  ]
}
```

Timestamps are relative to stream start (matching transcript timeline).

### How YapCut Uses Chat

Chat is a signal, not a directive:

- **Message density spikes** — sudden bursts indicate something happened. Strong highlight correlation.
- **Sentiment clustering** — "LOL"/"LMAO"/caps-lock = comedy. "???"/"NO WAY" = surprise. "F" spam = fail (funny or boring, context-dependent).
- **Chat as tiebreaker** — ambiguous transcript moment + high chat activity → tip toward KEEP. Ambiguous moment + dead chat → tip toward MAYBE.
- **Chat context in marker metadata** — included in `<comment>` so editor sees "chat was popping here."

### Chat Unavailable

YapCut operates on transcript + briefing alone if no chat log is provided. Chat is additive, never required.

---

## Style Memory: The EDL Feedback Loop

### Purpose

An evolving file that captures the editor's actual preferences based on real editorial decisions. Claude Code reads this at session start to calibrate marker generation.

### File

```
yapcut/
├── EDITORIAL_MEMORY.md
```

### The Diff Engine (`diff_analysis.py`)

After the editor finishes cutting in Premiere, they export an EDL (`File > Export > EDL`, CMX 3600 format). The diff script compares the proposed marker regions against the EDL — the definitive record of what survived the edit.

**The editor does not need to use markers during their edit.** They cut however they naturally cut. The EDL captures the result.

#### Phase 1: Parsing and Normalization

- **YapCut XML:** Frame counts (`<in>4500</in>`)
- **Premiere EDL:** SMPTE timecode (`00:02:30:00`)
- **Action:** Normalize both to absolute seconds (or frames) using the session timebase

#### Phase 2: Fuzzy Overlap Matching

Editors don't preserve marker boundaries exactly. They trim, extend, and adjust. Exact matching would produce garbage data.

**Dual-axis matching:** Primary key is marker name similarity. Fallback is temporal proximity. If an EDL clip has no name match but overlaps 85%+ with a proposed marker, it's the same moment — the name just didn't survive round-trip.

**Overlap calculation:**
```
Overlap = min(proposed_out, edl_out) - max(proposed_in, edl_in)
Percentage = Overlap / proposed_duration
```

#### Phase 3: Categorization

| Category | Condition | Signal Strength |
|----------|-----------|-----------------|
| `ACCEPTED` | Overlap ≥ 70% | Positive — Claude's recommendation was solid |
| `HEAVILY_MODIFIED` | 0% < Overlap < 70% | Moderate — right region, wrong boundaries. Claude should tighten. |
| `REJECTED` | Marker deleted or 0% overlap | Negative — Claude proposed something the editor didn't want |
| `USER_KEPT_DEAD_SPACE` | EDL clip exists in unmarked region | Strong negative — Claude missed a moment entirely. Detection thresholds too conservative. |
| `USER_KEPT_IN_EXISTING` | EDL clip exists inside a proposed marker but adds sub-structure | Moderate — Claude had the right area but missed a sub-moment |

#### Phase 4: Output (Appended to EDITORIAL_MEMORY.md)

```markdown
## Session: [Date] - [Preset Used]

**Global Stats:**
- Proposed: 42 markers | Survived in EDL: 28 | Not in EDL: 14
- AI Proposed Avg Duration: 45s | Editor Final Avg Duration: 22s

**Category Breakdown:**
- [KEEP]: 15 proposed → 10 ACCEPTED, 3 HEAVILY_MODIFIED, 2 REJECTED
- [MOMENT]: 4 proposed → 4 ACCEPTED
- [CUT]: 3 proposed → 3 ACCEPTED (editor agreed with all trap warnings)
- [CONTEXT]: 5 proposed → 4 ACCEPTED, 1 REJECTED

**Behavioral Shifts Detected:**
- Editor consistently trimmed [KEEP] markers by avg 40%, favoring clip tails over heads.
  → Recommendation: Tighten lead-in times on future sessions.
- 4 clips survived in EDL from unmarked (implicit CUT) regions, all during high
  chat-density moments below current detection threshold.
  → Recommendation: Lower chat density threshold for MAYBE flagging.
- All [CUT] trap warnings were honored. Trust level for CUT markers: high.
```

### Manual Entries

The editor can add qualitative notes at any time:

```markdown
[2026-02-25] Note: Stop flagging donation reads unless chat goes crazy
during one. 95% of them are cut regardless.

[2026-03-01] Note: I've been keeping more quiet moments lately. When I'm
genuinely reacting (not narrating), those land better than high-energy
callouts. Lean into authentic reactions.
```

### Cold Start

First session: `EDITORIAL_MEMORY.md` doesn't exist. YapCut operates on briefing + preset only. Memory builds organically.

---

## Input Dependencies

| Input | Source | Required |
|-------|--------|----------|
| Timecoded transcript JSON | `tools/transcribe.py` (WhisperX) | Yes |
| YouTube chat log JSON | VapoRise post-stream task or `chat_pull.py` | No |
| Editorial preset .md | Editor-created, in `yapcut/presets/` | No |
| Editorial memory .md | Auto-generated from diff analysis | No |
| Source media path(s) | Editor provides during briefing | Yes |
| Timeline framerate | Editor declares during briefing (default 30fps) | Yes |

---

## Project Structure

```
yapcut/
├── CLAUDE.md                    # System instructions for Claude Code
├── EDITORIAL_MEMORY.md          # Evolving style memory (auto + manual)
├── presets/
│   ├── battlefield-highlights.md
│   ├── full-vod-edit.md
│   ├── shorts-extraction.md
│   ├── battlefam-episode.md
│   └── chill-stream.md
├── tools/
│   ├── validate_xml.py          # FCP XML validator
│   ├── chat_pull.py             # YouTube chat log fetcher
│   └── diff_analysis.py         # EDL vs. markers comparison engine
├── input/
│   ├── transcript.json          # From tools/transcribe.py
│   └── chat.json                # YouTube chat (when available)
└── output/
    └── yapcut_markers.xml       # Generated marker track (or roughcut.xml)
```

---

## Data Flow

```
Stream ends
    │
    ├─→ tools/transcribe.py (WhisperX)
    │                                              │
    ├─→ VapoRise (remux, upload, chat pull)        │
    │         │                                    │
    │         └─→ chat.json ──────────┐            │
    │                                 ▼            ▼
    │                            ┌──────────────────────┐
    │                            │   YapCut Briefing     │
    │                            │   (Claude Code)       │
    │                            │                       │
    │                            │ + transcript.json     │
    │                            │ + chat.json           │
    │                            │ + preset .md          │
    │                            │ + EDITORIAL_MEMORY.md │
    │                            └──────────┬────────────┘
    │                                       │
    │                                       ▼
    │                              yapcut_markers.xml
    │                                       │
    │                                       ▼
    │                              Premiere Pro Import
    │                              (sync ISOs, edit)
    │                                       │
    │                                       ▼
    │                              EDL Export (CMX 3600)
    │                                       │
    │                                       ▼
    │                              diff_analysis.py
    │                                       │
    │                                       ▼
    │                              EDITORIAL_MEMORY.md
    │                                       │
    │                                       ▼
    │                              (next session is smarter)
    └───────────────────────────────────────┘
```

---

## v1 → v2 Summary

| Aspect | v1 (ClaudEdits) | v2 (YapCut) |
|--------|-----------------|-------------|
| Default output | Physical edit points | Spanned marker tracks on clip items |
| Multicam support | None | Native (markers preserve ISO sync) |
| Chat integration | None | YouTube chat as editorial signal |
| Editorial presets | None | Loadable .md preset files |
| Style memory | None | EDITORIAL_MEMORY.md with EDL-based diff |
| Feedback loop | None | Automated diff (EDL vs. markers) + manual notes |
| CUT logic | Mark everything | Sparse — only non-obvious traps and preset violations |
| Marker format | N/A | Spanned, prefixed names, comment reasoning, clip-attached |
| Briefing | Implicit | Explicit first-class workflow step with required declarations |
| Name | ClaudEdits | YapCut |
