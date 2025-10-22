import streamlit as st
import json
import os
from pathlib import Path

class ProjectManager:
    def __init__(self, default_base_path="Projects"):
        self.default_base_path = default_base_path
        self.projects_list_file = "projects.json"
    
    def load_projects_list(self):
        """Load list of all projects"""
        if os.path.exists(self.projects_list_file):
            try:
                with open(self.projects_list_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_projects_list(self, projects):
        """Save list of all projects"""
        with open(self.projects_list_file, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2)
    
    def create_project(self, project_name, base_path=None):
        """Create new project structure"""
        if not base_path:
            base_path = self.default_base_path
        
        project_path = Path(base_path) / project_name
        
        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create project config
        config = {
            'project_name': project_name,
            'project_path': str(project_path),
            'created_at': str(Path(project_path).stat().st_ctime),
            'channels': []
        }
        
        config_file = project_path / "project_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # Add to projects list
        projects = self.load_projects_list()
        if not any(p['project_name'] == project_name for p in projects):
            projects.append({
                'project_name': project_name,
                'project_path': str(project_path)
            })
            self.save_projects_list(projects)
        
        return str(project_path)
    
    def load_project_config(self, project_path):
        """Load project configuration"""
        config_file = Path(project_path) / "project_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def create_channel_structure(self, project_path, channel_name):
        """Create channel folders: transcripts and Rewritten"""
        channel_path = Path(project_path) / channel_name
        transcripts_path = channel_path / "transcripts"
        rewritten_path = channel_path / "Rewritten"
        
        transcripts_path.mkdir(parents=True, exist_ok=True)
        rewritten_path.mkdir(parents=True, exist_ok=True)
        
        return str(channel_path)

class ProjectManagerApp:
    def __init__(self):
        self.manager = ProjectManager()
    
    def run(self):
        
        # Initialize session state
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'current_project_path' not in st.session_state:
            st.session_state.current_project_path = None
        
        # Load existing projects
        projects = self.manager.load_projects_list()
        project_names = [p['project_name'] for p in projects]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Create new project
            st.markdown("**Create New Project:**")
            new_project_name = st.text_input(
                "Project Name:",
                placeholder="MyYouTubeProject",
                key="pm_new_project"
            )
        
        with col2:
            # Or select existing
            st.markdown("**Or Select Existing:**")
            if project_names:
                selected_project = st.selectbox(
                    "Select Project:",
                    [""] + project_names,
                    key="pm_select_project"
                )
            else:
                selected_project = ""
                st.info("No existing projects")
        
        # Custom path toggle
        use_custom_path = st.checkbox("Use Custom Path", key="pm_custom_path")
        
        custom_path = None
        if use_custom_path:
            custom_path = st.text_input(
                "Custom Base Path:",
                placeholder="/home/user/projects",
                key="pm_custom_path_input"
            )
        
        # Create/Load button
        if st.button("📂 Create/Load Project", type="primary", use_container_width=True, key="pm_create_load"):
            if new_project_name.strip():
                # Create new project
                try:
                    project_path = self.manager.create_project(
                        new_project_name.strip(),
                        custom_path if use_custom_path else None
                    )
                    st.session_state.current_project = new_project_name.strip()
                    st.session_state.current_project_path = project_path
                    st.success(f"✅ Project created: {project_path}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating project: {e}")
            
            elif selected_project:
                # Load existing project
                project_info = next((p for p in projects if p['project_name'] == selected_project), None)
                if project_info:
                    st.session_state.current_project = selected_project
                    st.session_state.current_project_path = project_info['project_path']
                    st.success(f"✅ Project loaded: {project_info['project_path']}")
                    st.rerun()
            else:
                st.warning("⚠️ Please enter a project name or select an existing project")
        
        # Show current project
        if st.session_state.current_project:
            st.markdown("---")
            st.success(f"📂 **Current Project:** {st.session_state.current_project}")
            st.info(f"📁 **Path:** {st.session_state.current_project_path}")
            
            # Show project structure
            if os.path.exists(st.session_state.current_project_path):
                with st.expander("📋 Project Structure", expanded=False):
                    project_path = Path(st.session_state.current_project_path)
                    
                    st.code(f"{st.session_state.current_project}/", language=None)
                    
                    for channel_dir in sorted(project_path.iterdir()):
                        if channel_dir.is_dir() and channel_dir.name != "__pycache__":
                            st.code(f"  ├── {channel_dir.name}/", language=None)
                            
                            transcripts_dir = channel_dir / "transcripts"
                            if transcripts_dir.exists():
                                transcript_count = len(list(transcripts_dir.glob("*/transcript.txt")))
                                st.code(f"  │   ├── transcripts/ ({transcript_count} transcripts)", language=None)
                            
                            rewritten_dir = channel_dir / "Rewritten"
                            if rewritten_dir.exists():
                                story_count = len(list(rewritten_dir.glob("*/Story_*.txt")))
                                st.code(f"  │   └── Rewritten/ ({story_count} stories)", language=None)
        else:
            st.info("👆 Please create or load a project to continue")