# ViewTube Parallel Chunking

**Date:** 2026-02-23
**Status:** Approved

## Purpose

Long VODs (2+ hours) can exceed Gemini's 1M token context window even at low resolution (~100 tokens/sec). Split videos into chunks and process them concurrently for faster results that fit in context.

## Behavior

1. Get video duration via `yt-dlp --get-duration`
2. If duration <= 30 min: single call (current behavior, unchanged)
3. If duration > 30 min: split into 30-minute chunks with 30-second overlaps, fire all concurrently via `asyncio`
4. Merge results: concatenate arrays, deduplicate overlap zones
5. Output single `gemini_analysis.json`

## Chunk Math

- Chunk size: 30 minutes
- Overlap: 30 seconds between adjacent chunks
- Example: 2.5 hour VOD = 5 chunks, each ~180K tokens at low res

## Deduplication

- Sort all entries by timestamp
- For entries from adjacent chunks in the overlap zone (within 5 seconds of each other): keep the one from the chunk where the timestamp is further from the boundary
- Energy map: merge at boundaries, no overlap needed (coarse 5-min blocks)
- Emotional beats: deduplicate by proximity, re-rank intensity across full VOD

## VideoMetadata API

```python
types.Part(
    file_data=types.FileData(file_uri=youtube_url),
    video_metadata=types.VideoMetadata(
        start_offset=f"{start_sec}s",
        end_offset=f"{end_sec}s",
    ),
)
```

## Dependencies

- `yt-dlp` for duration detection (no new Python packages)
