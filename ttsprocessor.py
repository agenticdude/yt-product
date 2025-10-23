import streamlit as st
import requests
import json
import os
from pathlib import Path

class TTSProcessor:
    def __init__(self, tts_endpoint):
        self.tts_endpoint = tts_endpoint
    
    def scan_rewritten_folders(self, project_path):
        """Scan project for all rewritten stories"""
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
                
                story_file = story_folder / f"Story_{story_folder.name}.txt"
                if not story_file.exists():
                    continue
                
                # Check if MP3 already exists
                mp3_file = story_folder / f"Story_{story_folder.name}.mp3"
                has_audio = mp3_file.exists()
                
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
                    'story_file': story_file,
                    'story_folder': story_folder,
                    'has_audio': has_audio,
                    'title': metadata.get('title', f'Story {story_folder.name}')
                })
        
        return stories_data
    
    def generate_audio(self, text, output_path, voice="af_sky"):
        """Generate audio using Kokoro TTS - SAME LOGIC AS BEFORE"""
        url = self.tts_endpoint
        
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "speed": 1.0
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=300)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            raise Exception(f"TTS generation failed: {str(e)}")


class TTSProcessorApp:
    def __init__(self):
        # Initialize session state
        if 'tts_scanned_stories' not in st.session_state:
            st.session_state.tts_scanned_stories = []
        if 'tts_selected_stories' not in st.session_state:
            st.session_state.tts_selected_stories = set()
        if 'tts_is_processing' not in st.session_state:
            st.session_state.tts_is_processing = False
    
    def _load_voices_from_json(self):
        voices_file_path = Path("voices.json")
        if voices_file_path.exists():
            with open(voices_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('voices', [])
        return []

    def run(self):
        # Check if project loaded
        if not st.session_state.get('current_project_path'):
            st.warning("⚠️ Please create/load a project in Step 0 first")
            return
        
        # Scan button
        if st.button("🔍 Scan Rewritten Folders", use_container_width=True, key="tts_scan_btn"):
            processor = TTSProcessor(st.session_state.tts_endpoint)
            st.session_state.tts_scanned_stories = processor.scan_rewritten_folders(st.session_state.current_project_path)
            st.session_state.tts_selected_stories = set()
            st.rerun()
        
        if not st.session_state.tts_scanned_stories:
            return
        
        st.success(f"📋 Found {len(st.session_state.tts_scanned_stories)} stories")
        
        # Group by channel
        channels = {}
        for story in st.session_state.tts_scanned_stories:
            ch_name = story['channel_name']
            if ch_name not in channels:
                channels[ch_name] = []
            channels[ch_name].append(story)
        
        # Select All / Deselect All (Global)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("☑️ Select All", use_container_width=True, key="tts_select_all_global"):
                st.session_state.tts_selected_stories = set(range(len(st.session_state.tts_scanned_stories)))
                st.rerun()
        with col2:
            if st.button("☐ Deselect All", use_container_width=True, key="tts_deselect_all_global"):
                st.session_state.tts_selected_stories = set()
                st.rerun()
        
        st.markdown("---")
        
        # Show stories grouped by channel
        for ch_name, ch_stories in sorted(channels.items()):
            st.markdown(f"### 📁 {ch_name} ({len(ch_stories)} stories)")
            
            # Select All / Deselect All for this channel
            col1, col2 = st.columns(2)
            
            # Get indices for this channel
            ch_indices = [i for i, s in enumerate(st.session_state.tts_scanned_stories) if s['channel_name'] == ch_name]
            
            with col1:
                if st.button(f"☑️ Select All", key=f"tts_select_ch_{ch_name}", use_container_width=True):
                    st.session_state.tts_selected_stories.update(ch_indices)
                    st.rerun()
            with col2:
                if st.button(f"☐ Deselect All", key=f"tts_deselect_ch_{ch_name}", use_container_width=True):
                    for idx in ch_indices:
                        st.session_state.tts_selected_stories.discard(idx)
                    st.rerun()
            
            # Show stories
            for story in ch_stories:
                idx = st.session_state.tts_scanned_stories.index(story)
                status = "🔊" if story['has_audio'] else "⏳"
                label = f"{status} Story {story['story_number']}: {story['title'][:60]}..."
                
                is_selected = idx in st.session_state.tts_selected_stories
                
                if st.checkbox(label, value=is_selected, key=f"tts_cb_{idx}"):
                    st.session_state.tts_selected_stories.add(idx)
                else:
                    st.session_state.tts_selected_stories.discard(idx)
            
            st.markdown("---")
        
        # Show selected count
        total_selected = len(st.session_state.tts_selected_stories)
        if total_selected > 0:
            st.info(f"**Selected: {total_selected} stories**")
            
            # Voice selection
            voice = st.selectbox(
                "Select Voice:",
                self._load_voices_from_json(),
                key="tts_voice"
            )
            
            # Skip existing toggle
            skip_existing = st.checkbox("Skip stories with existing audio", value=True, key="tts_skip_existing")
            
            # Filter stories to process
            to_process = []
            for idx in st.session_state.tts_selected_stories:
                story = st.session_state.tts_scanned_stories[idx]
                if not skip_existing or not story['has_audio']:
                    to_process.append(story)
            
            if len(to_process) == 0:
                st.warning("⚠️ No stories to process (all have audio)")
            else:
                # Process button
                if st.button(f"⚡ Generate Audio ({len(to_process)} stories)", 
                           type="primary", use_container_width=True, key="tts_process_btn"):
                    st.session_state.tts_is_processing = True
                    st.rerun()
        else:
            st.warning("⚠️ Please select at least one story")
        
        # Processing
        if st.session_state.tts_is_processing:
            st.markdown("---")
            st.markdown("### 🎙️ Generating Audio with Kokoro TTS")
            
            processor = TTSProcessor(st.session_state.tts_endpoint)
            voice = st.session_state.get('tts_voice', 'af_sky')
            skip_existing = st.session_state.get('tts_skip_existing', True)
            
            # Get stories to process
            to_process = []
            for idx in st.session_state.tts_selected_stories:
                story = st.session_state.tts_scanned_stories[idx]
                if not skip_existing or not story['has_audio']:
                    to_process.append(story)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            
            for i, story in enumerate(to_process):
                status_text.text(f"Generating {i+1}/{len(to_process)}: Story {story['story_number']}...")
                
                try:
                    # Read story text
                    with open(story['story_file'], 'r', encoding='utf-8') as f:
                        story_text = f.read()
                    
                    # Generate audio
                    mp3_path = story['story_folder'] / f"Story_{story['story_number']}.mp3"
                    processor.generate_audio(story_text, mp3_path, voice)
                    
                    success_count += 1
                    
                except Exception as e:
                    st.error(f"❌ Failed Story {story['story_number']}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(to_process))
            
            status_text.empty()
            progress_bar.empty()
            
            st.balloons()
            st.success(f"✅ Successfully generated audio for {success_count}/{len(to_process)} stories!")
            st.session_state.tts_is_processing = False