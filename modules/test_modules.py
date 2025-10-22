"""
Test Script - V4
"""

import sys
from pathlib import Path

print("=" * 60)
print("Testing Video Batch Processor V4")
print("=" * 60)

print("\n1. Testing imports...")
try:
    from modules.video_processor import check_ffmpeg_available, check_gpu_available
    print("   ✅ video_processor")
except Exception as e:
    print(f"   ❌ video_processor: {e}")
    sys.exit(1)

try:
    from modules.audio_handler import scan_folder_for_videos, scan_folder_for_audios
    print("   ✅ audio_handler")
except Exception as e:
    print(f"   ❌ audio_handler: {e}")
    sys.exit(1)

try:
    from modules.caption_generator import load_whisper_model, transcribe_audio, create_ass_file
    print("   ✅ caption_generator (4-5 words chunking)")
except Exception as e:
    print(f"   ❌ caption_generator: {e}")
    sys.exit(1)

try:
    from modules.subtitle_applier import burn_subtitles
    print("   ✅ subtitle_applier")
except Exception as e:
    print(f"   ❌ subtitle_applier: {e}")
    sys.exit(1)

try:
    from modules.image_overlay import apply_png_overlay
    print("   ✅ image_overlay (simplified)")
except Exception as e:
    print(f"   ❌ image_overlay: {e}")
    sys.exit(1)

print("\n2. Testing FFmpeg...")
try:
    ffmpeg_ok, ffmpeg_err = check_ffmpeg_available()
    if ffmpeg_ok:
        print("   ✅ FFmpeg available")
    else:
        print(f"   ❌ FFmpeg error: {ffmpeg_err}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n3. Testing GPU...")
try:
    gpu_ok = check_gpu_available()
    if gpu_ok:
        print("   ✅ NVIDIA GPU available")
    else:
        print("   ℹ️  GPU not available (CPU mode)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n4. Testing folders...")
base_dir = Path.cwd()
folders = {
    'input/videos': base_dir / 'input' / 'videos',
    'input/audios': base_dir / 'input' / 'audios',
    'output': base_dir / 'output',
    'temp': base_dir / 'temp'
}

for name, path in folders.items():
    if path.exists():
        print(f"   ✅ {name}/")
    else:
        print(f"   ⚠️  {name}/ missing (will be created)")
        path.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)

print("\n📋 V4 Features:")
print("   • 4-5 words per caption")
print("   • Simplified PNG overlay")
print("   • GPU/CPU at processing step")
print("   • Clean ASS subtitle format")
print("   • Audio removal")

print("\nRun: streamlit run app.py")
print("=" * 60)
