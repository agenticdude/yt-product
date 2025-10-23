"""
Subtitle Applier Module - CPU Version
Applies ASS subtitles using FFmpeg (CPU-based rendering and encoding)
"""

import subprocess
from pathlib import Path

def burn_subtitles(video_path, subtitle_path, output_path, quality_preset="high_quality"):
    """Burn ASS subtitles into video using CPU (libx264) encoding"""

    quality_settings = {
        "ultra_fast": {"cpu_preset": "ultrafast", "crf": "28", "audio_bitrate": "128k"},
        "fast": {"cpu_preset": "fast", "crf": "25", "audio_bitrate": "192k"},
        "high_quality": {"cpu_preset": "medium", "crf": "22", "audio_bitrate": "256k"},
        "maximum_quality": {"cpu_preset": "slow", "crf": "18", "audio_bitrate": "320k"},
    }

    selected = quality_settings.get(quality_preset, quality_settings["high_quality"])

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass={str(subtitle_path)}",
        "-c:v", "libx264",
        "-preset", selected["cpu_preset"],
        "-crf", selected["crf"],
        "-profile:v", "high",
        "-c:a", "aac",
        "-b:a", selected["audio_bitrate"],
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"CPU FFmpeg error: {result.stderr.decode(errors='ignore')}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"CPU subtitle burning failed: {e}")
