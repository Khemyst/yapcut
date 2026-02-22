"""
YapCut EDL Diff Analysis — Style Memory Feedback Loop

Compares YapCut marker proposals (FCP XML) against the editor's final cut (CMX 3600 EDL)
to build an editorial style memory profile. After each editing session, the editor exports
an EDL from Premiere Pro. This tool categorizes what was accepted, modified, or rejected,
and detects content the editor kept that YapCut never flagged.

Usage:
    python diff_analysis.py markers.xml final_edit.edl --timebase 30 --preset battlefield-highlights --memory path/to/EDITORIAL_MEMORY.md
"""

import argparse
import os
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


def smpte_to_frames(tc: str, timebase: int) -> int:
    """Convert SMPTE timecode (HH:MM:SS:FF) to absolute frame count.

    Example: 00:02:30:15 at timebase 30 -> (2*60+30)*30 + 15 = 4515
    """
    parts = tc.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid SMPTE timecode: {tc}")
    hh, mm, ss, ff = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    total_seconds = hh * 3600 + mm * 60 + ss
    return total_seconds * timebase + ff


def parse_edl(edl_path: str, timebase: int = 30) -> list[dict]:
    """Parse a CMX 3600 EDL file.

    Each edit decision line matches:
        NNN  REEL  TRACK  CUT  SRC_IN SRC_OUT REC_IN REC_OUT
    Following lines with ``* FROM CLIP NAME: xxx`` provide the clip name.

    Returns list of {"edit_num": int, "in_frame": int, "out_frame": int, "name": str}
    Uses SRC_IN and SRC_OUT for the frame positions (source timecodes).
    """
    clips = []
    # Pattern for edit decision lines:
    # NNN  REEL  TRACK  CUT  SRC_IN SRC_OUT REC_IN REC_OUT
    edit_pattern = re.compile(
        r"^\s*(\d{3})\s+"       # edit number (3 digits)
        r"\S+\s+"               # reel name
        r"\S+\s+"               # track type (V, A, etc.)
        r"\S+\s+"               # edit type (C = cut)
        r"(\d{2}:\d{2}:\d{2}:\d{2})\s+"  # SRC_IN
        r"(\d{2}:\d{2}:\d{2}:\d{2})\s+"  # SRC_OUT
        r"(\d{2}:\d{2}:\d{2}:\d{2})\s+"  # REC_IN
        r"(\d{2}:\d{2}:\d{2}:\d{2})"     # REC_OUT
    )
    clip_name_pattern = re.compile(r"^\*\s*FROM CLIP NAME:\s*(.+)$")

    with open(edl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_clip = None
    for line in lines:
        line = line.rstrip("\n\r")

        edit_match = edit_pattern.match(line)
        if edit_match:
            edit_num = int(edit_match.group(1))
            src_in = smpte_to_frames(edit_match.group(2), timebase)
            src_out = smpte_to_frames(edit_match.group(3), timebase)
            current_clip = {
                "edit_num": edit_num,
                "in_frame": src_in,
                "out_frame": src_out,
                "name": "",
            }
            clips.append(current_clip)
            continue

        name_match = clip_name_pattern.match(line)
        if name_match and current_clip is not None:
            current_clip["name"] = name_match.group(1).strip()

    return clips


def parse_markers_from_xml(xml_path: str) -> list[dict]:
    """Extract <marker> elements from FCP XML.

    Each marker has name, in, out, comment. Extracts the marker type
    from the [PREFIX] in the name (e.g. "[KEEP] Great Moment" -> type="KEEP").

    Returns list of {"name": str, "in": int, "out": int, "type": str, "comment": str}
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    prefix_pattern = re.compile(r"^\[([A-Z]+)\]")
    markers = []

    for marker in root.iter("marker"):
        name_el = marker.find("name")
        comment_el = marker.find("comment")
        in_el = marker.find("in")
        out_el = marker.find("out")

        name = (name_el.text or "").strip() if name_el is not None else ""
        comment = (comment_el.text or "").strip() if comment_el is not None else ""
        in_val = int(in_el.text.strip()) if in_el is not None and in_el.text else 0
        out_val = int(out_el.text.strip()) if out_el is not None and out_el.text else 0

        # Extract type from prefix
        prefix_match = prefix_pattern.match(name)
        marker_type = prefix_match.group(1) if prefix_match else ""

        markers.append({
            "name": name,
            "in": in_val,
            "out": out_val,
            "type": marker_type,
            "comment": comment,
        })

    return markers


def compute_overlap(proposed_in: int, proposed_out: int, edl_in: int, edl_out: int) -> float:
    """Calculate what percentage of the proposed marker region overlaps with the EDL clip.

    overlap = max(0, min(proposed_out, edl_out) - max(proposed_in, edl_in))
    percentage = overlap / (proposed_out - proposed_in)

    Returns 0.0 if proposed_duration <= 0 or no overlap.
    """
    proposed_duration = proposed_out - proposed_in
    if proposed_duration <= 0:
        return 0.0

    overlap = max(0, min(proposed_out, edl_out) - max(proposed_in, edl_in))
    return overlap / proposed_duration


def _name_similarity(name_a: str, name_b: str) -> float:
    """Compute word-overlap similarity between two names.

    Returns fraction of words in name_a that also appear in name_b (case-insensitive).
    """
    words_a = set(name_a.lower().split())
    words_b = set(name_b.lower().split())
    if not words_a:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / len(words_a)


def categorize_markers(markers: list[dict], edl_clips: list[dict]) -> list[dict]:
    """For each marker, find the best-matching EDL clip using dual-axis matching.

    Matching uses:
    - Name similarity (word overlap between marker name and EDL clip name)
    - Temporal overlap percentage

    Categories based on raw temporal overlap:
    - ACCEPTED: overlap >= 70%
    - HEAVILY_MODIFIED: 0% < overlap < 70%
    - REJECTED: overlap == 0% (no match)

    Also detects USER_KEPT_DEAD_SPACE: EDL clips that exist in regions with
    zero overlap with ANY proposed marker.
    """
    results = []

    # Track which EDL clips have been matched to any marker
    edl_matched = set()

    for marker in markers:
        best_overlap = 0.0
        best_edl_idx = -1

        for idx, edl_clip in enumerate(edl_clips):
            temporal = compute_overlap(marker["in"], marker["out"], edl_clip["in_frame"], edl_clip["out_frame"])
            name_sim = _name_similarity(marker["name"], edl_clip["name"])

            # Combined score: temporal overlap is primary, name is tiebreaker
            combined = temporal + (name_sim * 0.1)

            if combined > best_overlap:
                best_overlap = combined
                best_edl_idx = idx

        # Category is based on raw temporal overlap of the best match
        if best_edl_idx >= 0:
            raw_overlap = compute_overlap(
                marker["in"], marker["out"],
                edl_clips[best_edl_idx]["in_frame"], edl_clips[best_edl_idx]["out_frame"],
            )
        else:
            raw_overlap = 0.0

        if raw_overlap >= 0.70:
            category = "ACCEPTED"
            edl_matched.add(best_edl_idx)
        elif raw_overlap > 0.0:
            category = "HEAVILY_MODIFIED"
            edl_matched.add(best_edl_idx)
        else:
            category = "REJECTED"

        results.append({
            "name": marker["name"],
            "type": marker.get("type", ""),
            "category": category,
            "in": marker["in"],
            "out": marker["out"],
            "overlap": raw_overlap,
            "comment": marker.get("comment", ""),
        })

    # Detect USER_KEPT_DEAD_SPACE: EDL clips with zero overlap with ANY marker
    for idx, edl_clip in enumerate(edl_clips):
        if idx in edl_matched:
            continue

        # Check if this EDL clip has ANY temporal overlap with ANY marker
        has_overlap = False
        for marker in markers:
            overlap = compute_overlap(marker["in"], marker["out"], edl_clip["in_frame"], edl_clip["out_frame"])
            if overlap > 0.0:
                has_overlap = True
                break

        if not has_overlap:
            results.append({
                "name": edl_clip["name"],
                "type": None,
                "category": "USER_KEPT_DEAD_SPACE",
                "in": edl_clip["in_frame"],
                "out": edl_clip["out_frame"],
                "overlap": 0.0,
                "comment": "",
            })

    return results


def format_session_report(categorized: list[dict], preset: str = "none", date: str = None) -> str:
    """Format categorization results as a markdown session report.

    Includes:
    - Session header with date and preset
    - Global stats: Proposed count, Survived, Modified, Not in EDL
    - USER_KEPT_DEAD_SPACE count if any
    - Category breakdown by marker type (KEEP, MAYBE, CUT, etc.)
    """
    if date is None:
        date = str(__import__("datetime").date.today())

    # Count categories
    accepted = [c for c in categorized if c["category"] == "ACCEPTED"]
    modified = [c for c in categorized if c["category"] == "HEAVILY_MODIFIED"]
    rejected = [c for c in categorized if c["category"] == "REJECTED"]
    dead_space = [c for c in categorized if c["category"] == "USER_KEPT_DEAD_SPACE"]

    # Proposed = everything except dead space
    proposed = [c for c in categorized if c["category"] != "USER_KEPT_DEAD_SPACE"]

    lines = []
    lines.append(f"## Session: {date} | Preset: {preset}")
    lines.append("")
    lines.append("### Global Stats")
    lines.append("")
    lines.append(f"- **Proposed:** {len(proposed)}")
    lines.append(f"- **Survived (ACCEPTED):** {len(accepted)}")
    lines.append(f"- **Modified (HEAVILY_MODIFIED):** {len(modified)}")
    lines.append(f"- **Not in EDL (REJECTED):** {len(rejected)}")

    if dead_space:
        lines.append(f"- **USER_KEPT_DEAD_SPACE:** {len(dead_space)}")

    lines.append("")

    # Breakdown by marker type
    type_groups = {}
    for c in categorized:
        t = c.get("type") or "UNTYPED"
        if t not in type_groups:
            type_groups[t] = []
        type_groups[t].append(c)

    lines.append("### Category Breakdown by Type")
    lines.append("")

    for marker_type in sorted(type_groups.keys()):
        items = type_groups[marker_type]
        lines.append(f"**{marker_type}:**")
        for item in items:
            overlap_pct = f"{item['overlap'] * 100:.0f}%" if item["overlap"] > 0 else "0%"
            lines.append(f"  - [{item['category']}] {item['name']} (overlap: {overlap_pct})")
        lines.append("")

    # Detail: USER_KEPT_DEAD_SPACE
    if dead_space:
        lines.append("### Dead Space (Editor Kept, Not Proposed)")
        lines.append("")
        for ds in dead_space:
            lines.append(f"  - {ds['name']} (frames {ds['in']}-{ds['out']})")
        lines.append("")

    return "\n".join(lines)


def append_to_memory(report: str, memory_path: str = None) -> None:
    """Append session report to EDITORIAL_MEMORY.md.

    If the file doesn't exist, creates it with a header first.
    Default path: ../EDITORIAL_MEMORY.md relative to tools/.
    """
    if memory_path is None:
        tools_dir = Path(__file__).resolve().parent
        memory_path = str(tools_dir.parent / "EDITORIAL_MEMORY.md")

    exists = os.path.exists(memory_path)

    with open(memory_path, "a", encoding="utf-8") as f:
        if not exists:
            f.write("# EDITORIAL_MEMORY\n\n")
            f.write("Style memory log — auto-generated by YapCut diff_analysis.\n")
            f.write("Claude reads this at session start to calibrate editorial preferences.\n\n")
            f.write("---\n\n")
        f.write(report)
        f.write("\n\n---\n\n")


def main():
    """CLI entry point for EDL diff analysis."""
    parser = argparse.ArgumentParser(
        description="Compare YapCut marker proposals (FCP XML) against editor's final cut (CMX 3600 EDL)."
    )
    parser.add_argument("xml_path", help="Path to FCP XML file with markers")
    parser.add_argument("edl_path", help="Path to CMX 3600 EDL file")
    parser.add_argument("--timebase", type=int, default=30, help="Frame rate timebase (default: 30)")
    parser.add_argument("--preset", default="none", help="Preset name used for the session")
    parser.add_argument("--memory", default=None, help="Path to EDITORIAL_MEMORY.md (default: ../EDITORIAL_MEMORY.md)")

    args = parser.parse_args()

    print(f"Parsing markers from: {args.xml_path}")
    markers = parse_markers_from_xml(args.xml_path)
    print(f"  Found {len(markers)} markers")

    print(f"Parsing EDL from: {args.edl_path}")
    edl_clips = parse_edl(args.edl_path, timebase=args.timebase)
    print(f"  Found {len(edl_clips)} edit decisions")

    print()
    categorized = categorize_markers(markers, edl_clips)

    report = format_session_report(categorized, preset=args.preset)
    print(report)

    memory_path = args.memory
    append_to_memory(report, memory_path=memory_path)
    target = memory_path or str(Path(__file__).resolve().parent.parent / "EDITORIAL_MEMORY.md")
    print(f"\nAppended to: {target}")


if __name__ == "__main__":
    main()
