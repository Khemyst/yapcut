"""
YapCut WhisperX Transcription Tool

Transcribes a VOD using WhisperX and outputs a YapCut-compatible transcript
JSON file next to the source media.

Requires: whisperx, torch (with CUDA for GPU acceleration)
Optional: pyannote-audio (for speaker diarization via --diarize)

Usage:
    python tools/transcribe.py "path/to/vod.mp4" [options]

Options:
    --model        WhisperX model size (default: large-v3)
    --device       cuda or cpu (default: cuda)
    --compute-type float16, int8, etc. (default: float16)
    --language     Language code (default: en)
    --batch-size   Batch size for transcription (default: 16)
    --diarize      Enable speaker diarization (requires --hf-token)
    --hf-token     HuggingFace token for pyannote-audio
    --output       Custom output path (default: next to source as yapcut_transcript.json)
"""

import argparse
import json
import math
import sys
import uuid
from pathlib import Path


def _setup_windows_utf8():
    """Force UTF-8 stdout/stderr on Windows to handle Unicode paths."""
    import io, os
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def detect_eos(word_text: str) -> bool:
    """Detect end-of-sentence from word text.

    Returns True if the word ends with sentence-ending punctuation.
    """
    stripped = word_text.rstrip()
    if not stripped:
        return False
    return stripped[-1] in ".!?"


def convert_to_yapcut_format(aligned_result: dict, language: str, diarize_segments=None) -> dict:
    """Convert WhisperX aligned output to YapCut transcript JSON schema.

    Args:
        aligned_result: WhisperX alignment output with 'segments' and 'word_segments'.
        language: Language code (e.g. 'en').
        diarize_segments: Optional diarized segment list from whisperx.assign_word_speakers().

    Returns:
        dict matching YapCut transcript JSON schema.
    """
    # Build speaker map
    speakers_map = {}  # speaker_label -> uuid

    if diarize_segments is not None:
        # Use diarized segments which have speaker labels assigned
        source_segments = diarize_segments.get("segments", [])
    else:
        source_segments = aligned_result.get("segments", [])

    # First pass: collect all speaker labels
    for seg in source_segments:
        speaker_label = seg.get("speaker", "Unknown")
        if speaker_label not in speakers_map:
            speakers_map[speaker_label] = str(uuid.uuid4())

    # If no speakers found, add a default
    if not speakers_map:
        speakers_map["Unknown"] = str(uuid.uuid4())

    # Build speakers array
    speakers = [
        {"id": sid, "name": label}
        for label, sid in speakers_map.items()
    ]

    # Second pass: convert segments
    yapcut_segments = []
    for seg in source_segments:
        words_raw = seg.get("words", [])
        if not words_raw:
            continue

        # Filter out words with no text
        words_with_text = [w for w in words_raw if (w.get("word") or "").strip()]
        if not words_with_text:
            continue

        speaker_label = seg.get("speaker", "Unknown")
        speaker_id = speakers_map.get(speaker_label, speakers_map.get("Unknown", ""))

        seg_start = seg.get("start")
        seg_end = seg.get("end")

        # Build words array
        yapcut_words = []
        for w in words_with_text:
            word_text = w.get("word", "").strip()

            # Handle missing timestamps — fall back to segment start
            w_start = w.get("start")
            w_end = w.get("end")

            if w_start is None or w_end is None or _is_nan(w_start) or _is_nan(w_end):
                w_start = seg_start if seg_start is not None else 0.0
                w_end = w_start
                duration = 0.0
                confidence = 0.0
            else:
                duration = round(w_end - w_start, 4)
                if duration < 0:
                    duration = 0.0

                score = w.get("score", 0.0)
                if score is None or _is_nan(score):
                    confidence = 0.0
                else:
                    confidence = round(score, 4)

            yapcut_words.append({
                "start": round(w_start, 4),
                "duration": duration,
                "confidence": confidence,
                "eos": detect_eos(word_text),
                "tags": [],
                "text": word_text,
                "type": "word",
            })

        if not yapcut_words:
            continue

        # Segment timing from first/last word
        first_start = yapcut_words[0]["start"]
        last_word = yapcut_words[-1]
        seg_duration = round((last_word["start"] + last_word["duration"]) - first_start, 4)
        if seg_duration < 0:
            seg_duration = 0.0

        yapcut_segments.append({
            "start": first_start,
            "duration": seg_duration,
            "speaker": speaker_id,
            "language": language,
            "words": yapcut_words,
        })

    lang_code = f"{language}-us" if len(language) == 2 else language

    return {
        "language": lang_code,
        "segments": yapcut_segments,
        "speakers": speakers,
    }


