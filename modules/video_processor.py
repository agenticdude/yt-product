"""
Video Processor Module
"""

import subprocess
import multiprocessing
from pathlib import Path

def check_gpu_available():
    """Check if NVIDIA GPU encoding is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        return "h264_nvenc" in result.stdout
    except:
        return False

def check_ffmpeg_available():
    """Check ffmpeg and ffprobe availability"""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=5)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=5)
        return True, ""
    except Exception as e:
        return False, str(e)

def get_media_duration(path):
    """Get duration in seconds"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error: {result.stderr.decode(errors='ignore')}")
    try:
        return float(result.stdout.decode().strip())
    except:
        raise RuntimeError("Unable to parse duration")

def loop_video_to_match_audio(video_path, audio_path, output_path, use_gpu=False, quality_preset="fast"):
    """Loop video to match audio duration"""
    video_dur = get_media_duration(video_path)
    audio_dur = get_media_duration(audio_path)
    
    if audio_dur <= video_dur:
        return combine_video_audio(video_path, audio_path, output_path, use_gpu, quality_preset)
    
    loops_needed = int(audio_dur / video_dur) + 1
    
    concat_file = Path(output_path).parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for _ in range(loops_needed):
            f.write(f"file '{Path(video_path).resolve()}'\n")
    
    temp_looped = Path(output_path).parent / "temp_looped.mp4"
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(temp_looped)]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"Video looping failed: {result.stderr.decode(errors='ignore')}")
    
    trimmed_video = Path(output_path).parent / "temp_trimmed.mp4"
    cmd = ["ffmpeg", "-y", "-i", str(temp_looped), "-t", str(audio_dur), "-c", "copy", str(trimmed_video)]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"Video trimming failed: {result.stderr.decode(errors='ignore')}")
    
    final_result = combine_video_audio(trimmed_video, audio_path, output_path, use_gpu, quality_preset)
    
    try:
        Path(concat_file).unlink()
        Path(temp_looped).unlink()
        Path(trimmed_video).unlink()
    except:
        pass
    
    return final_result

def combine_video_audio(video_path, audio_path, output_path, use_gpu=False, quality_preset="fast"):
    """Combine video and audio, removing original audio"""
    preset_map = {"fastest": "veryfast", "fast": "fast", "balanced": "medium", "quality": "slow"}
    cpu_preset = preset_map.get(quality_preset, "fast")
    threads = max(1, int(multiprocessing.cpu_count() * 0.75))
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v",
        "-map", "1:a"
    ]
    
    if use_gpu:
        cmd += ["-c:v", "h264_nvenc", "-preset", "fast", "-b:v", "5M"]
    else:
        cmd += ["-c:v", "libx264", "-preset", cpu_preset, "-crf", "23", "-threads", str(threads)]
    
    cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest", str(output_path)]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"Video-audio combination failed: {result.stderr.decode(errors='ignore')}")
    
    return str(output_path)

def get_audio_name_from_path(audio_path):
    """Extract filename without extension"""
    return Path(audio_path).stem
