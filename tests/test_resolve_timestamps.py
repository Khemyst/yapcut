"""Tests for tools/resolve_timestamps.py — Stage 2 timestamp resolution."""

import copy
import sys
from pathlib import Path

# Allow importing from tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from resolve_timestamps import (  # noqa: E402
    flatten_words,
    _normalize,
    find_anchor,
    _find_eos_at_or_after,
    resolve_boundaries,
    find_internal_cuts,
    resolve_segment,
    resolve_outline,
)

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# Test fixtures — synthetic transcripts
# ---------------------------------------------------------------------------

TRANSCRIPT = {
    "language": "en-us",
    "segments": [
        {
            "start": 10.0, "duration": 5.0, "speaker": "spk-001", "language": "en-us",
            "words": [
                {"start": 10.0, "duration": 0.3, "confidence": 0.9, "eos": False, "tags": [], "text": "What", "type": "word"},
                {"start": 10.4, "duration": 0.2, "confidence": 0.85, "eos": False, "tags": [], "text": "up", "type": "word"},
                {"start": 10.7, "duration": 0.5, "confidence": 0.88, "eos": True, "tags": [], "text": "y'all?", "type": "word"},
            ]
        },
        {
            "start": 12.0, "duration": 4.0, "speaker": "spk-001", "language": "en-us",
            "words": [
                {"start": 12.0, "duration": 0.4, "confidence": 0.92, "eos": False, "tags": [], "text": "This", "type": "word"},
                {"start": 12.5, "duration": 0.3, "confidence": 0.91, "eos": False, "tags": [], "text": "is", "type": "word"},
                {"start": 12.9, "duration": 0.6, "confidence": 0.95, "eos": True, "tags": [], "text": "crazy.", "type": "word"},
            ]
        },
        {
            "start": 50.0, "duration": 8.0, "speaker": "spk-001", "language": "en-us",
            "words": [
                {"start": 50.0, "duration": 0.3, "confidence": 0.7, "eos": False, "tags": [], "text": "Such", "type": "word"},
                {"start": 50.4, "duration": 0.2, "confidence": 0.65, "eos": False, "tags": [], "text": "a", "type": "word"},
                {"start": 50.7, "duration": 0.4, "confidence": 0.9, "eos": False, "tags": [], "text": "long", "type": "word"},
                {"start": 51.2, "duration": 0.4, "confidence": 0.88, "eos": False, "tags": [], "text": "time", "type": "word"},
                {"start": 51.7, "duration": 0.8, "confidence": 0.93, "eos": True, "tags": [], "text": "coming.", "type": "word"},
            ]
        },
        {
            "start": 100.0, "duration": 6.0, "speaker": "spk-001", "language": "en-us",
            "words": [
                {"start": 100.0, "duration": 0.5, "confidence": 0.8, "eos": False, "tags": [], "text": "Video", "type": "word"},
                {"start": 100.6, "duration": 0.5, "confidence": 0.85, "eos": False, "tags": [], "text": "games", "type": "word"},
                {"start": 101.2, "duration": 0.3, "confidence": 0.9, "eos": False, "tags": [], "text": "will", "type": "word"},
                {"start": 101.6, "duration": 0.3, "confidence": 0.87, "eos": False, "tags": [], "text": "pay", "type": "word"},
                {"start": 102.0, "duration": 0.4, "confidence": 0.92, "eos": False, "tags": [], "text": "your", "type": "word"},
                {"start": 102.5, "duration": 0.7, "confidence": 0.95, "eos": True, "tags": [], "text": "bills.", "type": "word"},
            ]
        },
    ],
    "speakers": [{"id": "spk-001", "name": "Unknown"}]
}


def _make_transcript_with_gap():
    """TRANSCRIPT with an extra segment containing a 3s dead air gap."""
    t = copy.deepcopy(TRANSCRIPT)
    gap_segment = {
        "start": 20.0, "duration": 10.0, "speaker": "spk-001", "language": "en-us",
        "words": [
            {"start": 20.0, "duration": 0.5, "confidence": 0.9, "eos": False, "tags": [], "text": "I", "type": "word"},
            {"start": 20.6, "duration": 0.4, "confidence": 0.88, "eos": True, "tags": [], "text": "see.", "type": "word"},
            # 3.0s gap here (21.0 -> 24.0)
            {"start": 24.0, "duration": 0.5, "confidence": 0.85, "eos": False, "tags": [], "text": "That's", "type": "word"},
            {"start": 24.6, "duration": 0.6, "confidence": 0.9, "eos": True, "tags": [], "text": "cool.", "type": "word"},
        ]
    }
    # Insert after "crazy." segment (index 1), before "Such" segment (index 2)
    t["segments"].insert(2, gap_segment)
    return t


