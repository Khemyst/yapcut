"""Stage 2 — Resolve text anchors from a narrative outline to precise timestamps.

Takes a narrative outline JSON (editorial decisions) + a WhisperX transcript
JSON (word-level timestamps), and resolves text anchors to precise frame-accurate
timestamps. Outputs a segment_list.json ready for XML assembly.

Usage:
    python resolve_timestamps.py outline.json transcript.json [-o output.json]

Standard library only — no external dependencies.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. flatten_words
# ---------------------------------------------------------------------------

def flatten_words(transcript: dict) -> list[dict]:
    """Extract all words from all segments into a single ordered list.

    Each word dict retains: start, duration, confidence, eos, tags, text, type.
    """
    words: list[dict] = []
    for segment in transcript.get("segments", []):
        for word in segment.get("words", []):
            words.append(word)
    return words


# ---------------------------------------------------------------------------
# 2. _normalize
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s']", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation (keep apostrophes), collapse whitespace."""
    text = text.lower()
    text = _PUNCT_RE.sub("", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


# ---------------------------------------------------------------------------
# 3. find_anchor
# ---------------------------------------------------------------------------

def find_anchor(
    words: list[dict],
    anchor: str,
    approximate_sec: float | None = None,
    search_window_sec: float = 60.0,
) -> tuple[int, int]:
    """Find a text phrase in the word list. Returns (start_idx, end_idx) inclusive.

    - Split anchor into tokens, normalize both sides
    - Slide a window of size N across words
    - Use difflib.SequenceMatcher for fuzzy matching (threshold 0.75)
    - If approximate_sec is given, only search within +/- search_window_sec
    - Raises ValueError if no match above threshold
    """
    anchor_norm = _normalize(anchor)
    anchor_tokens = anchor_norm.split()
    n = len(anchor_tokens)

    if n == 0:
        raise ValueError("No match found: anchor is empty")

    best_score = 0.0
    best_start = -1
    best_end = -1

    for i in range(len(words) - n + 1):
        # If approximate_sec given, skip words outside the window
        if approximate_sec is not None:
            word_t = words[i]["start"]
            if abs(word_t - approximate_sec) > search_window_sec:
                continue

        # Build the candidate string from n consecutive words
        candidate_tokens = [_normalize(words[j]["text"]) for j in range(i, i + n)]
        candidate_str = " ".join(candidate_tokens)

        score = difflib.SequenceMatcher(None, anchor_norm, candidate_str).ratio()

        if score > best_score:
            best_score = score
            best_start = i
            best_end = i + n - 1

    if best_score < 0.75:
        raise ValueError(
            f"No match found for anchor '{anchor}' (best score: {best_score:.2f})"
        )

    return best_start, best_end


# ---------------------------------------------------------------------------
# 4. _find_eos_at_or_after
# ---------------------------------------------------------------------------

def _find_eos_at_or_after(words: list[dict], idx: int) -> int | None:
    """Find nearest word with eos=True at or after idx. Returns index or None."""
    for i in range(idx, len(words)):
        if words[i].get("eos", False):
            return i
    return None


# ---------------------------------------------------------------------------
# 5. resolve_boundaries
# ---------------------------------------------------------------------------

def resolve_boundaries(
    words: list[dict],
    start_idx: int,
    end_idx: int,
    start_pad_sec: float = 0.5,
    min_duration_sec: float = 5.0,
) -> dict:
    """Resolve precise start/end times from word indices.

    - Start = words[start_idx]["start"] - start_pad_sec, clamped to 0
    - End = snap to nearest eos at or after end_idx, use word.start + word.duration
    - Enforce minimum duration by extending to later EOS words
    - Returns dict with: start_sec, end_sec, start_word, end_word, eos_verified,
      duration_sec, warnings
    """
    warnings: list[str] = []

    # Start time with padding
    start_sec = max(0.0, words[start_idx]["start"] - start_pad_sec)

    # Snap end to eos
    eos_idx = _find_eos_at_or_after(words, end_idx)
    eos_verified = eos_idx is not None

    if eos_idx is not None:
        end_word_idx = eos_idx
    else:
        end_word_idx = end_idx
        warnings.append("No eos found at or after end_idx; using end_idx as-is")

    end_sec = words[end_word_idx]["start"] + words[end_word_idx]["duration"]

    # Enforce minimum duration
    duration = end_sec - start_sec
    if duration < min_duration_sec:
        # Try extending to later eos words until we meet min_duration
        extended = False
        search_from = end_word_idx + 1
        while search_from < len(words):
            next_eos = _find_eos_at_or_after(words, search_from)
            if next_eos is None:
                break
            candidate_end = words[next_eos]["start"] + words[next_eos]["duration"]
            if candidate_end - start_sec >= min_duration_sec:
                end_word_idx = next_eos
                end_sec = candidate_end
                eos_verified = True
                extended = True
                warnings.append(
                    f"Extended to meet min_duration_sec={min_duration_sec}s "
                    f"(was {duration:.1f}s, now {end_sec - start_sec:.1f}s)"
                )
                break
            search_from = next_eos + 1

        if not extended:
            # Use last available word if we still can't meet minimum
            last_idx = len(words) - 1
            end_word_idx = last_idx
            end_sec = words[last_idx]["start"] + words[last_idx]["duration"]
            if end_sec - start_sec < min_duration_sec:
                warnings.append(
                    f"Could not meet min_duration_sec={min_duration_sec}s; "
                    f"duration is {end_sec - start_sec:.1f}s"
                )

    return {
        "start_sec": start_sec,
        "end_sec": end_sec,
        "start_word": words[start_idx]["text"],
        "end_word": words[end_word_idx]["text"],
        "eos_verified": eos_verified,
        "duration_sec": round(end_sec - start_sec, 3),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# 6. find_internal_cuts
# ---------------------------------------------------------------------------

def find_internal_cuts(
    words: list[dict],
    start_idx: int,
    end_idx: int,
    min_gap_sec: float = 1.5,
) -> list[dict]:
    """Find gaps > min_gap_sec between consecutive words within a range.

    Returns list of {start_sec, end_sec, gap_sec, reason}.
    """
    cuts: list[dict] = []

    for i in range(start_idx, end_idx):
        current_end = words[i]["start"] + words[i]["duration"]
        next_start = words[i + 1]["start"]
        gap = next_start - current_end

        if gap >= min_gap_sec:
            cuts.append({
                "start_sec": current_end,
                "end_sec": next_start,
                "gap_sec": round(gap, 3),
                "reason": f"Dead air ({gap:.1f}s gap)",
            })

    return cuts


# ---------------------------------------------------------------------------
# 7. resolve_segment
# ---------------------------------------------------------------------------

def resolve_segment(
    words: list[dict],
    segment: dict,
    start_pad_sec: float = 0.5,
    min_duration_sec: float = 5.0,
    search_window_sec: float = 60.0,
) -> dict:
    """Resolve a single outline segment to precise timestamps.

    Finds start anchor, finds end anchor, resolves boundaries, finds internal
    cuts. Returns the full resolved segment dict.
    """
    seg_id = segment.get("id", "unknown")
    label = segment.get("label", "")
    marker_type = segment.get("marker_type", "KEEP")
    comment = segment.get("comment", "")
    approx_start = segment.get("approximate_start_sec")
    approx_end = segment.get("approximate_end_sec")
    anchor_start = segment.get("anchor_start", "")
    anchor_end = segment.get("anchor_end", "")

    warnings: list[str] = []

    # Resolve start anchor
    try:
        start_idx, _ = find_anchor(
            words, anchor_start,
            approximate_sec=approx_start,
            search_window_sec=search_window_sec,
        )
    except ValueError as e:
        warnings.append(f"Start anchor failed: {e}")
        # Fallback: use approximate_start_sec
        start_idx = _find_nearest_word(words, approx_start or 0.0)

    # Resolve end anchor
    try:
        _, end_idx = find_anchor(
            words, anchor_end,
            approximate_sec=approx_end or approx_start,
            search_window_sec=search_window_sec,
        )
    except ValueError as e:
        warnings.append(f"End anchor failed: {e}")
        # Fallback: use approximate_end_sec
        end_idx = _find_nearest_word(words, approx_end or (approx_start or 0.0) + 30.0)

    # Ensure end >= start
    if end_idx < start_idx:
        end_idx = start_idx
        warnings.append("End index was before start index; clamped to start")

    # Resolve boundaries
    bounds = resolve_boundaries(words, start_idx, end_idx, start_pad_sec, min_duration_sec)
    warnings.extend(bounds["warnings"])

    # Find internal cuts
    internal_cuts = find_internal_cuts(words, start_idx, end_idx)

    return {
        "id": seg_id,
        "label": label,
        "marker_type": marker_type,
        "comment": comment,
        "status": "resolved" if not any("failed" in w.lower() for w in warnings) else "approximate",
        "start_sec": bounds["start_sec"],
        "end_sec": bounds["end_sec"],
        "duration_sec": bounds["duration_sec"],
        "start_word": bounds["start_word"],
        "end_word": bounds["end_word"],
        "eos_verified": bounds["eos_verified"],
        "internal_cuts": internal_cuts,
        "warnings": warnings,
    }


def _find_nearest_word(words: list[dict], target_sec: float) -> int:
    """Find the word index nearest to target_sec."""
    if not words:
        return 0
    best_idx = 0
    best_dist = abs(words[0]["start"] - target_sec)
    for i, w in enumerate(words):
        dist = abs(w["start"] - target_sec)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


# ---------------------------------------------------------------------------
# 8. resolve_outline
# ---------------------------------------------------------------------------

def resolve_outline(
    outline: dict,
    transcript: dict,
    start_pad_sec: float = 0.5,
    min_duration_sec: float = 5.0,
    search_window_sec: float = 60.0,
) -> dict:
    """Process entire outline. Resolves all segments and teaser clips.

    Returns a segment_list dict ready for XML assembly.
    """
    words = flatten_words(transcript)

    # Resolve segments
    resolved_segments: list[dict] = []
    for seg in outline.get("segments", []):
        resolved = resolve_segment(
            words, seg, start_pad_sec, min_duration_sec, search_window_sec
        )
        resolved_segments.append(resolved)

    # Resolve teasers
    resolved_teasers: list[dict] = []
    for teaser in outline.get("teasers", []):
        teaser_out = {
            "name": teaser.get("name", "Teaser"),
            "clips": [],
        }
        for clip in teaser.get("clips", []):
            # Treat each clip like a mini-segment
            clip_seg = {
                "id": f"teaser-{teaser.get('name', 'X')}-{clip.get('label', '?')}",
                "label": clip.get("label", ""),
                "marker_type": "TEASER",
                "comment": "",
                "approximate_start_sec": clip.get("approximate_start_sec"),
                "approximate_end_sec": clip.get("approximate_end_sec"),
                "anchor_start": clip.get("anchor_start", ""),
                "anchor_end": clip.get("anchor_end", ""),
            }
            resolved_clip = resolve_segment(
                words, clip_seg, start_pad_sec,
                min_duration_sec=2.0,  # Teasers can be shorter
                search_window_sec=search_window_sec,
            )
            teaser_out["clips"].append(resolved_clip)
        resolved_teasers.append(teaser_out)

    # Build output
    return {
        "title": outline.get("title", "Untitled"),
        "target_runtime_minutes": outline.get("target_runtime_minutes"),
        "source": outline.get("source", {}),
        "segments": resolved_segments,
        "teasers": resolved_teasers,
        "summary": {
            "total_segments": len(resolved_segments),
            "resolved": sum(1 for s in resolved_segments if s["status"] == "resolved"),
            "approximate": sum(1 for s in resolved_segments if s["status"] == "approximate"),
            "total_teasers": len(resolved_teasers),
        },
    }


# ---------------------------------------------------------------------------
# 9. CLI main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point: resolve outline anchors against a transcript."""
    parser = argparse.ArgumentParser(
        description="Resolve text anchors from a narrative outline to precise timestamps."
    )
    parser.add_argument("outline", help="Path to narrative outline JSON")
    parser.add_argument("transcript", help="Path to WhisperX transcript JSON")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output path for segment_list.json (default: next to outline)",
    )
    args = parser.parse_args()

    # Read inputs
    outline_path = Path(args.outline)
    transcript_path = Path(args.transcript)

    if not outline_path.exists():
        print(f"ERROR: Outline not found: {outline_path}", file=sys.stderr)
        sys.exit(1)
    if not transcript_path.exists():
        print(f"ERROR: Transcript not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    # Resolve
    result = resolve_outline(outline, transcript)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = outline_path.parent / "segment_list.json"

    # Write output
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Print summary
    summary = result["summary"]
    print(f"Resolved {summary['resolved']}/{summary['total_segments']} segments "
          f"({summary['approximate']} approximate)")
    print(f"Teasers: {summary['total_teasers']}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
