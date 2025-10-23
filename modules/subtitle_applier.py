"""
Subtitle Applier Module - GPU ONLY (No CPU Fallback)
100% GPU-optimized subtitle burning with NVIDIA CUDA
"""

import subprocess
from pathlib import Path

def burn_subtitles(video_path, subtitle_path, output_path, quality_preset="high_quality"):
    """Burn ASS subtitles into video using GPU - NO CPU FALLBACK"""
    
    # GPU-ONLY preset mappings
    quality_settings = {
        "ultra_fast": {"gpu_preset": "p4", "cq": "23", "audio_bitrate": "256k"},
        "high_quality": {"gpu_preset": "p6", "cq": "19", "audio_bitrate": "320k"},
        "maximum_quality": {"gpu_preset": "p7", "cq": "17", "audio_bitrate": "320k"},

    }
    
    selected = quality_settings.get(quality_preset, quality_settings["high_quality"])
    
    # GPU encoding with hardware acceleration
    cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda",
        "-hwaccel_output_format", "cuda",
        "-i", str(video_path),
        "-vf", f"ass={str(subtitle_path)}",
        "-c:v", "h264_nvenc",
        "-preset", selected["gpu_preset"],
        "-tune", "hq",
        "-rc", "vbr",
        "-cq", selected["cq"],
        "-profile:v", "high",
        "-spatial-aq", "1",
        "-temporal-aq", "1",
        "-c:a", "aac",
        "-b:a", selected["audio_bitrate"],
        str(output_path)
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"GPU FFmpeg error: {result.stderr.decode(errors='ignore')}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"GPU subtitle burning failed: {e}")