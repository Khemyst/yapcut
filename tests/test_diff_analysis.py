"""Tests for tools/diff_analysis.py — EDL diff analysis for style memory feedback loop."""

import sys
import tempfile
import os
from pathlib import Path

# Allow importing from tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from diff_analysis import (  # noqa: E402
    smpte_to_frames,
    parse_edl,
    parse_markers_from_xml,
    compute_overlap,
    categorize_markers,
    format_session_report,
    append_to_memory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_EDL = """\
TITLE: Test Edit
FCM: NON-DROP FRAME

001  AX       V     C        00:00:05:00 00:00:35:15 00:00:00:00 00:00:30:15
* FROM CLIP NAME: Great Moment

002  AX       V     C        00:01:00:00 00:01:22:10 00:00:30:15 00:00:52:25
* FROM CLIP NAME: Sick Play

003  AX       V     C        00:02:10:00 00:02:25:00 00:00:52:25 00:01:07:25
* FROM CLIP NAME: Unexpected Keep
"""

EMPTY_EDL = """\
TITLE: Empty Edit
FCM: NON-DROP FRAME

"""


def _write_temp_file(content: str, suffix: str = ".edl") -> str:
    """Write content to a temporary file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return f.name


def _sample_markers_xml() -> str:
    """Return a minimal FCP XML with markers on the first clipitem."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<xmeml version="5">\n'
        '<sequence id="seq-001">\n'
        '<name>Marker Test</name>\n'
        '<duration>54000</duration>\n'
        '<rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>\n'
        '<media>\n'
        '<video><track>\n'
        '<clipitem id="v-clip-001">\n'
        '<name>Full Source</name>\n'
        '<duration>54000</duration>\n'
        '<rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>\n'
        '<start>0</start><end>54000</end><in>0</in><out>54000</out>\n'
        '<file id="file-001">\n'
        '<name>source.mp4</name>\n'
        '<pathurl>file:///C:/videos/source.mp4</pathurl>\n'
        '<duration>54000</duration>\n'
        '<rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>\n'
        '<media><video><samplecharacteristics>'
        '<width>1920</width><height>1080</height>'
        '</samplecharacteristics></video></media>\n'
        '</file>\n'
        '<marker>\n'
        '  <name>[KEEP] Great Moment</name>\n'
        '  <comment>High energy gameplay</comment>\n'
        '  <in>150</in>\n'
        '  <out>1065</out>\n'
        '</marker>\n'
        '<marker>\n'
        '  <name>[MAYBE] Sick Play</name>\n'
        '  <comment>Decent clip</comment>\n'
        '  <in>1800</in>\n'
        '  <out>2470</out>\n'
        '</marker>\n'
        '<marker>\n'
        '  <name>[CUT] Dead Air</name>\n'
        '  <comment>Nothing happening</comment>\n'
        '  <in>5000</in>\n'
        '  <out>6000</out>\n'
        '</marker>\n'
        '</clipitem>\n'
        '</track></video>\n'
        '<audio><track>\n'
        '<clipitem id="a-clip-001">\n'
        '<name>Full Source</name>\n'
        '<duration>54000</duration>\n'
        '<rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>\n'
        '<start>0</start><end>54000</end><in>0</in><out>54000</out>\n'
        '<file id="file-001"/>\n'
        '</clipitem>\n'
        '</track></audio>\n'
        '</media>\n'
        '</sequence>\n'
        '</xmeml>\n'
    )


# ---------------------------------------------------------------------------
# SMPTE conversion tests
# ---------------------------------------------------------------------------

def test_smpte_to_frames_basic():
    """00:02:30:15 at timebase 30 should yield 4515 frames."""
    assert smpte_to_frames("00:02:30:15", 30) == 4515


def test_smpte_to_frames_zero():
    """00:00:00:00 should yield 0."""
    assert smpte_to_frames("00:00:00:00", 30) == 0


# ---------------------------------------------------------------------------
# EDL parsing tests
# ---------------------------------------------------------------------------

