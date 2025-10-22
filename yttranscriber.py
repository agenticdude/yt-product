import streamlit as st
import yt_dlp
import requests
import json
import os
import time
import random
import re
from datetime import datetime
from pathlib import Path
from manager import ProjectManager

class YouTubeTranscriber:
    def __init__(self):
        pass
    
    def sanitize_filename(self, filename):
        """Remove or replace characters that aren't allowed in filenames"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename)
        return filename.strip()[:200]
    
    def extract_channel_name(self, channel_url):
        """Extract channel name from URL"""
        ydl_opts = {'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                return info.get('channel', info.get('uploader', 'Unknown_Channel'))
        except:
            return 'Unknown_Channel'
    
    def extract_videos(self, channel_url, max_videos, sort_by):
        """Extract video URLs and titles from a YouTube channel"""
        ydl_opts = {
            "extract_flat": False,
            "dump_single_json": True,
            "quiet": True
        }
        
        if max_videos:
            ydl_opts["playlistend"] = max_videos
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            videos = info.get("entries", [])
            
        video_data = []
        for v in videos:
            if v and v.get('id') and v.get('title'):
                view_count = v.get('view_count', 0) or 0
                video_info = {
                    'id': v['id'],
                    'title': v['title'],
                    'url': f"https://www.youtube.com/watch?v={v['id']}",
                    'view_count': view_count,
                    'upload_date': v.get('upload_date', ''),
                    'duration': v.get('duration', 0)
                }
                video_data.append(video_info)
        
        # Sort based on user preference
        if sort_by == "Popularity":
            video_data.sort(key=lambda x: x['view_count'], reverse=True)
        else:  # Date
            video_data.sort(key=lambda x: x['upload_date'], reverse=True)
        
        return video_data
    
    def fetch_transcript(self, video_url, retries=5):
        """Fetch transcript with retries"""
        url = "https://tactiq-apps-prod.tactiq.io/transcript"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": "https://tactiq.io",
            "Referer": "https://tactiq.io/",
            "Connection": "keep-alive",
        }
        
        data = {"videoUrl": video_url, "langCode": "en"}
        
        for attempt in range(1, retries + 1):
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code in (200, 201):
                return response.json()
            elif response.status_code == 429:
                wait_time = min(60, 5 * attempt) + random.uniform(0, 3)
                time.sleep(wait_time)
                continue
            else:
                return None
        
        return None
    
    def transcribe_videos(self, project_path, channel_url, video_data, sort_by):
        """Transcribe videos and save to project structure"""
        # Extract channel name
        channel_name = self.extract_channel_name(channel_url)
        channel_name = self.sanitize_filename(channel_name)
        
        # Create channel folder structure using ProjectManager
        pm = ProjectManager()
        channel_path = pm.create_channel_structure(project_path, channel_name)
        
        # Transcripts go to: project_path/channel_name/transcripts/
        transcripts_dir = Path(channel_path) / "transcripts"
        
        successful_transcripts = 0
        total_videos = len(video_data)
        metadata = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, video_info in enumerate(video_data, 1):
            if not st.session_state.yt_is_running:
                break
            
            # Update progress
            progress = i / total_videos
            progress_bar.progress(progress)
            status_text.text(f"Extracting transcripts: {i}/{total_videos}")
            
            video_url = video_info['url']
            video_title = video_info['title']
            
            try:
                resp_json = self.fetch_transcript(video_url)
                if not resp_json:
                    continue
                
                captions = resp_json.get("captions", [])
                if not captions:
                    continue
                
                transcript_text = " ".join(caption["text"] for caption in captions)
                
                if not transcript_text.strip():
                    continue
                
                # Create numbered folder
                folder_name = str(i)
                video_folder = transcripts_dir / folder_name
                video_folder.mkdir(parents=True, exist_ok=True)
                
                # Save transcript
                filename = video_folder / "transcript.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(transcript_text)
                
                # Add to metadata
                metadata.append({
                    "folder": folder_name,
                    "title": video_title,
                    "url": video_url,
                    "views": video_info['view_count'],
                    "upload_date": video_info['upload_date']
                })
                
                successful_transcripts += 1
                
            except Exception as e:
                continue
            
            time.sleep(random.uniform(1, 3))
        
        # Save metadata
        metadata_file = transcripts_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        progress_bar.progress(1.0)
        status_text.empty()
        
        return successful_transcripts, total_videos, channel_name, str(channel_path)


class YouTubeTranscriberApp:
    def __init__(self):
        # Initialize session state
        if 'yt_is_running' not in st.session_state:
            st.session_state.yt_is_running = False
    
    def run(self):
        # Check if project loaded
        if not st.session_state.get('current_project_path'):
            st.warning("⚠️ Please create/load a project in Step 0 first")
            return
        
        # Number of channels
        num_channels = st.number_input(
            "Number of Channels:",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            key="yt_num_channels"
        )
        
        st.markdown("---")
        
        # Channel configuration
        channel_configs = []
        for i in range(num_channels):
            st.markdown(f"### Channel {i+1}")
            
            # Channel URL
            url = st.text_input(
                "Channel URL:",
                key=f"yt_channel_url_{i}",
                placeholder="https://www.youtube.com/@channelname/videos"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                video_option = st.radio(
                    "Extract Videos:",
                    ["All videos", "Specific number"],
                    key=f"yt_option_{i}"
                )
            
            with col2:
                if video_option == "Specific number":
                    num_videos = st.number_input(
                        "Number of Videos:",
                        min_value=1,
                        max_value=1000,
                        value=50,
                        step=10,
                        key=f"yt_num_videos_{i}"
                    )
                else:
                    num_videos = None
                    st.write("")
            
            with col3:
                sort_by = st.radio(
                    "Sort by:",
                    ["Popularity", "Date"],
                    key=f"yt_sort_{i}"
                )
            
            if url.strip():
                channel_configs.append({
                    'url': url.strip(),
                    'max_videos': num_videos,
                    'sort_by': sort_by
                })
            
            st.markdown("---")
        
        # Start/Stop button
        if not st.session_state.yt_is_running:
            if st.button("▶️ Start Extraction", type="primary", use_container_width=True, key="yt_start"):
                if len(channel_configs) < num_channels:
                    st.error(f"❌ Please enter all {num_channels} channel URLs")
                else:
                    st.session_state.yt_is_running = True
                    st.rerun()
        else:
            if st.button("⏹️ Stop", type="secondary", use_container_width=True, key="yt_stop"):
                st.session_state.yt_is_running = False
                st.rerun()
        
        # Run transcription
        if st.session_state.yt_is_running:
            st.markdown("### 🚀 Processing Channels")
            
            transcriber = YouTubeTranscriber()
            project_path = st.session_state.current_project_path
            
            for idx, config in enumerate(channel_configs):
                st.write(f"**Channel {idx+1}/{len(channel_configs)}:** {config['url']}")
                
                try:
                    # Extract videos
                    with st.spinner(f"Extracting videos from channel {idx+1}..."):
                        video_data = transcriber.extract_videos(
                            config['url'],
                            config['max_videos'],
                            config['sort_by']
                        )
                    
                    if not video_data:
                        st.error(f"❌ No videos found in channel {idx+1}")
                        continue
                    
                    st.info(f"✅ Found {len(video_data)} videos")
                    
                    # Transcribe videos
                    successful, total, channel_name, channel_path = transcriber.transcribe_videos(
                        project_path,
                        config['url'],
                        video_data,
                        config['sort_by']
                    )
                    
                    if successful > 0:
                        st.success(f"✅ Channel '{channel_name}': {successful}/{total} transcripts extracted")
                        st.info(f"📁 Saved to: {channel_path}/transcripts/")
                    else:
                        st.warning(f"⚠️ Channel '{channel_name}': No transcripts extracted")
                    
                except Exception as e:
                    st.error(f"❌ Error processing channel {idx+1}: {e}")
                
                if not st.session_state.yt_is_running:
                    st.warning("⚠️ Stopped by user")
                    break
            
            st.balloons()
            st.session_state.yt_is_running = False
            st.success("✅ Extraction complete! Proceed to Step 2 to process with Claude AI.")