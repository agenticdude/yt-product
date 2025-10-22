"""
Caption Generator Module
With 4-5 word chunking and karaoke color effect
"""

from datetime import timedelta
from pathlib import Path
from faster_whisper import WhisperModel

def load_whisper_model(model_size="base", device="cpu", compute_type="int8"):
    """Load Faster-Whisper model"""
    return WhisperModel(model_size, device=device, compute_type=compute_type)

def chunk_text_by_words(text, max_words=5):
    """Split text into chunks of 4-5 words"""
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= max_words:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def transcribe_audio(model, audio_path, language=None):
    """Transcribe audio using Whisper model and chunk into 4-5 word segments"""
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    
    chunked_segments = []
    full_text = []
    
    for segment in segments:
        text = segment.text.strip()
        full_text.append(text)
        
        chunks = chunk_text_by_words(text, max_words=5)
        
        if len(chunks) == 0:
            continue
        
        segment_duration = segment.end - segment.start
        chunk_duration = segment_duration / len(chunks)
        
        for i, chunk in enumerate(chunks):
            chunk_start = segment.start + (i * chunk_duration)
            chunk_end = chunk_start + chunk_duration
            
            chunked_segments.append({
                'start': chunk_start,
                'end': chunk_end,
                'text': chunk
            })
    
    return {
        'text': ' '.join(full_text),
        'segments': chunked_segments,
        'language': info.language
    }

def format_timestamp_ass(seconds):
    """Convert seconds to ASS timestamp format (h:mm:ss.cc)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"

def create_ass_file(segments, output_path, font_name="Arial", font_size=24,
                    primary_color="&H00FFFFFF", outline_color="&H00000000",
                    back_color="&H80000000", bold=True, italic=False,
                    underline=False, shadow_depth=2, outline_width=2,
                    alignment=2, margin_v=20, margin_h=0, scale_x=100, 
                    scale_y=100, spacing=0, blur_edges=0, fade_in=0.0, 
                    fade_out=0.0, enable_karaoke=False,
                    karaoke_main_color="&H00FFFFFF", karaoke_speaking_color="&H000000FF"):
    """Create ASS subtitle file with karaoke color effect"""
    
    header = f"""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{primary_color},{outline_color},{back_color},{-1 if bold else 0},{-1 if italic else 0},{-1 if underline else 0},0,{scale_x},{scale_y},{spacing},0,1,{outline_width},{shadow_depth},{alignment},{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header)
        
        for segment in segments:
            start_time = format_timestamp_ass(segment['start'])
            end_time = format_timestamp_ass(segment['end'])
            text = segment['text'].strip()
            
            effect_tags = ""
            
            if fade_in > 0 or fade_out > 0:
                fade_in_ms = int(fade_in * 1000)
                fade_out_ms = int(fade_out * 1000)
                effect_tags += f"\\fad({fade_in_ms},{fade_out_ms})"
            
            if blur_edges > 0:
                effect_tags += f"\\be{blur_edges}"
            
            if enable_karaoke:
                words = text.split()
                duration = segment['end'] - segment['start']
                word_duration = (duration / len(words)) if words else duration
                k_time = int(word_duration * 100)
                
                karaoke_text = ""
                for word in words:
                    karaoke_text += f"{{\\k{k_time}\\c{karaoke_speaking_color}}}{word} "
                
                text = f"{{\\c{karaoke_main_color}}}{karaoke_text.strip()}"
            
            final_text = f"{effect_tags}{text}" if effect_tags else text
            
            f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{final_text}\n")
    
    return str(output_path)