def test_parse_edl_extracts_clips():
    """Parse sample EDL with 3 clips, verify names and frame positions."""
    path = _write_temp_file(SAMPLE_EDL)
    clips = parse_edl(path, timebase=30)

    assert len(clips) == 3

    # Clip 1: in=150 (5*30), out=1065 (35*30+15)
    assert clips[0]["edit_num"] == 1
    assert clips[0]["in_frame"] == 150
    assert clips[0]["out_frame"] == 1065
    assert clips[0]["name"] == "Great Moment"

    # Clip 2: in=1800 (60*30), out=2470 (82*30+10)
    assert clips[1]["edit_num"] == 2
    assert clips[1]["in_frame"] == 1800
    assert clips[1]["out_frame"] == 2470
    assert clips[1]["name"] == "Sick Play"

    # Clip 3: in=3900 (130*30), out=4350 (145*30)
    # Note: 00:02:25:00 = (2*60+25)*30 + 0 = 4350, not 4500
    assert clips[2]["edit_num"] == 3
    assert clips[2]["in_frame"] == 3900
    assert clips[2]["out_frame"] == 4350
    assert clips[2]["name"] == "Unexpected Keep"

    os.unlink(path)


def test_parse_edl_empty():
    """EDL with only header returns empty list."""
    path = _write_temp_file(EMPTY_EDL)
    clips = parse_edl(path, timebase=30)
    assert clips == []
    os.unlink(path)


# ---------------------------------------------------------------------------
# Marker parsing tests
# ---------------------------------------------------------------------------

def test_parse_markers_from_xml():
    """Parse markers from FCP XML, verify names, types, frames, and comments."""
    path = _write_temp_file(_sample_markers_xml(), suffix=".xml")
    markers = parse_markers_from_xml(path)

    assert len(markers) == 3

    assert markers[0]["name"] == "[KEEP] Great Moment"
    assert markers[0]["type"] == "KEEP"
    assert markers[0]["in"] == 150
    assert markers[0]["out"] == 1065
    assert markers[0]["comment"] == "High energy gameplay"

    assert markers[1]["type"] == "MAYBE"
    assert markers[2]["type"] == "CUT"

    os.unlink(path)


# ---------------------------------------------------------------------------
# Overlap calculation tests
# ---------------------------------------------------------------------------

def test_compute_overlap_full():
    """Identical ranges should yield 1.0 (100% overlap)."""
    assert compute_overlap(100, 200, 100, 200) == 1.0


def test_compute_overlap_partial():
    """50% overlap should yield 0.5."""
    # Proposed: 0-100, EDL: 50-150 → overlap = 50, proposed_dur = 100
    assert compute_overlap(0, 100, 50, 150) == 0.5


def test_compute_overlap_none():
    """Non-overlapping ranges should yield 0.0."""
    assert compute_overlap(0, 100, 200, 300) == 0.0


def test_compute_overlap_edl_inside_proposed():
    """EDL clip entirely inside proposed range yields partial overlap."""
    # Proposed: 0-200, EDL: 50-100 → overlap = 50, proposed_dur = 200
    assert compute_overlap(0, 200, 50, 100) == 0.25


def test_compute_overlap_zero_proposed_duration():
    """Zero-length proposed region should return 0.0 (avoid division by zero)."""
    assert compute_overlap(100, 100, 100, 200) == 0.0


# ---------------------------------------------------------------------------
# Categorization tests
# ---------------------------------------------------------------------------

def test_categorize_accepted():
    """Marker with 70%+ overlap should be categorized as ACCEPTED."""
    markers = [{"name": "Great Moment", "in": 100, "out": 200, "type": "KEEP", "comment": "good"}]
    # EDL clip covers 100-200 exactly → 100% overlap
    edl_clips = [{"edit_num": 1, "in_frame": 100, "out_frame": 200, "name": "Great Moment"}]
    result = categorize_markers(markers, edl_clips)
    accepted = [r for r in result if r["category"] == "ACCEPTED"]
    assert len(accepted) == 1


