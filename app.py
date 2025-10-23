import streamlit as st
from manager import ProjectManagerApp
from thumbnail import ThumbnailGeneratorApp
from ttsprocessor import TTSProcessorApp
from yttranscriber import YouTubeTranscriberApp
from clprocessor import StoryProcessorApp
from vidprocessor import VideoProcessorApp

# Page configuration
st.set_page_config(
    page_title="YouTube & Story Processing Suite",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .step-header {
        font-size: 1.8rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #667eea;
    }
    .stButton>button {
        width: 100%;
    }
    .section-divider {
        margin: 3rem 0;
        border-top: 3px solid #667eea;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">🎬 YouTube & Story Processing Suite</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'claude_api_key' not in st.session_state:
        st.session_state.claude_api_key = ""
    if 'tts_endpoint' not in st.session_state:
        st.session_state.tts_endpoint = "http://localhost:8080/v1/audio/speech"
    
    # ==================== STEP 0: Project Manager ====================
    st.markdown("## 📁 Step 0: Project Manager")
    st.markdown("Create or load a project to organize your work")
    
    ProjectManagerApp().run()
    
    # Check if project is loaded
    if not st.session_state.get('current_project'):
        st.warning("⚠️ Please create or load a project to continue with other steps")
        return
    
    # Load project-specific API keys if a project is loaded
    if st.session_state.get('current_project_path'):
        manager = ProjectManagerApp().manager # Access the ProjectManager instance
        project_config = manager.load_project_config(st.session_state.current_project_path)
        if project_config:
            if 'claude_api_key' in project_config and project_config['claude_api_key']:
                st.session_state.claude_api_key = project_config['claude_api_key']
            if 'tts_endpoint' in project_config and project_config['tts_endpoint']:
                st.session_state.tts_endpoint = project_config['tts_endpoint']

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ==================== STEP 0.5: API Configuration ====================
    st.markdown("## 🔑 API Configuration")
    st.markdown("Configure your API credentials and endpoints")
    
    with st.expander("⚙️ API Settings", expanded=not st.session_state.claude_api_key):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Claude AI API")
            claude_key = st.text_input(
                "Claude API Key:",
                value=st.session_state.claude_api_key,
                type="password",
                key="claude_api_key_input",
                help="Get your API key from https://console.anthropic.com/"
            )
            
            if claude_key != st.session_state.claude_api_key:
                st.session_state.claude_api_key = claude_key
                if st.session_state.get('current_project_path'):
                    manager = ProjectManagerApp().manager
                    project_config = manager.load_project_config(st.session_state.current_project_path)
                    if project_config:
                        project_config['claude_api_key'] = claude_key
                        manager.save_project_config(st.session_state.current_project_path, project_config)
                if claude_key:
                    st.success("✅ Claude API Key updated")
            
            if st.session_state.claude_api_key:
                st.success("✅ Claude API Key is configured")
            else:
                st.warning("⚠️ Claude API Key is required for Step 2")
        
        with col2:
            st.markdown("### Kokoro TTS API")
            tts_endpoint = st.text_input(
                "TTS Endpoint URL:",
                value=st.session_state.tts_endpoint,
                key="tts_endpoint_input",
                help="Default: http://localhost:8080/v1/audio/speech"
            )
            
            if tts_endpoint != st.session_state.tts_endpoint:
                st.session_state.tts_endpoint = tts_endpoint
                if st.session_state.get('current_project_path'):
                    manager = ProjectManagerApp().manager
                    project_config = manager.load_project_config(st.session_state.current_project_path)
                    if project_config:
                        project_config['tts_endpoint'] = tts_endpoint
                        manager.save_project_config(st.session_state.current_project_path, project_config)
                st.success("✅ TTS Endpoint updated")
            
            if st.session_state.tts_endpoint:
                st.success("✅ TTS Endpoint is configured")
            else:
                st.warning("⚠️ TTS Endpoint is required for Step 3")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ==================== STEP 1: YouTube Transcriber ====================
    st.markdown("## 📺 Step 1: YouTube Channel Transcriber")
    st.markdown("Extract transcripts from YouTube channels")
    
    YouTubeTranscriberApp().run()
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ==================== STEP 2: Story Processor ====================
    st.markdown("## 📖 Step 2: Story Processor with Claude AI")
    st.markdown("Scan transcripts and process with Claude AI")
    
    if not st.session_state.claude_api_key:
        st.warning("⚠️ Please configure Claude API Key in API Configuration to use this feature")
    else:
        StoryProcessorApp().run()
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ==================== STEP 3: TTS Processor ====================
    st.markdown("## 🎙️ Step 3: Text-to-Speech Processor")
    st.markdown("Convert rewritten stories to audio using Kokoro TTS")
    
    if not st.session_state.tts_endpoint:
        st.warning("⚠️ Please configure TTS Endpoint in API Configuration to use this feature")
    else:
        TTSProcessorApp().run()
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ==================== STEP 4: Thumbnail Generator ====================
    st.markdown("## 🎨 Step 4: Thumbnail Generator")
    st.markdown("Create eye-catching thumbnails from story metadata")
    
    ThumbnailGeneratorApp().run()
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # ==================== STEP 5: Video Processor ====================
    st.markdown("## 🎬 Step 5: Video Processor")
    st.markdown("Generate final videos with captions, karaoke effects, and green screen overlays")
    
    VideoProcessorApp().run()
    
    # ==================== Footer ====================
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p>🎬 YouTube & Story Processing Suite v2.0</p>
        <p>Extract → Rewrite → Generate Audio → Create Thumbnails → Generate Videos</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()