TRANSCRIPT_WITH_GAP = _make_transcript_with_gap()


OUTLINE_FIXTURE = {
    "title": "Test Edit",
    "target_runtime_minutes": 1,
    "source": {
        "path": "C:\\test\\source.mp4",
        "duration_sec": 200.0,
        "width": 1920, "height": 1080,
        "timebase": 30, "ntsc": True
    },
    "segments": [
        {
            "id": "seg-001", "label": "Opening", "marker_type": "KEEP",
            "comment": "First words.",
            "approximate_start_sec": 10, "approximate_end_sec": 13,
            "anchor_start": "What up y'all", "anchor_end": "crazy"
        },
        {
            "id": "seg-002", "label": "Time Coming", "marker_type": "KEEP",
            "comment": "The wait.",
            "approximate_start_sec": 50, "approximate_end_sec": 52,
            "anchor_start": "long time", "anchor_end": "coming"
        },
    ],
    "teasers": [
        {
            "name": "Teaser A",
            "clips": [{"label": "Bills", "anchor_start": "Video games", "anchor_end": "bills", "approximate_start_sec": 100}]
        }
    ]
}


# ---------------------------------------------------------------------------
# flatten_words tests
# ---------------------------------------------------------------------------

class TestFlattenWords:

    def test_flatten_words_returns_all_words(self):
        """Flattened word list should contain all 17 words across all segments."""
        # seg0: 3 + seg1: 3 + seg2: 5 + seg3: 6 = 17
        words = flatten_words(TRANSCRIPT)
        assert len(words) == 17

    def test_flatten_words_preserves_order(self):
        """Timestamps must be in non-decreasing order after flattening."""
        words = flatten_words(TRANSCRIPT)
        starts = [w["start"] for w in words]
        assert starts == sorted(starts)

    def test_flatten_words_preserves_fields(self):
        """First word should retain all original fields."""
        words = flatten_words(TRANSCRIPT)
        w = words[0]
        assert w["text"] == "What"
        assert w["start"] == 10.0
        assert w["duration"] == 0.3
        assert w["eos"] is False
        assert w["confidence"] == 0.9

    def test_flatten_words_crosses_segment_boundaries(self):
        """Word at index 2 should be last from seg 0, word at index 3 first from seg 1."""
        words = flatten_words(TRANSCRIPT)
        assert words[2]["text"] == "y'all?"
        assert words[3]["text"] == "This"


# ---------------------------------------------------------------------------
# find_anchor tests
# ---------------------------------------------------------------------------

class TestFindAnchor:

    def test_find_anchor_exact_match(self):
        """'What up y'all' should match indices 0-2."""
        words = flatten_words(TRANSCRIPT)
        start, end = find_anchor(words, "What up y'all")
        assert start == 0
        assert end == 2

    def test_find_anchor_case_insensitive(self):
        """Lowercase anchor should still match."""
        words = flatten_words(TRANSCRIPT)
        start, end = find_anchor(words, "what up y'all")
        assert start == 0
        assert end == 2

    def test_find_anchor_ignores_punctuation(self):
        """'long time coming' should match even though transcript has 'coming.'"""
        words = flatten_words(TRANSCRIPT)
        start, end = find_anchor(words, "long time coming")
        # "long" is at index 8, "time" at 9, "coming." at 10
        assert words[start]["text"] == "long"
        assert words[end]["text"] == "coming."

    def test_find_anchor_with_approximate_time(self):
        """approximate_sec should disambiguate when anchor could match multiple locations."""
        words = flatten_words(TRANSCRIPT)
        # Search near t=50 for "long time" — should find index 8,9
        start, end = find_anchor(words, "long time", approximate_sec=50.0, search_window_sec=10.0)
        assert words[start]["text"] == "long"
        assert words[end]["text"] == "time"

    def test_find_anchor_not_found_raises(self):
        """Non-existent phrase should raise ValueError."""
        words = flatten_words(TRANSCRIPT)
        with pytest.raises(ValueError, match="No match"):
            find_anchor(words, "this phrase does not exist anywhere")


# ---------------------------------------------------------------------------
# resolve_boundaries tests
# ---------------------------------------------------------------------------