def test_categorize_rejected():
    """Marker with no EDL match should be categorized as REJECTED."""
    markers = [{"name": "Dead Air", "in": 5000, "out": 6000, "type": "CUT", "comment": "nothing"}]
    # EDL clips are far away
    edl_clips = [{"edit_num": 1, "in_frame": 100, "out_frame": 200, "name": "Great Moment"}]
    result = categorize_markers(markers, edl_clips)
    rejected = [r for r in result if r["category"] == "REJECTED"]
    assert len(rejected) == 1


def test_categorize_heavily_modified():
    """Marker with partial overlap (>0%, <70%) should be HEAVILY_MODIFIED."""
    markers = [{"name": "Some Clip", "in": 0, "out": 200, "type": "MAYBE", "comment": "maybe"}]
    # EDL covers 0-100 → 50% overlap
    edl_clips = [{"edit_num": 1, "in_frame": 0, "out_frame": 100, "name": "Some Clip"}]
    result = categorize_markers(markers, edl_clips)
    modified = [r for r in result if r["category"] == "HEAVILY_MODIFIED"]
    assert len(modified) == 1


def test_user_kept_dead_space():
    """EDL clip in unmarked region should produce USER_KEPT_DEAD_SPACE entry."""
    # Markers only cover 100-200
    markers = [{"name": "Great Moment", "in": 100, "out": 200, "type": "KEEP", "comment": "good"}]
    # EDL has a clip at 100-200 (matching) AND one at 5000-6000 (dead space)
    edl_clips = [
        {"edit_num": 1, "in_frame": 100, "out_frame": 200, "name": "Great Moment"},
        {"edit_num": 2, "in_frame": 5000, "out_frame": 6000, "name": "Surprise Keeper"},
    ]
    result = categorize_markers(markers, edl_clips)
    dead_space = [r for r in result if r["category"] == "USER_KEPT_DEAD_SPACE"]
    assert len(dead_space) == 1
    assert dead_space[0]["name"] == "Surprise Keeper"


# ---------------------------------------------------------------------------
# Report formatting tests
# ---------------------------------------------------------------------------

def test_format_session_report_contains_stats():
    """Verify report contains expected sections and stats."""
    categorized = [
        {"name": "Great Moment", "type": "KEEP", "category": "ACCEPTED",
         "in": 100, "out": 200, "overlap": 1.0, "comment": "good"},
        {"name": "Sick Play", "type": "MAYBE", "category": "HEAVILY_MODIFIED",
         "in": 1800, "out": 2470, "overlap": 0.5, "comment": "decent"},
        {"name": "Dead Air", "type": "CUT", "category": "REJECTED",
         "in": 5000, "out": 6000, "overlap": 0.0, "comment": "nothing"},
        {"name": "Surprise Keeper", "type": None, "category": "USER_KEPT_DEAD_SPACE",
         "in": 8000, "out": 9000, "overlap": 0.0, "comment": ""},
    ]
    report = format_session_report(categorized, preset="battlefield-highlights", date="2026-02-22")

    assert "battlefield-highlights" in report
    assert "2026-02-22" in report
    assert "Proposed:" in report or "Proposed" in report
    assert "Survived" in report or "ACCEPTED" in report
    assert "Modified" in report or "HEAVILY_MODIFIED" in report
    assert "USER_KEPT_DEAD_SPACE" in report or "Dead Space" in report


# ---------------------------------------------------------------------------
# Memory append tests
# ---------------------------------------------------------------------------

def test_append_to_memory_creates_file():
    """append_to_memory should create EDITORIAL_MEMORY.md if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = os.path.join(tmpdir, "EDITORIAL_MEMORY.md")
        report = "## Session Report\nSome data here."
        append_to_memory(report, memory_path=memory_path)

        assert os.path.exists(memory_path)
        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "EDITORIAL_MEMORY" in content or "Session Report" in content


def test_append_to_memory_appends():
    """append_to_memory should append to existing file, not overwrite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = os.path.join(tmpdir, "EDITORIAL_MEMORY.md")
        append_to_memory("## Session 1", memory_path=memory_path)
        append_to_memory("## Session 2", memory_path=memory_path)

        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Session 1" in content
        assert "Session 2" in content
