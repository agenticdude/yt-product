"""
Video Overlay Module
Green screen removal with timing control
"""

import subprocess
from pathlib import Path

def get_video_duration(video_path):
    """Get video duration in seconds"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error: {result.stderr.decode(errors='ignore')}")
    try:
        return float(result.stdout.decode().strip())
    except:
        raise RuntimeError("Unable to parse duration")

def apply_video_overlay(
    main_video_path,
    overlay_video_path,
    output_path,
    timing_mode="range",
    start_time=0,
    end_time=None,
    position="top-right",
    size_percent=20,
    remove_green=True,
    green_similarity=0.3,
    green_blend=0.1,
    keep_overlay_audio=False,
    use_gpu=False,
    quality_preset="fast"
):
    """
    Apply video overlay with green screen removal
    
    Args:
        timing_mode: "range" or "original"
        start_time: When to start showing overlay
        end_time: When to stop (for "range" mode only)
        position: One of 9 positions
        size_percent: Size as % of video width
        remove_green: Remove green screen
        green_similarity: 0.1-0.9 (how close to green)
        green_blend: 0.0-0.3 (edge smoothing)
        keep_overlay_audio: Mix overlay audio with main
    """
    
    overlay_duration = get_video_duration(overlay_video_path)
    
    if timing_mode == "range":
        if end_time is None or end_time <= start_time:
            raise ValueError("For range mode, end_time must be > start_time")
        enable_expr = f"between(t,{start_time},{end_time})"
    else:
        end_time = start_time + overlay_duration
        enable_expr = f"between(t,{start_time},{end_time})"
    
    positions = {
        'top-left': '20:20',
        'top-center': '(main_w-overlay_w)/2:20',
        'top-right': 'main_w-overlay_w-20:20',
        'middle-left': '20:(main_h-overlay_h)/2',
        'center': '(main_w-overlay_w)/2:(main_h-overlay_h)/2',
        'middle-right': 'main_w-overlay_w-20:(main_h-overlay_h)/2',
        'bottom-left': '20:main_h-overlay_h-20',
        'bottom-center': '(main_w-overlay_w)/2:main_h-overlay_h-20',
        'bottom-right': 'main_w-overlay_w-20:main_h-overlay_h-20'
    }
    
    pos_expr = positions.get(position, positions['bottom-right'])
    
    if remove_green:
        filter_complex = f"[1:v]chromakey=0x00FF00:{green_similarity}:{green_blend},scale=iw*{size_percent/100}:-1[ov];[0:v][ov]overlay={pos_expr}:enable='{enable_expr}'[v]"
    else:
        filter_complex = f"[1:v]scale=iw*{size_percent/100}:-1[ov];[0:v][ov]overlay={pos_expr}:enable='{enable_expr}'[v]"
    
    preset_map = {"fastest": "veryfast", "fast": "fast", "balanced": "medium", "quality": "slow"}
    cpu_preset = preset_map.get(quality_preset, "fast")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(main_video_path),
        "-i", str(overlay_video_path)
    ]
    
    if keep_overlay_audio:
        filter_complex += ";[0:a][1:a]amix=inputs=2[a]"
        cmd += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "0:a", "-c:a", "copy"]
    
    if use_gpu:
        cmd += ["-c:v", "h264_nvenc", "-preset", "fast", "-b:v", "5M"]
    else:
        cmd += ["-c:v", "libx264", "-preset", cpu_preset, "-crf", "23"]
    
    cmd.append(str(output_path))
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"Overlay failed: {result.stderr.decode(errors='ignore')}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"Video overlay failed: {e}")