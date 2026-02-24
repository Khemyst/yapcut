# ViewTube — Gemini Video Analysis Module

**Date:** 2026-02-23
**Status:** Approved

## Purpose

Automates Stage 0 of the post-ready cut pipeline. Currently the human manually pastes a YouTube URL + prompt into Gemini's web UI and copies the JSON output. This module does it via the Gemini API in one command.

## Interface

```
python tools/viewtube.py "https://www.youtube.com/watch?v=abc123" --media-dir "C:\path\to\streams\folder"
```

- **First arg:** YouTube URL (required)
- **`--media-dir`:** Output directory for `gemini_analysis.json` (required — the folder where the source VOD lives)
- API key loaded from `viewtube/.env` (falls back to `GEMINI_API_KEY` env var)

## Model

`gemini-3-flash-preview` — Pro-level intelligence at flash speed/price. Hardcoded (no flag).

## Data Flow

```
YouTube URL
    |
    v
Gemini API (gemini-3-flash-preview)
    |  file_data: { file_uri: youtube_url }
    |  prompt: structured visual analysis
    |
    v
JSON response (parsed + validated)
    |
    v
{media-dir}/gemini_analysis.json
```

## Prompt

Hardcoded in the script. 5 sections:

1. **SPEAKER LOG** — Who is speaking in each segment (Jay, NPC, Chat-TTS, Donation, Other). Jay identified as "the streamer/host — Black man, on camera, wearing headphones."
2. **VISUAL MOMENTS** — Timestamped notable visual events (reactions, gameplay events, object interactions, on-screen text).
3. **SILENCE PERIODS** — Stretches of 10+ seconds where Jay isn't speaking, with description of what's on screen.
4. **ENERGY MAP** — Jay's energy/engagement level in ~5-minute blocks (low/medium/high/peak).
5. **EMOTIONAL BEATS** — Top 5-10 strongest emotional moments ranked by intensity.

## Output Schema

```json
{
  "source_url": "https://youtube.com/...",
  "model": "gemini-3-flash-preview",
  "speaker_log": [
    {"start": 114, "end": 2789, "speaker": "Jay", "brief_quote": "first few words..."}
  ],
  "visual_moments": [
    {"time": 2884, "type": "object_interaction", "intensity": "high", "description": "..."}
  ],
  "silence_periods": [
    {"start": 0, "end": 114, "visual_activity": "description of what's on screen"}
  ],
  "energy_map": [
    {"start": 0, "end": 300, "level": "medium", "note": "..."}
  ],
  "emotional_beats": [
    {"time": 4573, "emotion": "shock", "intensity_rank": 1, "context": "what caused it"}
  ]
}
```

## Dependencies

- `google-genai` — Google's Gemini Python SDK
- `python-dotenv` — .env file loading

## Error Handling

- Validates YouTube URL format before API call
- Checks API key exists
- Collision-safe output (`_v2`, `_v3` suffix if file exists)
- Prints token usage from response metadata

## Decisions

- **Streamer identity hardcoded** — This is Jay's tool, no need for a --streamer flag
- **Model hardcoded** — gemini-3-flash-preview, no --model flag
- **Output location** — next to source media per pipeline convention, no --output override
