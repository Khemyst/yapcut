"""Tests for tools/assemble_xml.py — Stage 3 XML assembly from segment_list.json."""

import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Allow importing from tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from assemble_xml import assemble, _sf, _xml_esc, _make_pathurl, _split_segment_by_internal_cuts, get_safe_path  # noqa: E402
from validate_xml import validate  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture — reusable segment_list matching the spec
# ---------------------------------------------------------------------------

SEGMENT_LIST = {
    "source": {
        "path": "C:\\Users\\test\\Videos\\source.mp4",
        "duration_sec": 200.0,
        "width": 1920,
        "height": 1080,
        "timebase": 30,
        "ntsc": True,
    },
    "segments": [
        {
            "id": "seg-001",
            "label": "Opening",
            "marker_type": "KEEP",
            "comment": "First words.",
            "start_sec": 9.5,
            "end_sec": 13.5,
            "duration_sec": 4.0,
            "internal_cuts": [],
            "warnings": [],
        },
        {
            "id": "seg-002",
            "label": "Story",
            "marker_type": "KEEP",
            "comment": "The story.",
            "start_sec": 50.0,
            "end_sec": 62.5,
            "duration_sec": 12.5,
            "internal_cuts": [
                {
                    "start_sec": 54.0,
                    "end_sec": 56.5,
                    "gap_sec": 2.5,
                    "reason": "dead air",
                }
            ],
            "warnings": [],
        },
    ],
    "teasers": [
        {
            "name": "Teaser A",
            "clips": [{"label": "Hook", "start_sec": 50.0, "end_sec": 55.0}],
        }
    ],
}


def _write_and_validate(xml_str: str) -> list[str]:
    """Write XML string to a temp file and run validate_xml.validate()."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    )
    f.write(xml_str)
    f.close()
    return validate(f.name)


def _parse_xml(xml_str: str) -> ET.Element:
    """Parse XML string and return the root element."""
    return ET.fromstring(xml_str)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_assemble_produces_valid_xml():
    """Generated XML should pass validate_xml with no issues."""
    xml_str = assemble(SEGMENT_LIST)
    issues = _write_and_validate(xml_str)
    assert issues == [], f"Expected no validation issues, got: {issues}"


def test_assemble_has_correct_sequences():
    """1 teaser + 1 main = 2 sequences total."""
    xml_str = assemble(SEGMENT_LIST)
    root = _parse_xml(xml_str)
    sequences = root.findall(".//sequence")
    assert len(sequences) == 2, f"Expected 2 sequences, got {len(sequences)}"

    # First should be teaser, second should be main
    names = [seq.findtext("name") for seq in sequences]
    assert "Teaser A" in names[0], f"First sequence should be teaser, got: {names[0]}"


def test_assemble_v1_clips_are_continuous():
    """Each V1 clip's end must equal the next clip's start."""
    xml_str = assemble(SEGMENT_LIST)
    root = _parse_xml(xml_str)

    # Find main sequence (last one)
    sequences = root.findall(".//sequence")
    main_seq = sequences[-1]

    # V1 is the first video track
    video = main_seq.find("media/video")
    tracks = video.findall("track")
    v1_track = tracks[0]
    clips = v1_track.findall("clipitem")

    assert len(clips) >= 2, f"Expected at least 2 V1 clips, got {len(clips)}"

    for i in range(len(clips) - 1):
        end_i = int(clips[i].findtext("end"))
        start_next = int(clips[i + 1].findtext("start"))
        assert end_i == start_next, (
            f"V1 clip {i} end ({end_i}) != clip {i+1} start ({start_next})"
        )


def test_assemble_v2_has_markers():
    """V2 track should have a single clipitem with markers for each segment."""
    xml_str = assemble(SEGMENT_LIST)
    root = _parse_xml(xml_str)

    # Main sequence is the last one
    sequences = root.findall(".//sequence")
    main_seq = sequences[-1]

    # V2 is the second video track
    video = main_seq.find("media/video")
    tracks = video.findall("track")
    assert len(tracks) >= 2, f"Expected at least 2 video tracks, got {len(tracks)}"

    v2_track = tracks[1]
    clips = v2_track.findall("clipitem")
    assert len(clips) == 1, f"Expected 1 V2 clipitem, got {len(clips)}"

    markers = clips[0].findall("marker")
    assert len(markers) == 2, f"Expected 2 markers (one per segment), got {len(markers)}"

    # Check marker names have correct prefixes
    marker_names = [m.findtext("name") for m in markers]
    assert "[KEEP]" in marker_names[0]
    assert "[KEEP]" in marker_names[1]

    # Check marker frame values are correct (seconds * timebase)
    timebase = SEGMENT_LIST["source"]["timebase"]
    first_in = int(markers[0].findtext("in"))
    first_out = int(markers[0].findtext("out"))
    assert first_in == int(9.5 * timebase), f"Marker 1 in: expected {int(9.5*timebase)}, got {first_in}"
    assert first_out == int(13.5 * timebase), f"Marker 1 out: expected {int(13.5*timebase)}, got {first_out}"


def test_assemble_stereo_audio():
    """Main sequence must have 2 audio tracks (one per stereo channel)."""
    xml_str = assemble(SEGMENT_LIST)
    root = _parse_xml(xml_str)

    # Main sequence is the last one
    sequences = root.findall(".//sequence")
    main_seq = sequences[-1]

    audio = main_seq.find("media/audio")
    assert audio is not None, "Main sequence missing <audio>"

    tracks = audio.findall("track")
    assert len(tracks) == 2, f"Expected 2 audio tracks, got {len(tracks)}"

    # Each audio track should have sourcetrack with correct trackindex
    for ch, track in enumerate(tracks, start=1):
        clips = track.findall("clipitem")
        assert len(clips) >= 1, f"Audio track {ch} has no clipitems"
        for clip in clips:
            st = clip.find("sourcetrack")
            assert st is not None, f"Audio clip in track {ch} missing <sourcetrack>"
            assert st.findtext("mediatype") == "audio"
            assert st.findtext("trackindex") == str(ch)


def test_assemble_internal_cuts_split_clipitems():
    """Segment with 1 internal cut should produce 2 V1 clipitems.
    Total: 1 (no cuts) + 2 (1 cut) = 3 V1 clips."""
    xml_str = assemble(SEGMENT_LIST)
    root = _parse_xml(xml_str)

    # Main sequence is the last one
    sequences = root.findall(".//sequence")
    main_seq = sequences[-1]

    # V1 is the first video track
    video = main_seq.find("media/video")
    tracks = video.findall("track")
    v1_track = tracks[0]
    clips = v1_track.findall("clipitem")

    assert len(clips) == 3, (
        f"Expected 3 V1 clipitems (1 from seg-001 + 2 from seg-002), got {len(clips)}"
    )

    # Also verify audio tracks have matching clip counts
    audio = main_seq.find("media/audio")
    for track in audio.findall("track"):
        audio_clips = track.findall("clipitem")
        assert len(audio_clips) == 3, (
            f"Expected 3 audio clipitems to match V1, got {len(audio_clips)}"
        )


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


def test_sf_conversion():
    """_sf should convert seconds to frames."""
    assert _sf(1.0, 30) == 30
    assert _sf(0.5, 30) == 15
    assert _sf(10.0, 24) == 240
    assert _sf(0.0, 30) == 0


def test_xml_esc():
    """_xml_esc should escape XML special characters."""
    assert _xml_esc("a & b") == "a &amp; b"
    assert _xml_esc("<tag>") == "&lt;tag&gt;"
    assert _xml_esc('"quoted"') == "&quot;quoted&quot;"
    assert _xml_esc("clean") == "clean"


def test_make_pathurl():
    """_make_pathurl should produce correct file:/// URLs."""
    url = _make_pathurl("C:\\Users\\test\\Videos\\source.mp4")
    assert url.startswith("file:///C:")
    assert "C%3A" not in url, "Drive letter colon should NOT be encoded"
    assert "\\" not in url, "Backslashes should be converted to forward slashes"


