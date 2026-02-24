#!/usr/bin/env python3
"""ViewTube — Gemini video analysis for YapCut Stage 0.

Sends a YouTube URL to Gemini for structured visual analysis,
producing gemini_analysis.json for the post-ready cut pipeline.

For videos > 30 minutes, automatically splits into parallel chunks
with 30-second overlaps and merges the results.

Usage:
    python tools/viewtube.py "https://www.youtube.com/watch?v=abc123" --media-dir "C:\\path\\to\\streams"
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load API key from viewtube/.env (relative to project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / "viewtube" / ".env")

MODEL = "gemini-3-flash-preview"
CHUNK_MINUTES = 30
OVERLAP_SECONDS = 30

PROMPT = """\
Watch this entire video and produce a structured analysis. Do NOT make editorial \
recommendations — just describe what you observe. Output valid JSON only, no markdown \
fences, no commentary outside the JSON.

1. SPEAKER LOG — For every segment where someone speaks, identify WHO is speaking:
   - "Jay" (the streamer/host — Black man, on camera, wearing headphones)
   - "NPC" (in-game character dialogue from the video game)
   - "Chat-TTS" or "Donation" (if any text-to-speech or donation reads)
   - "Other" (anyone else)
   Format: {{"start": seconds, "end": seconds, "speaker": "Jay"|"NPC"|"Chat-TTS"|"Donation"|"Other", "brief_quote": "first few words..."}}

2. VISUAL MOMENTS — Timestamp every moment where something visually notable happens:
   - Jay has a physical reaction (leans forward, covers mouth, jumps, laughs hard, gets emotional)
   - A major gameplay event (explosion, death, cutscene transition, squad wipe)
   - Jay interacts with a physical object (puts on hat, picks something up)
   - On-screen text/UI that tells a story (mission complete, character death screen, etc.)
   Format: {{"time": seconds, "type": "physical_reaction"|"gameplay_event"|"object_interaction"|"ui_text", "intensity": "low"|"medium"|"high", "description": "what happens visually"}}

3. SILENCE PERIODS — Every stretch of 10+ seconds where Jay is NOT speaking but something \
is happening on screen. Describe what's happening visually during the silence.
   Format: {{"start": seconds, "end": seconds, "visual_activity": "description of what's on screen"}}

4. ENERGY MAP — Rate Jay's visible energy/engagement level across the video in roughly \
5-minute blocks:
   - "low" (calm, quiet, reading chat)
   - "medium" (engaged, talking normally)
   - "high" (animated, excited, loud)
   - "peak" (strongest reactions in the video)
   Format: {{"start": seconds, "end": seconds, "level": "low"|"medium"|"high"|"peak", "note": "brief description"}}

5. EMOTIONAL BEATS — Identify the top 5-10 strongest emotional moments in the video, \
ranked by intensity. These are moments where Jay's emotional state is most visible or \
audible — excitement, frustration, shock, joy, sadness, etc.
   Format: {{"time": seconds, "emotion": "description of the emotion", "intensity_rank": 1, "context": "what caused it"}}

Output the complete JSON object with these keys:
{{"speaker_log": [...], "visual_moments": [...], "silence_periods": [...], "energy_map": [...], "emotional_beats": [...]}}

Be thorough. Cover the entire video. Do not skip sections.\
"""

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/(watch\?v=|live/|shorts/)|youtu\.be/)[A-Za-z0-9_-]+"
)

DEDUP_THRESHOLD = 5  # seconds — entries within this range across chunks are duplicates

# Regex to extract video ID from any YouTube URL format
_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|live/|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]+)"
)


def normalize_url(url: str) -> str:
    """Convert any YouTube URL format to standard watch?v= format."""
    m = _VIDEO_ID_RE.search(url)
    if not m:
        return url
    return f"https://www.youtube.com/watch?v={m.group(1)}"


def get_safe_path(directory: Path, basename: str) -> Path:
    """Return a path that won't overwrite existing files."""
    candidate = directory / f"{basename}.json"
    if not candidate.exists():
        return candidate
    version = 2
    while True:
        candidate = directory / f"{basename}_v{version}.json"
        if not candidate.exists():
            return candidate
        version += 1