class TestResolveBoundaries:

    def test_resolve_boundaries_snaps_to_eos(self):
        """End word should have eos: true."""
        words = flatten_words(TRANSCRIPT)
        # Indices 0-2: "What up y'all?" — word 2 has eos=True
        result = resolve_boundaries(words, 0, 2)
        assert result["eos_verified"] is True

    def test_resolve_boundaries_applies_start_padding(self):
        """Start should be 0.5s before first word's start time."""
        words = flatten_words(TRANSCRIPT)
        result = resolve_boundaries(words, 0, 2, start_pad_sec=0.5)
        assert result["start_sec"] == pytest.approx(10.0 - 0.5)

    def test_resolve_boundaries_start_padding_clamps_to_zero(self):
        """Padding beyond time 0 should clamp to 0."""
        words = flatten_words(TRANSCRIPT)
        result = resolve_boundaries(words, 0, 2, start_pad_sec=20.0)
        assert result["start_sec"] == 0.0

    def test_resolve_boundaries_end_extends_to_word_end(self):
        """end_sec should be the end word's start + duration."""
        words = flatten_words(TRANSCRIPT)
        # Word 2: "y'all?" start=10.7, duration=0.5 -> end at 11.2
        # Use min_duration_sec=0 to avoid extension logic
        result = resolve_boundaries(words, 0, 2, min_duration_sec=0.0)
        assert result["end_sec"] == pytest.approx(10.7 + 0.5)

    def test_resolve_boundaries_minimum_duration(self):
        """Short segment should be extended to meet minimum duration, with a warning."""
        words = flatten_words(TRANSCRIPT)
        # Indices 0-2 span ~10.0 to ~11.2 = 1.2s, well under default 5s min
        # Should extend to a later eos word to hit min duration
        result = resolve_boundaries(words, 0, 2, min_duration_sec=5.0)
        assert result["duration_sec"] >= 5.0
        assert len(result["warnings"]) > 0


# ---------------------------------------------------------------------------
# find_internal_cuts tests
# ---------------------------------------------------------------------------

class TestFindInternalCuts:

    def test_find_internal_cuts_detects_gap(self):
        """Should detect the 3s gap in TRANSCRIPT_WITH_GAP."""
        words = flatten_words(TRANSCRIPT_WITH_GAP)
        # The gap segment words: "I" (20.0-20.5), "see." (20.6-21.0), gap, "That's" (24.0), "cool." (24.6)
        # Find the range that includes those words
        start_idx = None
        end_idx = None
        for i, w in enumerate(words):
            if w["text"] == "I" and w["start"] == 20.0:
                start_idx = i
            if w["text"] == "cool." and w["start"] == 24.6:
                end_idx = i
        assert start_idx is not None and end_idx is not None
        cuts = find_internal_cuts(words, start_idx, end_idx, min_gap_sec=1.5)
        assert len(cuts) >= 1
        # The gap should be roughly 3s (from 21.0 to 24.0)
        assert any(c["gap_sec"] >= 2.5 for c in cuts)

    def test_find_internal_cuts_no_gap(self):
        """Normal speech without gaps should return no internal cuts."""
        words = flatten_words(TRANSCRIPT)
        # Indices 0-5: "What up y'all? This is crazy." — tight speech
        cuts = find_internal_cuts(words, 0, 5, min_gap_sec=1.5)
        assert cuts == []


# ---------------------------------------------------------------------------
# resolve_segment test
# ---------------------------------------------------------------------------

class TestResolveSegment:

    def test_resolve_segment(self):
        """Full segment resolution should produce correct start/end and metadata."""
        words = flatten_words(TRANSCRIPT)
        seg = OUTLINE_FIXTURE["segments"][0]
        result = resolve_segment(words, seg)
        assert result["id"] == "seg-001"
        assert result["label"] == "Opening"
        assert result["marker_type"] == "KEEP"
        assert "start_sec" in result
        assert "end_sec" in result
        assert result["end_sec"] > result["start_sec"]
        assert result["status"] == "resolved"


# ---------------------------------------------------------------------------
# resolve_outline tests
# ---------------------------------------------------------------------------

class TestResolveOutline:

    def test_resolve_outline_produces_all_segments(self):
        """All outline segments should be present in output."""
        result = resolve_outline(OUTLINE_FIXTURE, TRANSCRIPT)
        assert len(result["segments"]) == 2

    def test_resolve_outline_produces_teasers(self):
        """Teaser clips should be resolved."""
        result = resolve_outline(OUTLINE_FIXTURE, TRANSCRIPT)
        assert "teasers" in result
        assert len(result["teasers"]) == 1
        assert result["teasers"][0]["name"] == "Teaser A"
        assert len(result["teasers"][0]["clips"]) == 1
        clip = result["teasers"][0]["clips"][0]
        assert "start_sec" in clip
        assert "end_sec" in clip

    def test_resolve_outline_carries_source_through(self):
        """Source config should pass through to output unchanged."""
        result = resolve_outline(OUTLINE_FIXTURE, TRANSCRIPT)
        assert result["source"] == OUTLINE_FIXTURE["source"]
