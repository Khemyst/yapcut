"""
YapCut Audio Energy Analysis Tool

Extracts per-second audio energy (RMS amplitude in dB) from a VOD using FFmpeg.
Outputs a JSON sidecar that Claude reads alongside the transcript for
three-signal triangulation: speech timing + audio energy + chat density.

This enables smarter cut decisions:
  - No speech + quiet audio = dead air (cut it)
  - No speech + loud audio = gameplay moment (keep it)
  - No speech + audio spike = explosion/event (keep, reaction lead-in)
  - Energy-based pacing analysis: detect flat zones, peaks, natural rhythm

Requires: ffmpeg (must be on PATH)

Usage:
    python tools/audio_energy.py "path/to/vod.mp4" [options]

Options:
    --window       Analysis window in seconds (default: 1.0)
    --output       Custom output path (default: next to source as yapcut_energy.json)
"""

import argparse
import io
import json
import os
import subprocess
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def extract_energy(source_path: str, window: float = 1.0) -> dict:
    """Extract per-window RMS energy from audio using FFmpeg."""
    source = Path(source_path)
    if not source.exists():
        print(f"Error: source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    # Use FFmpeg's astats filter to get per-window RMS levels
    # -af segement audio into windows, measure each
    cmd = [
        "ffmpeg",
        "-i", str(source),
        "-af", f"asegment=timestamps=0,astats=metadata=1:reset={int(1/window)}",
        "-f", "null",
        "-"
    ]

    # Alternative approach: use volumedetect per-second by analyzing chunks
    # More reliable across FFmpeg versions
    print(f"Analyzing audio energy: {source.name}")
    print(f"Window size: {window}s")

    # Get total duration first
    probe_cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "json",
        str(source)
    ]

    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error probing file: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    probe_data = json.loads(result.stdout)
    total_duration = float(probe_data["format"]["duration"])
    total_windows = int(total_duration / window)

    print(f"Duration: {total_duration:.1f}s ({total_windows} windows)")

    # Extract raw audio samples and compute RMS per window using FFmpeg
    # Output 16-bit signed PCM, mono, at a sample rate that divides cleanly
    sample_rate = 16000
    samples_per_window = int(sample_rate * window)

    cmd = [
        "ffmpeg",
        "-v", "quiet",
        "-i", str(source),
        "-ac", "1",              # mono
        "-ar", str(sample_rate), # resample
        "-f", "s16le",           # raw 16-bit signed little-endian PCM
        "-acodec", "pcm_s16le",
        "pipe:1"
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    import math
    energy_data = []
    window_index = 0

    while True:
        # Read one window's worth of samples (2 bytes per sample for s16le)
        raw = process.stdout.read(samples_per_window * 2)
        if not raw or len(raw) < 4:
            break

        # Convert raw bytes to samples
        num_samples = len(raw) // 2
        samples = []
        for i in range(num_samples):
            sample = int.from_bytes(raw[i*2:(i+1)*2], byteorder="little", signed=True)
            samples.append(sample)

        # Compute RMS
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / num_samples)

        # Convert to dB (relative to max 16-bit value of 32768)
        if rms > 0:
            db = 20 * math.log10(rms / 32768)
        else:
            db = -96.0  # silence floor

        timestamp = window_index * window
        energy_data.append({
            "t": round(timestamp, 1),
            "rms_db": round(db, 1)
        })

        window_index += 1

        # Progress indicator every 60 seconds
        if window_index % int(60 / window) == 0:
            pct = min(100, int(window_index / max(1, total_windows) * 100))
            print(f"  {pct}% ({window_index}/{total_windows} windows)")

    process.wait()

    print(f"  100% - extracted {len(energy_data)} energy samples")

    # Compute statistics for context
    db_values = [e["rms_db"] for e in energy_data if e["rms_db"] > -96]
    if db_values:
        avg_db = sum(db_values) / len(db_values)
        min_db = min(db_values)
        max_db = max(db_values)

        # Classify energy levels relative to the VOD's own range
        # This accounts for different recording levels across VODs
        db_range = max_db - min_db
        if db_range > 0:
            silence_threshold = avg_db - (db_range * 0.3)
            high_energy_threshold = avg_db + (db_range * 0.2)
        else:
            silence_threshold = -50.0
            high_energy_threshold = -20.0
    else:
        avg_db = -96.0
        min_db = -96.0
        max_db = -96.0
        silence_threshold = -50.0
        high_energy_threshold = -20.0

    return {
        "source": source.name,
        "window_seconds": window,
        "total_duration": round(total_duration, 1),
        "total_windows": len(energy_data),
        "statistics": {
            "avg_db": round(avg_db, 1),
            "min_db": round(min_db, 1),
            "max_db": round(max_db, 1),
            "silence_threshold_db": round(silence_threshold, 1),
            "high_energy_threshold_db": round(high_energy_threshold, 1)
        },
        "energy": energy_data
    }


def main():
    parser = argparse.ArgumentParser(
        description="YapCut Audio Energy Analysis — extract per-second energy curve from a VOD"
    )
    parser.add_argument("source", help="Path to source video/audio file")
    parser.add_argument("--window", type=float, default=1.0,
                        help="Analysis window in seconds (default: 1.0)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON path (default: next to source as yapcut_energy.json)")

    args = parser.parse_args()

    data = extract_energy(args.source, args.window)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(args.source).parent / "yapcut_energy.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\nSaved: {out_path}")
    print(f"  Avg energy: {data['statistics']['avg_db']} dB")
    print(f"  Range: {data['statistics']['min_db']} to {data['statistics']['max_db']} dB")
    print(f"  Silence threshold: {data['statistics']['silence_threshold_db']} dB")
    print(f"  High energy threshold: {data['statistics']['high_energy_threshold_db']} dB")


if __name__ == "__main__":
    main()
