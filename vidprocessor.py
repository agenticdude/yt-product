"""
Video Processor Module - Step 5
Scans Rewritten folders, processes stories with audio into final videos
Keeps ALL original caption and overlay logic intact
"""

import streamlit as st
import shutil
from pathlib import Path
import json
import random

# Import video processing modules (user must have these)
try:
    from modules.video_processor import (
        check_ffmpeg_available, check_gpu_available, get_media_duration,
        loop_video_to_match_audio, get_audio_name_from_path
    )
    from modules.audio_handler import save_uploaded_file
    from modules.caption_generator import (
        load_whisper_model, transcribe_audio, create_ass_file
    )
    from modules.subtitle_applier import burn_subtitles
    from modules.video_overlay import apply_video_overlay, get_video_duration
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class VideoProcessorScanner:
    def __init__(self):
        self.temp_dir = Path("temp_video_processing")
        self.temp_dir.mkdir(exist_ok=True)
    
    def scan_rewritten_folders(self, project_path):
        """Scan project for stories with audio files ready for video processing"""
        stories_data = []
        project_path = Path(project_path)
        
        # Scan all channel folders
        for channel_dir in sorted(project_path.iterdir()):
            if not channel_dir.is_dir() or channel_dir.name in ['__pycache__', '.git']:
                continue
            
            rewritten_dir = channel_dir / "Rewritten"
            if not rewritten_dir.exists():
                continue
            
            # Scan story folders
            for story_folder in sorted(rewritten_dir.iterdir(), key=lambda x: int(x.name) if x.name.isdigit() else 999999):
                if not story_folder.is_dir() or not story_folder.name.isdigit():
                    continue
                
                # Check if audio exists
                audio_file = story_folder / f"Story_{story_folder.name}.mp3"
                if not audio_file.exists():
                    continue
                
                # Check if video already exists
                video_file = story_folder / f"Story_{story_folder.name}.mp4"
                has_video = video_file.exists()
                
                # Load metadata
                metadata_file = story_folder / "metadata.json"
                metadata = {}
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                stories_data.append({
                    'channel_name': channel_dir.name,
                    'story_number': story_folder.name,
                    'story_folder': story_folder,
                    'audio_path': audio_file,
                    'video_path': video_file,
                    'has_video': has_video,
                    'title': metadata.get('title', f'Story {story_folder.name}'),
                    'metadata': metadata
                })
        
        return stories_data


