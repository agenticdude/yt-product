"""
Video Processor Module - GPU ONLY (No CPU Fallback)
100% GPU-optimized with NVIDIA CUDA acceleration
Includes auto single/parallel detection, time tracking, and stream copy optimization
"""

import subprocess
import multiprocessing
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def get_video_resolution(path):
    """Get video resolution (width, height)"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        str(path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error getting resolution: {result.stderr.decode(errors='ignore')}")
    try:
        width, height = map(int, result.stdout.decode().strip().split('x'))
        return width, height
    except ValueError:
        raise RuntimeError("Unable to parse video resolution")

def format_time(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"

def scale_video_to_1080p(input_path, output_path, quality_preset="high_quality"):
    """Scale video to 1080p using GPU - NO CPU FALLBACK"""
    width, height = get_video_resolution(input_path)
    if width == 1920 and height == 1080:
        logger.info(f"Video already 1080p: {input_path}")
        return str(input_path)
    
    # GPU-ONLY quality presets
    quality_settings = {
        "ultra_fast": {
            "gpu_preset": "p4",
            "cq": "23",
            "multipass": "disabled",
            "spatial_aq": "0",
            "temporal_aq": "0",
            "audio_bitrate": "256k"
        },
        "high_quality": {
            "gpu_preset": "p6",
            "cq": "19",
            "multipass": "fullres",
            "spatial_aq": "1",
            "temporal_aq": "1",
            "audio_bitrate": "320k"
        },
        "maximum_quality": {
            "gpu_preset": "p7",
            "cq": "17",
            "multipass": "fullres",
            "spatial_aq": "1",
            "temporal_aq": "1",
            "audio_bitrate": "320k"
        }
    }
    
    selected_quality = quality_settings.get(quality_preset, quality_settings["high_quality"])
    gpu_preset = selected_quality["gpu_preset"]
    cq = selected_quality["cq"]
    multipass = selected_quality["multipass"]
    spatial_aq = selected_quality["spatial_aq"]
    temporal_aq = selected_quality["temporal_aq"]
    audio_bitrate = selected_quality["audio_bitrate"]
    
    # GPU-accelerated encoding with hardware decoding
    cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda",
        "-hwaccel_output_format", "cuda",
        "-i", str(input_path),
        "-vf", "scale_cuda=1920:1080:interp_algo=lanczos",
        "-map", "0:v",
        "-map", "0:a?",  # Include audio if present
        "-c:v", "h264_nvenc",
        "-preset", gpu_preset,
        "-tune", "hq",
        "-profile:v", "high",
        "-rc", "vbr",
        "-cq", cq,
        "-rc-lookahead", "32",
        "-spatial-aq", spatial_aq,
        "-temporal-aq", temporal_aq,
        "-bf", "3",
        "-gpu", "0"
    ]
    
    # Add multipass if enabled
    if multipass != "disabled":
        cmd += ["-multipass", multipass]
    
    # For maximum quality, enable additional features
    if quality_preset == "maximum_quality":
        cmd += ["-b_ref_mode", "middle", "-dpb_size", "4"]
    
    cmd += ["-c:a", "aac", "-b:a", audio_bitrate, str(output_path)]
    
    logger.info(f"GPU scaling video to 1080p: {input_path} -> {output_path}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"GPU video scaling failed: {result.stderr.decode(errors='ignore')}")
    
    logger.info(f"Successfully GPU-scaled video: {output_path}")
    return str(output_path)

def loop_video_to_match_audio(video_path, audio_path, output_path, quality_preset="high_quality"):
    """Loop video to match audio duration with GPU encoding and timing tracking"""
    start_time = time.time()
    logger.info(f"GPU processing video loop: {video_path} with audio: {audio_path}")
    
    # First, scale the input video to 1080p if it's not already (GPU)
    scaled_video_path = Path(output_path).parent / f"scaled_input_{Path(video_path).name}"
    processed_video_path = scale_video_to_1080p(video_path, scaled_video_path, quality_preset)
    
    video_dur = get_media_duration(processed_video_path)
    audio_dur = get_media_duration(audio_path)
    
    logger.info(f"Video duration: {video_dur}s, Audio duration: {audio_dur}s")
    
    if audio_dur <= video_dur:
        logger.info("Audio shorter than video, combining directly with GPU")
        result = combine_video_audio(processed_video_path, audio_path, output_path, quality_preset)
        # Clean up scaled video if it was created
        if str(processed_video_path) != str(video_path):
            try:
                Path(processed_video_path).unlink()
            except:
                pass
        
        elapsed_time = time.time() - start_time
        logger.info(f"GPU processing completed in {format_time(elapsed_time)}")
        return result, elapsed_time
    
    loops_needed = int(audio_dur / video_dur) + 1
    logger.info(f"Looping video {loops_needed} times to match audio duration")
    
    concat_file = Path(output_path).parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for _ in range(loops_needed):
            f.write(f"file '{Path(processed_video_path).resolve()}'\n")
    
    temp_looped = Path(output_path).parent / "temp_looped.mp4"
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(temp_looped)]
    
    logger.info("Concatenating video loops (stream copy)")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"Video looping failed: {result.stderr.decode(errors='ignore')}")
    
    trimmed_video = Path(output_path).parent / "temp_trimmed.mp4"
    cmd = ["ffmpeg", "-y", "-i", str(temp_looped), "-t", str(audio_dur), "-c", "copy", str(trimmed_video)]
    
    logger.info("Trimming looped video to match audio duration (stream copy)")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"Video trimming failed: {result.stderr.decode(errors='ignore')}")
    
    logger.info("Combining trimmed video with audio using GPU")
    final_result = combine_video_audio(trimmed_video, audio_path, output_path, quality_preset)
    
    # Cleanup temporary files
    try:
        Path(concat_file).unlink()
        Path(temp_looped).unlink()
        Path(trimmed_video).unlink()
        if str(processed_video_path) != str(video_path):
            Path(processed_video_path).unlink()
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Successfully created final video with GPU in {format_time(elapsed_time)}: {output_path}")
    return final_result, elapsed_time

def combine_video_audio(video_path, audio_path, output_path, quality_preset="high_quality"):
    """Combine video and audio using GPU - NO CPU FALLBACK"""
    # GPU-ONLY quality presets
    quality_settings = {
        "ultra_fast": {
            "gpu_preset": "p4",
            "cq": "23",
            "multipass": "disabled",
            "spatial_aq": "0",
            "temporal_aq": "0",
            "audio_bitrate": "256k"
        },
        "high_quality": {
            "gpu_preset": "p6",
            "cq": "19",
            "multipass": "fullres",
            "spatial_aq": "1",
            "temporal_aq": "1",
            "audio_bitrate": "320k"
        },
        "maximum_quality": {
            "gpu_preset": "p7",
            "cq": "17",
            "multipass": "fullres",
            "spatial_aq": "1",
            "temporal_aq": "1",
            "audio_bitrate": "320k"
        },
       
    }
    
    selected_quality = quality_settings.get(quality_preset, quality_settings["high_quality"])
    gpu_preset = selected_quality["gpu_preset"]
    cq = selected_quality["cq"]
    multipass = selected_quality["multipass"]
    spatial_aq = selected_quality["spatial_aq"]
    temporal_aq = selected_quality["temporal_aq"]
    audio_bitrate = selected_quality["audio_bitrate"]
    
    # GPU-accelerated encoding with hardware decoding
    cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda",
        "-hwaccel_output_format", "cuda",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "h264_nvenc",
        "-preset", gpu_preset,
        "-tune", "hq",
        "-profile:v", "high",
        "-rc", "vbr",
        "-cq", cq,
        "-rc-lookahead", "32",
        "-spatial-aq", spatial_aq,
        "-temporal-aq", temporal_aq,
        "-bf", "3",
        "-gpu", "0"
    ]
    
    # Add multipass if enabled
    if multipass != "disabled":
        cmd += ["-multipass", multipass]
    
    # For maximum quality, enable additional features
    if quality_preset == "maximum_quality":
        cmd += ["-b_ref_mode", "middle", "-dpb_size", "4"]
    
    cmd += ["-c:a", "aac", "-b:a", audio_bitrate, "-shortest", str(output_path)]
    
    logger.info(f"GPU combining video and audio: {video_path} + {audio_path}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"GPU video-audio combination failed: {result.stderr.decode(errors='ignore')}")
    
    logger.info(f"Successfully GPU-combined video and audio: {output_path}")
    return str(output_path)

def process_single_video_task(task_data):
    """
    Process a single video task with GPU and timing - helper for parallel processing
    
    Args:
        task_data: Dictionary containing:
            - video_path: Path to video file
            - audio_path: Path to audio file
            - output_path: Path for output file
            - quality_preset: Quality preset string
    
    Returns:
        Dictionary with task results, status, and timing info
    """
    start_time = time.time()
    
    try:
        video_path = task_data['video_path']
        audio_path = task_data['audio_path']
        output_path = task_data['output_path']
        quality_preset = task_data.get('quality_preset', 'high_quality')
        
        logger.info(f"Starting GPU task: {Path(video_path).name} -> {Path(output_path).name}")
        
        result_path, processing_time = loop_video_to_match_audio(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            quality_preset=quality_preset
        )
        
        elapsed_time = time.time() - start_time
        
        return {
            'status': 'success',
            'output_path': result_path,
            'video_path': video_path,
            'audio_path': audio_path,
            'error': None,
            'processing_time': processing_time,
            'total_time': elapsed_time
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"GPU task failed for {task_data.get('video_path', 'unknown')}: {str(e)}")
        return {
            'status': 'failed',
            'output_path': None,
            'video_path': task_data.get('video_path'),
            'audio_path': task_data.get('audio_path'),
            'error': str(e),
            'processing_time': 0,
            'total_time': elapsed_time
        }

def process_videos_parallel(tasks, max_workers=4, quality_preset="high_quality"):
    """
    Process multiple videos in parallel using GPU with time tracking
    
    Args:
        tasks: List of dictionaries with video_path, audio_path, output_path
        max_workers: Maximum parallel workers (default: 4 for 24GB GPU)
        quality_preset: Quality preset (default: "high_quality")
    
    Returns:
        Dictionary with results, timing, and statistics
    """
    batch_start_time = time.time()
    
    # Check GPU availability
    gpu_available = check_gpu_available()
    if not gpu_available:
        raise RuntimeError("❌ GPU (NVENC) not available! This version requires NVIDIA GPU with CUDA support.")
    
    # For 24GB GPU, 4 workers is optimal for 1080p
    max_workers = min(max_workers, 6)
    logger.info(f"Using GPU with {max_workers} parallel workers")
    
    # Prepare tasks with settings
    prepared_tasks = []
    for task in tasks:
        task_copy = task.copy()
        task_copy['quality_preset'] = quality_preset
        prepared_tasks.append(task_copy)
    
    results = []
    completed_count = 0
    
    logger.info(f"Starting GPU parallel processing of {len(prepared_tasks)} videos")
    
    # Process tasks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(process_single_video_task, task): task 
            for task in prepared_tasks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                completed_count += 1
                
                if result['status'] == 'success':
                    logger.info(f"✓ GPU completed ({completed_count}/{len(prepared_tasks)}): {Path(result['output_path']).name} in {format_time(result['total_time'])}")
                else:
                    logger.error(f"✗ Failed ({completed_count}/{len(prepared_tasks)}): {Path(task['video_path']).name} - {result['error']}")
                    
            except Exception as e:
                completed_count += 1
                logger.error(f"✗ Exception ({completed_count}/{len(prepared_tasks)}) for {Path(task['video_path']).name}: {str(e)}")
                results.append({
                    'status': 'failed',
                    'output_path': None,
                    'video_path': task['video_path'],
                    'audio_path': task['audio_path'],
                    'error': str(e),
                    'processing_time': 0,
                    'total_time': 0
                })
    
    # Calculate summary
    total_time = time.time() - batch_start_time
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    logger.info(f"GPU batch processing complete in {format_time(total_time)}: {successful} succeeded, {failed} failed")
    
    return {
        'results': results,
        'total_time': total_time,
        'successful_count': successful,
        'failed_count': failed
    }

def process_videos_smart(tasks, max_workers=4, quality_preset="high_quality"):
    """
    Smart GPU processing: automatically decides single or parallel based on task count
    
    Args:
        tasks: List of dictionaries with video_path, audio_path, output_path
        max_workers: Max parallel workers (default: 4)
        quality_preset: Quality preset (default: "high_quality")
    
    Returns:
        Dictionary with results, timing, and statistics
    """
    batch_start_time = time.time()
    
    # Check GPU
    if not check_gpu_available():
        raise RuntimeError("❌ GPU (NVENC) not available! This version requires NVIDIA GPU with CUDA support.")
    
    if len(tasks) == 0:
        return {
            'results': [],
            'total_time': 0,
            'successful_count': 0,
            'failed_count': 0,
            'processing_mode': 'none'
        }
    
    elif len(tasks) == 1:
        # Single video - use direct GPU processing
        logger.info("Single video detected - using direct GPU processing")
        task = tasks[0]
        
        try:
            result_path, processing_time = loop_video_to_match_audio(
                video_path=task['video_path'],
                audio_path=task['audio_path'],
                output_path=task['output_path'],
                quality_preset=quality_preset
            )
            
            total_time = time.time() - batch_start_time
            
            return {
                'results': [{
                    'status': 'success',
                    'output_path': result_path,
                    'video_path': task['video_path'],
                    'audio_path': task['audio_path'],
                    'error': None,
                    'processing_time': processing_time,
                    'total_time': total_time
                }],
                'total_time': total_time,
                'successful_count': 1,
                'failed_count': 0,
                'processing_mode': 'single_gpu'
            }
            
        except Exception as e:
            total_time = time.time() - batch_start_time
            logger.error(f"Single GPU video processing failed: {str(e)}")
            
            return {
                'results': [{
                    'status': 'failed',
                    'output_path': None,
                    'video_path': task['video_path'],
                    'audio_path': task['audio_path'],
                    'error': str(e),
                    'processing_time': 0,
                    'total_time': total_time
                }],
                'total_time': total_time,
                'successful_count': 0,
                'failed_count': 1,
                'processing_mode': 'single_gpu'
            }
    
    else:
        # Multiple videos - use parallel GPU processing
        logger.info(f"Multiple videos detected ({len(tasks)}) - using parallel GPU processing")
        result = process_videos_parallel(tasks, max_workers, quality_preset)
        result['processing_mode'] = 'parallel_gpu'
        return result

def get_audio_name_from_path(audio_path):
    """Extract filename without extension"""
    return Path(audio_path).stem


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("VIDEO PROCESSOR - 100% GPU OPTIMIZED (NO CPU FALLBACK)")
    print("=" * 60)
    
    # Check GPU
    if not check_gpu_available():
        print("\n❌ ERROR: NVIDIA GPU with NVENC not detected!")
        print("This version requires GPU. Please check:")
        print("  - NVIDIA GPU with CUDA support")
        print("  - Latest drivers installed")
        print("  - FFmpeg compiled with nvenc support")
        exit(1)
    
    print("\n✅ GPU detected and ready!")
    print("\nQuality Presets:")
    print("  - ultra_fast: p4, cq=23, 256k audio")
    print("  - high_quality: p6, cq=19, 320k audio (recommended)")
    print("  - maximum_quality: p7, cq=17, 320k audio")
    print("\n" + "=" * 60)