def get_video_duration(youtube_url: str) -> float:
    """Get video duration in seconds via yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--get-duration", "--no-warnings", youtube_url],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    raw = result.stdout.strip()
    # yt-dlp returns duration as H:MM:SS, MM:SS, or SS
    parts = raw.split(":")
    parts.reverse()
    total = 0.0
    for i, part in enumerate(parts):
        total += float(part) * (60 ** i)
    return total


def build_chunks(duration_sec: float) -> list[tuple[int, int]]:
    """Build chunk boundaries with overlap. Returns list of (start_sec, end_sec)."""
    chunk_sec = CHUNK_MINUTES * 60
    if duration_sec <= chunk_sec:
        return [(0, int(duration_sec))]
    chunks = []
    start = 0
    while start < duration_sec:
        end = min(start + chunk_sec, int(duration_sec))
        # If the remaining video after this chunk would be < 5 min,
        # extend this chunk to the end instead of creating a tiny one
        remaining = duration_sec - end
        if 0 < remaining < 300:
            end = int(duration_sec)
        chunks.append((start, end))
        if end >= duration_sec:
            break
        start = end - OVERLAP_SECONDS
    return chunks


def parse_response(response) -> dict:
    """Parse JSON from a Gemini response, handling markdown fences."""
    raw = response.text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
        return json.loads(cleaned)


def _dedup_point_entries(entries: list[dict], time_key: str) -> list[dict]:
    """Remove near-duplicate point entries (single timestamp)."""
    if not entries:
        return entries
    entries.sort(key=lambda e: e.get(time_key, 0))
    result = [entries[0]]
    for entry in entries[1:]:
        if abs(entry.get(time_key, 0) - result[-1].get(time_key, 0)) > DEDUP_THRESHOLD:
            result.append(entry)
    return result


def _dedup_span_entries(entries: list[dict]) -> list[dict]:
    """Remove near-duplicate span entries (start/end timestamps)."""
    if not entries:
        return entries
    entries.sort(key=lambda e: e.get("start", 0))
    result = [entries[0]]
    for entry in entries[1:]:
        prev = result[-1]
        if abs(entry.get("start", 0) - prev.get("start", 0)) > DEDUP_THRESHOLD:
            result.append(entry)
    return result


def merge_analyses(chunks: list[dict]) -> dict:
    """Merge multiple chunk analyses into a single result."""
    if len(chunks) == 1:
        return chunks[0]

    merged = {
        "speaker_log": [],
        "visual_moments": [],
        "silence_periods": [],
        "energy_map": [],
        "emotional_beats": [],
    }

    for i, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            print(f"  Warning: chunk {i + 1} returned unexpected type {type(chunk).__name__}, skipping")
            continue
        for key in merged:
            val = chunk.get(key, [])
            if isinstance(val, list):
                merged[key].extend(val)
            else:
                print(f"  Warning: chunk {i + 1} key '{key}' is {type(val).__name__}, not list")

    # Deduplicate
    merged["speaker_log"] = _dedup_span_entries(merged["speaker_log"])
    merged["visual_moments"] = _dedup_point_entries(merged["visual_moments"], "time")
    merged["silence_periods"] = _dedup_span_entries(merged["silence_periods"])
    merged["energy_map"] = _dedup_span_entries(merged["energy_map"])

    # Emotional beats: dedup then re-rank
    merged["emotional_beats"] = _dedup_point_entries(merged["emotional_beats"], "time")
    merged["emotional_beats"].sort(key=lambda e: e.get("intensity_rank", 99))
    for i, beat in enumerate(merged["emotional_beats"]):
        beat["intensity_rank"] = i + 1

    return merged


async def analyze_chunk(
    client: genai.Client,
    youtube_url: str,
    start_sec: int,
    end_sec: int,
    chunk_idx: int,
    total_chunks: int,
) -> dict:
    """Analyze a single chunk of video."""
    label = f"[{chunk_idx + 1}/{total_chunks}]"
    start_ts = f"{start_sec // 3600}:{(start_sec % 3600) // 60:02d}:{start_sec % 60:02d}"
    end_ts = f"{end_sec // 3600}:{(end_sec % 3600) // 60:02d}:{end_sec % 60:02d}"
    print(f"  {label} {start_ts} - {end_ts} ...", flush=True)

    t0 = time.time()

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL,
        contents=types.Content(
            parts=[
                types.Part(
                    file_data=types.FileData(file_uri=youtube_url),
                    video_metadata=types.VideoMetadata(
                        start_offset=f"{start_sec}s",
                        end_offset=f"{end_sec}s",
                    ),
                ),
                types.Part(text=PROMPT),
            ]
        ),
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
        ),
    )

    elapsed = time.time() - t0
    analysis = parse_response(response)

    tokens = ""
    if response.usage_metadata:
        meta = response.usage_metadata
        tokens = f" ({meta.total_token_count} tokens)"

    print(f"  {label} done in {elapsed:.1f}s{tokens}", flush=True)

    # Ensure we have a dict with expected keys
    if isinstance(analysis, list):
        # Gemini sometimes wraps the result in an array
        if len(analysis) == 1 and isinstance(analysis[0], dict):
            analysis = analysis[0]
        else:
            print(f"  {label} Warning: got list of {len(analysis)} items, wrapping")
            analysis = {"speaker_log": analysis}
    if not isinstance(analysis, dict):
        print(f"  {label} Warning: unexpected response type {type(analysis).__name__}")
        analysis = {}

    return analysis


async def analyze_parallel(youtube_url: str, chunks: list[tuple[int, int]]) -> dict:
    """Run all chunk analyses concurrently and merge."""
    client = genai.Client()
    tasks = [
        analyze_chunk(client, youtube_url, start, end, i, len(chunks))
        for i, (start, end) in enumerate(chunks)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            start, end = chunks[i]
            print(f"  [!] Chunk {i + 1} failed: {result}", flush=True)
        else:
            successes.append(result)
    if not successes:
        raise RuntimeError("All chunks failed")
    if len(successes) < len(chunks):
        print(f"  Warning: {len(chunks) - len(successes)}/{len(chunks)} chunks failed", flush=True)
    return merge_analyses(successes)


def analyze(youtube_url: str, media_dir: Path) -> Path:
    """Send a YouTube URL to Gemini and save the analysis JSON."""
    youtube_url = normalize_url(youtube_url)
    print(f"Model: {MODEL}")
    print(f"URL: {youtube_url}")

    # Get video duration
    print("Getting video duration...", flush=True)
    duration = get_video_duration(youtube_url)
    dur_str = f"{int(duration) // 3600}:{(int(duration) % 3600) // 60:02d}:{int(duration) % 60:02d}"
    print(f"Duration: {dur_str} ({duration:.0f}s)")

    # Build chunks
    chunks = build_chunks(duration)

    if len(chunks) == 1:
        print("Single chunk - sending directly...", flush=True)
        client = genai.Client()
        t0 = time.time()
        response = client.models.generate_content(
            model=MODEL,
            contents=types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=youtube_url)
                    ),
                    types.Part(text=PROMPT),
                ]
            ),
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
            ),
        )
        elapsed = time.time() - t0
        analysis = parse_response(response)

        if response.usage_metadata:
            meta = response.usage_metadata
            print(f"Tokens - prompt: {meta.prompt_token_count}, "
                  f"response: {meta.candidates_token_count}, "
                  f"total: {meta.total_token_count}")
        print(f"Completed in {elapsed:.1f}s")
    else:
        print(f"Splitting into {len(chunks)} chunks ({CHUNK_MINUTES}min each, "
              f"{OVERLAP_SECONDS}s overlap)...", flush=True)
        t0 = time.time()
        analysis = asyncio.run(analyze_parallel(youtube_url, chunks))
        elapsed = time.time() - t0
        print(f"All chunks completed in {elapsed:.1f}s")

        # Print merge stats
        for key in ["speaker_log", "visual_moments", "silence_periods", "energy_map", "emotional_beats"]:
            print(f"  {key}: {len(analysis.get(key, []))} entries")

    # Add metadata
    analysis["source_url"] = youtube_url
    analysis["model"] = MODEL
    analysis["duration_sec"] = duration
    analysis["chunks"] = len(chunks)

    # Save with collision-safe naming
    out_path = get_safe_path(media_dir, "gemini_analysis")
    out_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="ViewTube — Gemini video analysis for YapCut Stage 0"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--media-dir",
        required=True,
        type=Path,
        help="Directory to save gemini_analysis.json (should be the source media folder)",
    )
    args = parser.parse_args()

    # Validate URL
    if not YOUTUBE_URL_RE.match(args.url):
        print(f"Error: '{args.url}' doesn't look like a YouTube URL", file=sys.stderr)
        sys.exit(1)

    # Validate output directory
    if not args.media_dir.is_dir():
        print(f"Error: '{args.media_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    analyze(args.url, args.media_dir)


if __name__ == "__main__":
    main()