class VideoProcessorApp:
    def __init__(self):
        self.scanner = VideoProcessorScanner()
        self.temp_dir = self.scanner.temp_dir
        
        # Initialize session state
        if 'vp_scanned_stories' not in st.session_state:
            st.session_state.vp_scanned_stories = []
        if 'vp_selected_stories' not in st.session_state:
            st.session_state.vp_selected_stories = set()
        if 'vp_uploaded_videos' not in st.session_state:
            st.session_state.vp_uploaded_videos = []
    
    def run(self):
        # Check modules
        if not MODULES_AVAILABLE:
            st.error("❌ Required video processing modules not found. Please ensure you have the 'modules' folder with:")
            st.code("""
- modules/video_processor.py
- modules/audio_handler.py
- modules/caption_generator.py
- modules/subtitle_applier.py
- modules/video_overlay.py
            """)
            return
        
        # Check if project loaded
        if not st.session_state.get('current_project_path'):
            st.warning("⚠️ Please create/load a project in Step 0 first")
            return
        
        # Check FFmpeg
        ffmpeg_ok, ffmpeg_err = check_ffmpeg_available()
        if not ffmpeg_ok:
            st.error(f"❌ FFmpeg not available: {ffmpeg_err}")
            return
        
        gpu_available = check_gpu_available()
        if gpu_available:
            st.success("✅ GPU acceleration available")
        else:
            st.info("ℹ️ Using CPU encoding")
        
        st.markdown("---")
        
        # STEP 1: Scan for stories with audio
        st.markdown("### 🔍 Step 1: Scan for Stories with Audio")
        
        if st.button("🔍 Scan Rewritten Folders for Stories with Audio", use_container_width=True, key="vp_scan_btn"):
            st.session_state.vp_scanned_stories = self.scanner.scan_rewritten_folders(st.session_state.current_project_path)
            st.session_state.vp_selected_stories = set()
            st.rerun()
        
        if not st.session_state.vp_scanned_stories:
            st.info("👆 Click scan to find stories with audio files")
            return
        
        st.success(f"📋 Found {len(st.session_state.vp_scanned_stories)} stories with audio")
        
        # Group by channel
        channels = {}
        for story in st.session_state.vp_scanned_stories:
            ch_name = story['channel_name']
            if ch_name not in channels:
                channels[ch_name] = []
            channels[ch_name].append(story)
        
        # Select All / Deselect All
        col1, col2 = st.columns(2)
        with col1:
            if st.button("☑️ Select All", use_container_width=True, key="vp_select_all"):
                st.session_state.vp_selected_stories = set(range(len(st.session_state.vp_scanned_stories)))
                st.rerun()
        with col2:
            if st.button("☐ Deselect All", use_container_width=True, key="vp_deselect_all"):
                st.session_state.vp_selected_stories = set()
                st.rerun()
        
        st.markdown("---")
        
        # Show stories grouped by channel
        for ch_name, ch_stories in sorted(channels.items()):
            st.markdown(f"### 📁 {ch_name} ({len(ch_stories)} stories)")
            
            # Channel select/deselect
            col1, col2 = st.columns(2)
            ch_indices = [i for i, s in enumerate(st.session_state.vp_scanned_stories) if s['channel_name'] == ch_name]
            
            with col1:
                if st.button(f"☑️ Select All", key=f"vp_select_ch_{ch_name}", use_container_width=True):
                    st.session_state.vp_selected_stories.update(ch_indices)
                    st.rerun()
            with col2:
                if st.button(f"☐ Deselect All", key=f"vp_deselect_ch_{ch_name}", use_container_width=True):
                    for idx in ch_indices:
                        st.session_state.vp_selected_stories.discard(idx)
                    st.rerun()
            
            # Show stories
            for story in ch_stories:
                idx = st.session_state.vp_scanned_stories.index(story)
                status = "🎬" if story['has_video'] else "⏳"
                label = f"{status} Story {story['story_number']}: {story['title'][:60]}..."
                
                is_selected = idx in st.session_state.vp_selected_stories
                
                if st.checkbox(label, value=is_selected, key=f"vp_cb_{idx}"):
                    st.session_state.vp_selected_stories.add(idx)
                else:
                    st.session_state.vp_selected_stories.discard(idx)
            
            st.markdown("---")
        
        # Show selected count
        total_selected = len(st.session_state.vp_selected_stories)
        if total_selected == 0:
            st.warning("⚠️ Please select at least one story")
            return
        
        st.info(f"**Selected: {total_selected} stories**")
        
        st.markdown("---")
        
        # STEP 2: Upload Background Videos
        st.markdown("### 📹 Step 2: Upload Background Videos")
        
        uploaded_videos = st.file_uploader(
            "Upload background videos (can be green screen)",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
            accept_multiple_files=True,
            key="vp_videos"
        )
        
        if uploaded_videos:
            st.success(f"✅ {len(uploaded_videos)} video(s) uploaded")
            
            # Save uploaded videos
            video_paths = []
            for vid in uploaded_videos:
                vid_path = self.temp_dir / vid.name
                save_uploaded_file(vid, vid_path)
                video_paths.append(str(vid_path))
            
            st.session_state.vp_uploaded_videos = video_paths
        
        if not st.session_state.vp_uploaded_videos:
            st.info("👆 Please upload at least one background video")
            return
        
        st.markdown("---")
        
        # STEP 3: Assign Videos to Stories
        st.markdown("### 🎯 Step 3: Assign Background Videos to Stories")
        
        assignment_mode = st.radio("Assignment mode:", ["Random", "Manual"], key="vp_assignment_mode")
        
        selected_stories = [st.session_state.vp_scanned_stories[i] for i in sorted(st.session_state.vp_selected_stories)]
        video_names = [Path(vp).name for vp in st.session_state.vp_uploaded_videos]
        
        assignments = {}
        
        if assignment_mode == "Random":
            st.info("Background videos will be randomly assigned to stories")
            video_indices = list(range(len(st.session_state.vp_uploaded_videos)))
            random.shuffle(video_indices)
            for i in range(len(selected_stories)):
                video_idx = video_indices[i % len(st.session_state.vp_uploaded_videos)]
                assignments[i] = video_idx
        else:
            st.markdown("**Select background video for each story:**")
            for i, story in enumerate(selected_stories):
                selected_video = st.selectbox(
                    f"Story {story['story_number']}: {story['title'][:40]}...",
                    video_names,
                    key=f"vp_assign_{i}"
                )
                video_idx = video_names.index(selected_video)
                assignments[i] = video_idx
        
        st.markdown("---")
        
        # STEP 4: Caption Settings with Karaoke Colors (EXACT COPY FROM ORIGINAL)
        st.markdown("### 🎨 Step 4: Caption Settings with Karaoke Colors")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎨 Basic Styling")
            font_name = st.selectbox("Font", ["Arial", "Helvetica", "Verdana", "Times", "Courier"], index=0, key="vp_font")
            font_size = st.slider("Font Size", 10, 72, 24, key="vp_font_size")
            
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                bold = st.checkbox("Bold", value=True, key="vp_bold")
            with col_b2:
                italic = st.checkbox("Italic", value=False, key="vp_italic")
            with col_b3:
                underline = st.checkbox("Underline", value=False, key="vp_underline")
            
            st.markdown("#### 🎨 Karaoke Colors")
            main_text_color = st.color_picker("Main Text Color", "#FFFFFF", help="Color for all words", key="vp_main_color")
            speaking_word_color = st.color_picker("Speaking Word Color", "#FF0000", help="Color when word is spoken", key="vp_speaking_color")
            enable_karaoke = st.checkbox("Enable Karaoke Effect", value=True, help="Words change color as they're spoken", key="vp_karaoke")
            
            st.markdown("#### 🎨 Outline & Background")
            outline_color = st.color_picker("Outline Color", "#000000", key="vp_outline_color")
            back_color_hex = st.color_picker("Background Color", "#000000", key="vp_back_color")
            back_opacity = st.slider("Background Opacity", 0, 255, 128, key="vp_back_opacity")
        
        with col2:
            st.markdown("#### 🎨 Outline & Shadow")
            outline_width = st.slider("Outline Width", 0, 10, 2, key="vp_outline_width")
            shadow_depth = st.slider("Shadow Depth", 0, 10, 2, key="vp_shadow")
            
            st.markdown("#### 📍 Position")
            alignment_options = [
                ("Bottom Left", 1), ("Bottom Center", 2), ("Bottom Right", 3),
                ("Middle Left", 4), ("Center", 5), ("Middle Right", 6),
                ("Top Left", 7), ("Top Center", 8), ("Top Right", 9)
            ]
            alignment = st.selectbox("Alignment", alignment_options, index=1, format_func=lambda x: x[0], key="vp_alignment")[1]
            margin_v = st.slider("Vertical Margin", 0, 100, 20, key="vp_margin")
        
        with st.expander("✨ Advanced Settings"):
            col_a1, col_a2 = st.columns(2)
            
            with col_a1:
                scale_x = st.slider("Scale X (%)", 50, 200, 100, key="vp_scale_x")
                scale_y = st.slider("Scale Y (%)", 50, 200, 100, key="vp_scale_y")
                spacing = st.slider("Spacing", 0, 10, 0, key="vp_spacing")
            
            with col_a2:
                blur_edges = st.slider("Blur Edges", 0, 10, 0, key="vp_blur")
                fade_in = st.slider("Fade In (sec)", 0.0, 2.0, 0.0, 0.1, key="vp_fade_in")
                fade_out = st.slider("Fade Out (sec)", 0.0, 2.0, 0.0, 0.1, key="vp_fade_out")
        
        st.markdown("---")
        
        # STEP 5: Video Overlay (Green Screen) (EXACT COPY FROM ORIGINAL)
        st.markdown("### 🎬 Step 5: Video Overlay (Green Screen)")
        
        enable_overlay = st.checkbox("Enable Video Overlay", key="vp_enable_overlay")
        
        overlay_path = None
        overlay_settings = {}
        
        if enable_overlay:
            uploaded_overlay = st.file_uploader("Upload Overlay Video (with green screen)", type=['mp4', 'mov', 'webm'], key="vp_overlay_video")
            
            if uploaded_overlay:
                overlay_path = self.temp_dir / uploaded_overlay.name
                save_uploaded_file(uploaded_overlay, overlay_path)
                
                try:
                    overlay_duration = get_video_duration(str(overlay_path))
                    st.success(f"✅ Overlay uploaded: {uploaded_overlay.name} ({overlay_duration:.1f}s)")
                except:
                    st.error("❌ Could not read overlay video")
                    overlay_path = None
                
                if overlay_path:
                    col_o1, col_o2 = st.columns(2)
                    
                    with col_o1:
                        st.markdown("#### 🎨 Green Screen")
                        remove_green = st.checkbox("Remove Green Screen", value=True, key="vp_remove_green")
                        if remove_green:
                            green_similarity = st.slider("Similarity", 0.1, 0.9, 0.3, 0.05, help="How close to green", key="vp_green_sim")
                            green_blend = st.slider("Blend", 0.0, 0.3, 0.1, 0.05, help="Edge smoothing", key="vp_green_blend")
                        else:
                            green_similarity = 0.3
                            green_blend = 0.1
                        
                        st.markdown("#### 📍 Position & Size")
                        overlay_position = st.selectbox("Position", [
                            'top-left', 'top-center', 'top-right',
                            'middle-left', 'center', 'middle-right',
                            'bottom-left', 'bottom-center', 'bottom-right'
                        ], index=2, key="vp_overlay_pos")
                        
                        overlay_size = st.slider("Size (% of width)", 10, 50, 20, key="vp_overlay_size")
                    
                    with col_o2:
                        st.markdown("#### ⏰ Timing")
                        timing_mode = st.radio("Timing Mode", ["Specific Time Range", "Start + Original Length"], index=0, key="vp_timing_mode")
                        
                        if timing_mode == "Specific Time Range":
                            overlay_start = st.number_input("Start (seconds)", 0, 99999, 0, key="vp_overlay_start")
                            overlay_end = st.number_input("End (seconds)", 0, 99999, 10, key="vp_overlay_end")
                            
                            if overlay_end <= overlay_start:
                                st.error("End time must be greater than start time")
                            else:
                                st.info(f"Overlay shows from {overlay_start}s to {overlay_end}s ({overlay_end - overlay_start}s total)")
                        else:
                            overlay_start = st.number_input("Start (seconds)", 0, 99999, 0, key="vp_overlay_start2")
                            overlay_end = overlay_start + overlay_duration
                            st.info(f"Overlay shows from {overlay_start}s to {overlay_end:.1f}s ({overlay_duration:.1f}s total)")
                        
                        keep_overlay_audio = st.checkbox("Keep Overlay Audio", value=False, key="vp_keep_audio")
                    
                    overlay_settings = {
                        'timing_mode': 'range' if timing_mode == "Specific Time Range" else 'original',
                        'start_time': overlay_start,
                        'end_time': overlay_end,
                        'position': overlay_position,
                        'size_percent': overlay_size,
                        'remove_green': remove_green,
                        'green_similarity': green_similarity,
                        'green_blend': green_blend,
                        'keep_overlay_audio': keep_overlay_audio
                    }
        
        st.markdown("---")
        
        # STEP 6: Processing Settings
        st.markdown("### ⚙️ Step 6: Processing Settings")
        
        col_gpu1, col_gpu2, col_gpu3 = st.columns(3)
        
        with col_gpu1:
            st.markdown("**🤖 Whisper**")
            whisper_device_option = st.radio(
                "Device",
                ["GPU (CUDA)", "CPU"],
                index=0 if gpu_available else 1,
                key="vp_whisper_gpu",
                disabled=not gpu_available
            )
            whisper_device = "cuda" if "GPU" in whisper_device_option else "cpu"
            whisper_model_size = st.selectbox("Model", ["tiny", "base", "small", "medium"], index=1, key="vp_whisper_model")
        
        with col_gpu2:
            st.markdown("**🎥 FFmpeg**")
            ffmpeg_device_option = st.radio(
                "Device",
                ["GPU (NVENC)", "CPU"],
                index=0 if gpu_available else 1,
                key="vp_ffmpeg_gpu",
                disabled=not gpu_available
            )
            use_gpu_encoding = "GPU" in ffmpeg_device_option
        
        with col_gpu3:
            st.markdown("**📊 Quality**")
            quality_preset = st.selectbox("Preset", ["fastest", "fast", "balanced"], index=1, key="vp_quality")
        
        st.markdown("---")
        
        # STEP 7: Process
        if st.button("🚀 START PROCESSING", type="primary", use_container_width=True, key="vp_process"):
            # Load Whisper model
            with st.spinner(f"Loading Whisper model ({whisper_model_size})..."):
                try:
                    whisper_model = load_whisper_model(
                        whisper_model_size,
                        device=whisper_device,
                        compute_type="float16" if whisper_device == "cuda" else "int8"
                    )
                    st.success("✅ Whisper model loaded")
                except Exception as e:
                    st.error(f"❌ Failed to load Whisper: {e}")
                    return
            
            processed_count = 0
            
            for story_idx, story in enumerate(selected_stories):
                st.markdown(f"### 🎬 Processing Story {story_idx + 1}/{len(selected_stories)}")
                st.markdown(f"**Story {story['story_number']}:** {story['title']}")
                
                audio_file = str(story['audio_path'])
                video_idx = assignments[story_idx]
                video_file = st.session_state.vp_uploaded_videos[video_idx]
                
                st.markdown(f"**Audio:** {Path(audio_file).name}")
                st.markdown(f"**Background:** {Path(video_file).name}")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Transcribe audio
                    status_text.text("🎤 Transcribing audio...")
                    result = transcribe_audio(whisper_model, audio_file)
                    
                    if not result['segments']:
                        st.error(f"❌ No speech detected")
                        continue
                    
                    progress_bar.progress(30)
                    
                    # Create ASS subtitles with karaoke
                    status_text.text("📝 Creating ASS subtitles with karaoke colors...")
                    
                    def hex_to_ass(hex_color):
                        hex_color = hex_color.lstrip('#')
                        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                        return f"&H00{b:02X}{g:02X}{r:02X}"
                    
                    def hex_to_ass_alpha(hex_color, alpha):
                        hex_color = hex_color.lstrip('#')
                        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                        alpha_inv = 255 - alpha
                        return f"&H{alpha_inv:02X}{b:02X}{g:02X}{r:02X}"
                    
                    primary_col = hex_to_ass(main_text_color)
                    outline_col = hex_to_ass(outline_color)
                    back_col = hex_to_ass_alpha(back_color_hex, back_opacity)
                    karaoke_main_col = hex_to_ass(main_text_color)
                    karaoke_speaking_col = hex_to_ass(speaking_word_color)
                    
                    subtitle_path = self.temp_dir / f"subtitles_{story['story_number']}.ass"
                    
                    create_ass_file(
                        result['segments'], str(subtitle_path),
                        font_name=font_name, font_size=font_size,
                        primary_color=primary_col, outline_color=outline_col,
                        back_color=back_col, bold=bold, italic=italic,
                        underline=underline, shadow_depth=shadow_depth,
                        outline_width=outline_width, alignment=alignment,
                        margin_v=margin_v, margin_h=0,
                        scale_x=scale_x, scale_y=scale_y, spacing=spacing,
                        blur_edges=blur_edges, fade_in=fade_in,
                        fade_out=fade_out, enable_karaoke=enable_karaoke,
                        karaoke_main_color=karaoke_main_col,
                        karaoke_speaking_color=karaoke_speaking_col
                    )
                    
                    progress_bar.progress(40)
                    
                    # Loop video to match audio
                    status_text.text("🔄 Matching video to audio duration...")
                    temp_combined = self.temp_dir / f"combined_{story['story_number']}.mp4"
                    
                    loop_video_to_match_audio(
                        video_file, audio_file, str(temp_combined),
                        use_gpu=use_gpu_encoding, quality_preset=quality_preset
                    )
                    
                    progress_bar.progress(60)
                    
                    # Burn subtitles
                    status_text.text("🔥 Burning subtitles...")
                    temp_with_subs = self.temp_dir / f"with_subs_{story['story_number']}.mp4"
                    
                    burn_subtitles(
                        str(temp_combined), str(subtitle_path), str(temp_with_subs),
                        use_gpu=use_gpu_encoding, quality_preset=quality_preset
                    )
                    
                    progress_bar.progress(80)
                    
                    # Apply overlay if enabled
                    if enable_overlay and overlay_path and overlay_path.exists():
                        status_text.text("🎬 Applying video overlay...")
                        final_output = story['video_path']
                        
                        apply_video_overlay(
                            str(temp_with_subs), str(overlay_path), str(final_output),
                            timing_mode=overlay_settings['timing_mode'],
                            start_time=overlay_settings['start_time'],
                            end_time=overlay_settings['end_time'],
                            position=overlay_settings['position'],
                            size_percent=overlay_settings['size_percent'],
                            remove_green=overlay_settings['remove_green'],
                            green_similarity=overlay_settings['green_similarity'],
                            green_blend=overlay_settings['green_blend'],
                            keep_overlay_audio=overlay_settings['keep_overlay_audio'],
                            use_gpu=use_gpu_encoding,
                            quality_preset=quality_preset
                        )
                    else:
                        final_output = story['video_path']
                        shutil.copy(str(temp_with_subs), str(final_output))
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")
                    
                    processed_count += 1
                    st.success(f"✅ **Story {story['story_number']}** → **{final_output.name}**")
                    
                    # Cleanup temp files
                    try:
                        subtitle_path.unlink(missing_ok=True)
                        temp_combined.unlink(missing_ok=True)
                        temp_with_subs.unlink(missing_ok=True)
                    except:
                        pass
                    
                except Exception as e:
                    st.error(f"❌ Error processing Story {story['story_number']}: {str(e)}")
                    continue
            
            st.balloons()
            st.success(f"""
✅ **Processing Complete!**

{processed_count}/{len(selected_stories)} videos processed successfully

Videos saved in their respective story folders as **Story_N.mp4**
            """)