def test_make_pathurl_with_spaces():
    """_make_pathurl should URL-encode spaces."""
    url = _make_pathurl("C:\\Users\\test\\My Videos\\source file.mp4")
    assert "%20" in url or "+" in url, "Spaces should be URL-encoded"
    assert " " not in url.replace("file:///", ""), "No literal spaces in URL"


def test_split_segment_no_internal_cuts():
    """Segment with no internal cuts returns one range."""
    seg = SEGMENT_LIST["segments"][0]
    ranges = _split_segment_by_internal_cuts(seg)
    assert ranges == [(9.5, 13.5)]


def test_split_segment_with_internal_cut():
    """Segment with one internal cut returns two kept ranges."""
    seg = SEGMENT_LIST["segments"][1]
    ranges = _split_segment_by_internal_cuts(seg)
    assert len(ranges) == 2
    assert ranges[0] == (50.0, 54.0), f"First range: expected (50.0, 54.0), got {ranges[0]}"
    assert ranges[1] == (56.5, 62.5), f"Second range: expected (56.5, 62.5), got {ranges[1]}"


def test_get_safe_path_no_collision(tmp_path):
    """When no file exists, return the base name directly."""
    p = get_safe_path(tmp_path, "yapcut_test")
    assert p == tmp_path / "yapcut_test.xml"


def test_get_safe_path_with_collision(tmp_path):
    """When base name exists, should append _v2."""
    (tmp_path / "yapcut_test.xml").touch()
    p = get_safe_path(tmp_path, "yapcut_test")
    assert p == tmp_path / "yapcut_test_v2.xml"


def test_get_safe_path_multiple_collisions(tmp_path):
    """When _v2 also exists, should go to _v3."""
    (tmp_path / "yapcut_test.xml").touch()
    (tmp_path / "yapcut_test_v2.xml").touch()
    p = get_safe_path(tmp_path, "yapcut_test")
    assert p == tmp_path / "yapcut_test_v3.xml"


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


def test_full_pipeline_outline_to_valid_xml():
    """End-to-end: outline + transcript -> resolve -> assemble -> valid XML."""
    from resolve_timestamps import resolve_outline
    # Import the test fixtures from test_resolve_timestamps
    from test_resolve_timestamps import TRANSCRIPT, OUTLINE_FIXTURE

    segment_list = resolve_outline(OUTLINE_FIXTURE, TRANSCRIPT)
    xml_str = assemble(segment_list)

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w", encoding="utf-8") as f:
        f.write(xml_str)
        f.flush()
        issues = validate(f.name)

    assert issues == [], f"Pipeline produced invalid XML: {issues}"
