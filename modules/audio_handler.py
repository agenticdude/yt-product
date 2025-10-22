"""
Audio Handler Module
"""

from pathlib import Path

def scan_folder_for_videos(folder_path):
    """Scan folder for video files"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    folder = Path(folder_path)
    
    if not folder.exists():
        return []
    
    video_files = []
    for ext in video_extensions:
        video_files.extend(folder.glob(f"*{ext}"))
        video_files.extend(folder.glob(f"*{ext.upper()}"))
    
    return sorted([str(f) for f in video_files])

def scan_folder_for_audios(folder_path):
    """Scan folder for audio files"""
    audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
    folder = Path(folder_path)
    
    if not folder.exists():
        return []
    
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(folder.glob(f"*{ext}"))
        audio_files.extend(folder.glob(f"*{ext.upper()}"))
    
    return sorted([str(f) for f in audio_files])

def save_uploaded_file(uploaded_file, destination_path):
    """Save uploaded file to destination"""
    with open(destination_path, "wb") as f:
        f.write(uploaded_file.read())
    return str(destination_path)
