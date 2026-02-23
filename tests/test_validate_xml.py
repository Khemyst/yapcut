"""Tests for tools/validate_xml.py — covers v1 rough-cut and v2 marker validation."""

import sys
import tempfile
from pathlib import Path

# Allow importing from tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from validate_xml import validate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — reusable XML fragments
# ---------------------------------------------------------------------------

def _minimal_roughcut_xml(
    extra_video_clip_children: str = "",
    timebase: int = 30,
    ntsc: str = "TRUE",
) -> str:
    """Return a minimal valid v1 rough-cut XML string.

    *extra_video_clip_children* is injected inside the first video clipitem
    so tests can add markers without duplicating the whole template.
    """
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<xmeml version="5">\n'
        f'<sequence id="seq-001">\n'
        f'<name>Rough Cut</name>\n'
        f'<duration>900</duration>\n'
        f'<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>\n'
        f'<media>\n'
        f'<video><track>\n'
        f'<clipitem id="v-clip-001">\n'
        f'<name>Clip 1</name>\n'
        f'<duration>54000</duration>\n'
        f'<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>\n'
        f'<start>0</start><end>900</end><in>0</in><out>900</out>\n'
        f'<file id="file-001">\n'
        f'<name>source.mp4</name>\n'
        f'<pathurl>file:///C:/videos/source.mp4</pathurl>\n'
        f'<duration>54000</duration>\n'
        f'<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>\n'
        f'<media><video><samplecharacteristics>'
        f'<width>1920</width><height>1080</height>'
        f'</samplecharacteristics></video>\n'
        f'<audio><samplecharacteristics>'
        f'<depth>16</depth><samplerate>48000</samplerate>'
        f'</samplecharacteristics></audio></media>\n'
        f'</file>\n'
        f'{extra_video_clip_children}\n'
        f'</clipitem>\n'
        f'</track></video>\n'
        f'<audio><track>\n'
        f'<clipitem id="a-clip-001">\n'
        f'<name>Clip 1</name>\n'
        f'<duration>54000</duration>\n'
        f'<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>\n'
        f'<start>0</start><end>900</end><in>0</in><out>900</out>\n'
        f'<file id="file-001"/>\n'
        f'</clipitem>\n'
        f'</track></audio>\n'
        f'</media>\n'
        f'</sequence>\n'
        f'</xmeml>\n'
    )


def _write_temp_xml(content: str) -> str:
    """Write *content* to a temporary .xml file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# v1 regression tests
# ---------------------------------------------------------------------------

def test_valid_roughcut_passes():
    """A minimal v1 rough-cut XML with no markers should validate cleanly."""
    path = _write_temp_xml(_minimal_roughcut_xml())
    issues = validate(path)
    assert issues == [], f"Expected no issues, got: {issues}"


def test_missing_file_returns_error():
    """Pointing at a nonexistent file should return a single 'File not found' error."""
    issues = validate("/nonexistent/path/to/file.xml")
    assert len(issues) == 1
    assert "File not found" in issues[0]


def test_malformed_xml():
    """Broken XML should return a parse-error issue."""
    path = _write_temp_xml("<xmeml version='5'><broken>")
    issues = validate(path)
    assert len(issues) == 1
    assert "XML parse error" in issues[0]


# ---------------------------------------------------------------------------
# v2 marker validation tests
# ---------------------------------------------------------------------------

def _marker_xml(name: str, comment: str = "reason", in_val: str = "100", out_val: str = "200") -> str:
    """Return a single <marker> XML fragment."""
    parts = [f"<marker><name>{name}</name>"]
    if comment is not None:
        parts.append(f"<comment>{comment}</comment>")
    if in_val is not None:
        parts.append(f"<in>{in_val}</in>")
    if out_val is not None:
        parts.append(f"<out>{out_val}</out>")
    parts.append("</marker>")
    return "".join(parts)


def test_valid_markers_pass():
    """XML with valid KEEP/CUT/MOMENT/MAYBE/CONTEXT markers should validate cleanly."""
    markers = "\n".join([
        _marker_xml("[KEEP] Great moment"),
        _marker_xml("[CUT] Dead air"),
        _marker_xml("[MOMENT] Funny bit"),
        _marker_xml("[MAYBE] Could work"),
        _marker_xml("[CONTEXT] Setup for joke"),
    ])
    path = _write_temp_xml(_minimal_roughcut_xml(extra_video_clip_children=markers))
    issues = validate(path)
    assert issues == [], f"Expected no issues, got: {issues}"


def test_marker_missing_comment():
    """A marker without <comment> should flag an issue."""
    marker = "<marker><name>[KEEP] Good part</name><in>100</in><out>200</out></marker>"
    path = _write_temp_xml(_minimal_roughcut_xml(extra_video_clip_children=marker))
    issues = validate(path)
    marker_issues = [i for i in issues if "comment" in i.lower()]
    assert len(marker_issues) >= 1, f"Expected a comment-related issue, got: {issues}"


def test_marker_missing_in_out():
    """A marker without <in> or <out> should flag an issue."""
    # Missing both in and out
    marker = "<marker><name>[KEEP] Good part</name><comment>reason</comment></marker>"
    path = _write_temp_xml(_minimal_roughcut_xml(extra_video_clip_children=marker))
    issues = validate(path)
    frame_issues = [i for i in issues if "in" in i.lower() or "out" in i.lower()]
    assert len(frame_issues) >= 1, f"Expected an in/out-related issue, got: {issues}"


def test_marker_invalid_prefix():
    """A marker without a proper [UPPERCASE] prefix should flag an issue."""
    marker = _marker_xml("no brackets here")
    path = _write_temp_xml(_minimal_roughcut_xml(extra_video_clip_children=marker))
    issues = validate(path)
    prefix_issues = [i for i in issues if "prefix" in i.lower()]
    assert len(prefix_issues) >= 1, f"Expected a prefix-related issue, got: {issues}"


def test_custom_preset_markers_pass():
    """Preset-defined marker types like [REACTION], [IMPRESSION], [TEASER] should validate."""
    markers = "\n".join([
        _marker_xml("[REACTION] First Murphy line"),
        _marker_xml("[IMPRESSION] Morgan Freeman voice"),
        _marker_xml("[TEASER] Cold open candidate"),
        _marker_xml("[BIT_OPEN] Running joke starts"),
        _marker_xml("[ANCHOR] Best exclusive moment"),
    ])
    path = _write_temp_xml(_minimal_roughcut_xml(extra_video_clip_children=markers))
    issues = validate(path)
    assert issues == [], f"Expected no issues for custom prefixes, got: {issues}"


def test_marker_out_before_in():
    """A marker where out <= in should flag an issue."""
    marker = _marker_xml("[KEEP] Good part", in_val="300", out_val="100")
    path = _write_temp_xml(_minimal_roughcut_xml(extra_video_clip_children=marker))
    issues = validate(path)
    range_issues = [i for i in issues if "out" in i.lower() and "in" in i.lower()]
    assert len(range_issues) >= 1, f"Expected an out<=in issue, got: {issues}"
