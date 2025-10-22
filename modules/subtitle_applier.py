"""
Subtitle Applier Module
Applies ASS subtitles to video using proper FFmpeg command
"""

import subprocess
from pathlib import Path

def burn_subtitles(video_path, subtitle_path, output_path, use_gpu=False, quality_preset="fast"):
    """Burn ASS subtitles into video using proper FFmpeg command"""
    
    preset_map = {
        "fastest": "veryfast",
        "fast": "fast",
        "balanced": "medium",
        "quality": "slow"
    }
    
    cpu_preset = preset_map.get(quality_preset, "fast")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass={str(subtitle_path)}",
        "-c:a", "copy"
    ]
    
    if use_gpu:
        cmd += ["-c:v", "h264_nvenc", "-preset", "fast", "-b:v", "5M"]
    else:
        cmd += ["-c:v", "libx264", "-preset", cpu_preset, "-crf", "23"]
    
    cmd.append(str(output_path))
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr.decode(errors='ignore')}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"Subtitle burning failed: {e}")