def _is_nan(value) -> bool:
    """Check if a value is NaN (handles float and non-float)."""
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def transcribe_full(source_path: str, model_name: str, device: str,
                    compute_type: str, batch_size: int, language: str) -> dict:
    """Run WhisperX transcription and alignment on source audio.

    Args:
        source_path: Path to the audio/video file.
        model_name: WhisperX model name (e.g. 'large-v3').
        device: 'cuda' or 'cpu'.
        compute_type: Compute type (e.g. 'float16', 'int8').
        batch_size: Batch size for transcription.
        language: Language code.

    Returns:
        WhisperX aligned result dict.
    """
    import whisperx

    print(f"Loading audio: {source_path}")
    audio = whisperx.load_audio(source_path)

    print(f"Loading model: {model_name} ({device}, {compute_type})")
    model = whisperx.load_model(model_name, device, compute_type=compute_type, language=language)

    print(f"Transcribing (batch_size={batch_size})...")
    result = model.transcribe(audio, batch_size=batch_size)

    print("Aligning timestamps...")
    model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
    aligned = whisperx.align(result["segments"], model_a, metadata, audio, device,
                             return_char_alignments=False)

    return aligned


def diarize_audio(audio_path: str, device: str, hf_token: str, aligned_result: dict) -> dict:
    """Run speaker diarization and assign speakers to aligned segments.

    Args:
        audio_path: Path to the audio/video file.
        device: 'cuda' or 'cpu'.
        hf_token: HuggingFace API token for pyannote-audio.
        aligned_result: WhisperX aligned result to assign speakers to.

    Returns:
        Updated aligned result with speaker labels assigned.
    """
    import whisperx

    print("Running speaker diarization...")
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
    diarize_df = diarize_model(audio_path)

    print("Assigning speakers to segments...")
    result = whisperx.assign_word_speakers(diarize_df, aligned_result)

    return result


def save_transcript(transcript_data: dict, output_path: str) -> None:
    """Write transcript data to JSON file.

    Args:
        transcript_data: YapCut transcript dict.
        output_path: Destination file path.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    print(f"Saved transcript: {path}")


def main():
    _setup_windows_utf8()

    parser = argparse.ArgumentParser(
        description="Transcribe a VOD using WhisperX and output YapCut-compatible JSON."
    )
    parser.add_argument("source", help="Path to source video/audio file")
    parser.add_argument("--model", default="large-v3", help="WhisperX model (default: large-v3)")
    parser.add_argument("--device", default="cuda", help="Device: cuda or cpu (default: cuda)")
    parser.add_argument("--compute-type", default="float16",
                        help="Compute type (default: float16)")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Batch size (default: 16)")
    parser.add_argument("--diarize", action="store_true",
                        help="Enable speaker diarization (requires --hf-token)")
    parser.add_argument("--hf-token", default=None,
                        help="HuggingFace token for pyannote-audio diarization")
    parser.add_argument("--output", default=None,
                        help="Output path (default: yapcut_transcript.json next to source)")

    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Error: Source file not found: {source}")
        sys.exit(1)

    if args.diarize and not args.hf_token:
        print("Error: --diarize requires --hf-token")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = source.parent / "yapcut_transcript.json"

    # Transcribe
    aligned_result = transcribe_full(
        str(source), args.model, args.device,
        args.compute_type, args.batch_size, args.language,
    )

    # Optional diarization
    diarize_result = None
    if args.diarize:
        diarize_result = diarize_audio(str(source), args.device, args.hf_token, aligned_result)

    # Convert to YapCut format
    transcript = convert_to_yapcut_format(
        aligned_result, args.language,
        diarize_segments=diarize_result,
    )

    # Save
    save_transcript(transcript, str(output_path))

    # Summary
    n_segments = len(transcript["segments"])
    n_words = sum(len(s["words"]) for s in transcript["segments"])
    n_speakers = len(transcript["speakers"])
    print(f"\nDone: {n_segments} segments, {n_words} words, {n_speakers} speaker(s)")


if __name__ == "__main__":
    main()
