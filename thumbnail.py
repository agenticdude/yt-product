import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json
import random
import io
from pathlib import Path

class ThumbnailGenerator:
    def __init__(self):
        pass
    
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
                
                metadata_file = story_folder / "metadata.json"
                if not metadata_file.exists():
                    continue
                
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    continue
                
                thumbnail_file = story_folder / "thumbnail.png"
                has_thumbnail = thumbnail_file.exists()
                
                source_file = story_folder / "source_info.json"
                source_info = {}
                if source_file.exists():
                    try:
                        with open(source_file, 'r', encoding='utf-8') as f:
                            source_info = json.load(f)
                    except:
                        pass
                
                stories_data.append({
                    'channel_name': channel_dir.name,
                    'story_number': story_folder.name,
                    'story_folder': story_folder,
                    'metadata': metadata,
                    'has_thumbnail': has_thumbnail,
                    'source_info': source_info
                })
        
        return stories_data
    
    def calculate_optimal_font_size(self, text, font_family, bold, max_width, max_height, initial_size):
        """Calculate optimal font size to fit text"""
        font_size = initial_size
        min_font_size = 20
        
        while font_size >= min_font_size:
            font_suffix = "-Bold" if bold else ""
            try:
                test_font = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVu{font_family}{font_suffix}.ttf", font_size)
            except:
                try:
                    test_font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    test_font = ImageFont.load_default()
                    break
            
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = test_font.getbbox(test_line)
                width = bbox[2] - bbox[0]
                
                if width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            line_height = font_size + 12
            total_height = len(lines) * line_height
            
            if total_height <= max_height:
                return font_size
            
            font_size -= 2
        
        return min_font_size
    
    def assign_word_colors(self, words, num_colors, color1, color2, color3):
        """Assign colors to words based on weighted random distribution"""
        color_assignments = []
        
        for word in words:
            if num_colors == 1:
                color_assignments.append(color1)
            elif num_colors == 2:
                if random.random() < 0.65:
                    color_assignments.append(color1)
                else:
                    color_assignments.append(color2)
            else:
                rand = random.random()
                if rand < 0.60:
                    color_assignments.append(color1)
                elif rand < 0.85:
                    color_assignments.append(color2)
                else:
                    color_assignments.append(color3)
        
        return color_assignments
    
    def wrap_text_with_colors(self, text, font, max_width, color_assignments):
        """Wrap text and maintain color assignments"""
        words = text.split()
        lines = []
        current_line = []
        current_colors = []
        
        for i, word in enumerate(words):
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
                current_colors.append(color_assignments[i])
            else:
                if current_line:
                    lines.append((current_line.copy(), current_colors.copy()))
                current_line = [word]
                current_colors = [color_assignments[i]]
        
        if current_line:
            lines.append((current_line, current_colors))
        
        return lines
    
    def resize_headshot_maintain_aspect(self, headshot_image, target_width, target_height):
        """Resize headshot maintaining aspect ratio and crop to fit"""
        # Get original dimensions
        orig_width, orig_height = headshot_image.size
        orig_aspect = orig_width / orig_height
        target_aspect = target_width / target_height
        
        # Calculate new dimensions to fill target area
        if orig_aspect > target_aspect:
            # Image is wider - fit to height and crop width
            new_height = target_height
            new_width = int(orig_aspect * new_height)
        else:
            # Image is taller - fit to width and crop height
            new_width = target_width
            new_height = int(new_width / orig_aspect)
        
        # Resize image
        resized = headshot_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop to target size (center crop)
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        cropped = resized.crop((left, top, right, bottom))
        
        return cropped
    
    def generate_thumbnail(self, story_text, bottom_text, bg_color, text_font_size, text_font_family, 
                          text_bold, num_text_colors, text_color1, text_color2, text_color3,
                          bottom_bar_color, bottom_bar_text_color, bottom_bar_font_size, bottom_bar_bold,
                          headshot_image, headshot_position, background_image=None):
        """Generate thumbnail with all settings"""
        
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), bg_color)
        
        if background_image:
            bg = background_image.resize((width, height))
            img.paste(bg, (0, 0))
        
        draw = ImageDraw.Draw(img)
        
        # Add headshot with aspect ratio maintained
        headshot_width = 340
        headshot_height = 500
        
        if headshot_position == "Left":
            headshot_x = 40
            text_area_x = headshot_x + headshot_width + 60
            text_area_width = width - text_area_x - 40
        else:
            text_area_x = 40
            text_area_width = width - headshot_width - 140
            headshot_x = width - headshot_width - 40
        
        headshot_y = 80
        
        # Resize headshot maintaining aspect ratio
        headshot_resized = self.resize_headshot_maintain_aspect(headshot_image, headshot_width, headshot_height)
        img.paste(headshot_resized, (headshot_x, headshot_y))
        
        # Main text
        words = story_text.split()
        color_assignments = self.assign_word_colors(words, num_text_colors, text_color1, text_color2, text_color3)
        
        font_suffix = "-Bold" if text_bold else ""
        try:
            font = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVu{text_font_family}{font_suffix}.ttf", text_font_size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", text_font_size)
            except:
                font = ImageFont.load_default()
        
        text_area_height = 500
        optimal_font_size = self.calculate_optimal_font_size(
            story_text, text_font_family, text_bold, text_area_width, text_area_height, text_font_size
        )
        
        try:
            font = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVu{text_font_family}{font_suffix}.ttf", optimal_font_size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", optimal_font_size)
            except:
                font = ImageFont.load_default()
        
        lines = self.wrap_text_with_colors(story_text, font, text_area_width, color_assignments)
        
        line_height = optimal_font_size + 12
        total_text_height = len(lines) * line_height
        text_start_y = 80 + (text_area_height - total_text_height) // 2
        
        y_offset = text_start_y
        for line_words, line_colors in lines:
            line_text = ' '.join(line_words)
            bbox = font.getbbox(line_text)
            line_width = bbox[2] - bbox[0]
            x_offset = text_area_x + (text_area_width - line_width) // 2
            
            for word, color in zip(line_words, line_colors):
                draw.text((x_offset, y_offset), word, font=font, fill=color)
                word_bbox = font.getbbox(word)
                word_width = word_bbox[2] - word_bbox[0]
                x_offset += word_width + font.getbbox(' ')[2]
            
            y_offset += line_height
        
        # Bottom bar
        bar_height = 100
        bar_y = height - bar_height
        draw.rectangle([(0, bar_y), (width, height)], fill=bottom_bar_color)
        
        bar_font_suffix = "-Bold" if bottom_bar_bold else ""
        try:
            bar_font = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{bar_font_suffix}.ttf", bottom_bar_font_size)
        except:
            try:
                bar_font = ImageFont.truetype("arial.ttf", bottom_bar_font_size)
            except:
                bar_font = ImageFont.load_default()
        
        bar_bbox = bar_font.getbbox(bottom_text)
        bar_text_width = bar_bbox[2] - bar_bbox[0]
        bar_text_height = bar_bbox[3] - bar_bbox[1]
        bar_text_x = (width - bar_text_width) // 2
        bar_text_y = bar_y + (bar_height - bar_text_height) // 2
        
        draw.text((bar_text_x, bar_text_y), bottom_text, font=bar_font, fill=bottom_bar_text_color)
        
        return img


class ThumbnailGeneratorApp:
    def __init__(self):
        self.generator = ThumbnailGenerator()
    
    def run(self):
        # Check if project loaded
        if not st.session_state.get('current_project_path'):
            st.warning("⚠️ Please create/load a project in Step 0 first")
            return
        
        # Session state
        if 'tg_scanned_stories' not in st.session_state:
            st.session_state.tg_scanned_stories = []
        if 'tg_selected_stories' not in st.session_state:
            st.session_state.tg_selected_stories = []
        if 'tg_preview_image' not in st.session_state:
            st.session_state.tg_preview_image = None
        
        # Scan button
        if st.button("🔍 Scan Rewritten Folders to Create Thumbnails", use_container_width=True, key="tg_scan_btn"):
            st.session_state.tg_scanned_stories = self.generator.scan_rewritten_folders(st.session_state.current_project_path)
            st.session_state.tg_selected_stories = []
            st.rerun()
        
        if not st.session_state.tg_scanned_stories:
            return
        
        st.success(f"📋 Found {len(st.session_state.tg_scanned_stories)} stories")
        
        # Group by channel
        channels = {}
        for story in st.session_state.tg_scanned_stories:
            ch_name = story['channel_name']
            if ch_name not in channels:
                channels[ch_name] = []
            channels[ch_name].append(story)
        
        # Select All / Deselect All
        col1, col2 = st.columns(2)
        with col1:
            if st.button("☑️ Select All", use_container_width=True, key="tg_select_all"):
                st.session_state.tg_selected_stories = list(range(len(st.session_state.tg_scanned_stories)))
                st.rerun()
        with col2:
            if st.button("☐ Deselect All", use_container_width=True, key="tg_deselect_all"):
                st.session_state.tg_selected_stories = []
                st.rerun()
        
        # Story selection
        st.markdown("### 📚 Stories")
        for ch_name, ch_stories in sorted(channels.items()):
            st.markdown(f"**📁 {ch_name}**")
            
            for story in ch_stories:
                idx = st.session_state.tg_scanned_stories.index(story)
                status = "✅" if story['has_thumbnail'] else "⏳"
                label = f"{status} Story {story['story_number']}: {story['metadata'].get('thumbnail', '')[:50]}..."
                
                if st.checkbox(label, value=(idx in st.session_state.tg_selected_stories), key=f"tg_story_{idx}"):
                    if idx not in st.session_state.tg_selected_stories:
                        st.session_state.tg_selected_stories.append(idx)
                else:
                    if idx in st.session_state.tg_selected_stories:
                        st.session_state.tg_selected_stories.remove(idx)
        
        if not st.session_state.tg_selected_stories:
            st.warning("⚠️ Please select at least one story")
            return
        
        st.info(f"**Selected: {len(st.session_state.tg_selected_stories)} stories**")
        
        st.markdown("---")
        
        # Global Theme Settings
        st.markdown("### 🎨 Global Theme Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            bg_file = st.file_uploader("Background Image (optional)", type=['png', 'jpg', 'jpeg'], key="tg_bg")
            bg_image = Image.open(bg_file) if bg_file else None
        with col2:
            bg_color = st.color_picker("Background Color", "#1a1a1a", key="tg_bg_color")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            text_font_size = st.slider("Font Size", 20, 60, 34, key="tg_font_size")
        with col2:
            text_font_family = st.selectbox("Font", ["Sans", "Sans-Bold", "Serif", "Serif-Bold"], key="tg_font")
        with col3:
            text_bold = st.checkbox("Bold Text", value=False, key="tg_bold")
        
        num_colors = st.radio("Text Colors:", [1, 2, 3], horizontal=True, key="tg_num_colors")
        
        color_cols = st.columns(3)
        with color_cols[0]:
            color1 = st.color_picker("Color 1", "#FFFFFF", key="tg_color1")
        with color_cols[1]:
            color2 = st.color_picker("Color 2", "#FFD700", key="tg_color2") if num_colors >= 2 else "#FFD700"
        with color_cols[2]:
            color3 = st.color_picker("Color 3", "#FF6B6B", key="tg_color3") if num_colors >= 3 else "#FF6B6B"
        
        st.markdown("**📊 Bottom Bar:**")
        col1, col2 = st.columns(2)
        with col1:
            bar_color = st.color_picker("Bar Color", "#DC143C", key="tg_bar_color")
            bar_font_size = st.slider("Bar Font Size", 30, 80, 55, key="tg_bar_font_size")
        with col2:
            bar_text_color = st.color_picker("Bar Text Color", "#FFFF00", key="tg_bar_text_color")
            bar_bold = st.checkbox("Bold Bottom Text", value=True, key="tg_bar_bold")
        
        st.markdown("---")
        
        # Headshot Mode
        st.markdown("### 🖼️ Headshot Mode")
        
        headshot_mode = st.radio(
            "Choose headshot mode:",
            ["Random (upload multiple, use randomly)", "Individual (one per story)"],
            key="tg_headshot_mode"
        )
        
        headshots_data = {}
        
        if "Random" in headshot_mode:
            st.markdown("**📸 Upload Multiple Headshots:**")
            uploaded_files = st.file_uploader(
                "Select multiple images (required)",
                type=['png', 'jpg', 'jpeg'],
                accept_multiple_files=True,
                key="tg_random_headshots"
            )
            
            if uploaded_files:
                st.success(f"✅ Uploaded {len(uploaded_files)} headshots")
                headshot_images = [Image.open(f) for f in uploaded_files]
                position = st.selectbox("Headshot Position:", ["Right", "Left"], key="tg_random_pos")
                
                for idx in st.session_state.tg_selected_stories:
                    headshots_data[idx] = {
                        'image': random.choice(headshot_images),
                        'position': position
                    }
            else:
                st.warning("⚠️ Please upload at least one headshot")
        
        else:
            st.markdown("**📸 Upload Headshot for Each Story:**")
            for idx in st.session_state.tg_selected_stories:
                story = st.session_state.tg_scanned_stories[idx]
                with st.expander(f"Story {story['story_number']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        headshot_file = st.file_uploader(
                            "Upload headshot:",
                            type=['png', 'jpg', 'jpeg'],
                            key=f"tg_ind_headshot_{idx}"
                        )
                    with col2:
                        position = st.selectbox("Position:", ["Right", "Left"], key=f"tg_ind_pos_{idx}")
                    
                    if headshot_file:
                        headshots_data[idx] = {
                            'image': Image.open(headshot_file),
                            'position': position
                        }
            
            missing = len(st.session_state.tg_selected_stories) - len(headshots_data)
            if missing > 0:
                st.warning(f"⚠️ {missing} stories missing headshots")
        
        st.markdown("---")
        
        # Preview (First story only)
        st.markdown("### 👁️ Preview (First Story)")
        
        if st.session_state.tg_selected_stories and len(headshots_data) > 0:
            first_idx = st.session_state.tg_selected_stories[0]
            story = st.session_state.tg_scanned_stories[first_idx]
            
            st.info(f"Previewing: Story {story['story_number']}")
            
            if st.button("👁️ Generate Preview", use_container_width=True, key="tg_preview_btn"):
                if first_idx not in headshots_data:
                    st.error("⚠️ First story missing headshot")
                else:
                    with st.spinner("Generating..."):
                        thumbnail_text = story['metadata'].get('thumbnail', 'No text')
                        hook_text = story['metadata'].get('hook', '¡MIRA LO QUE PASÓ!')
                        
                        thumbnail = self.generator.generate_thumbnail(
                            story_text=thumbnail_text,
                            bottom_text=hook_text,
                            bg_color=bg_color,
                            text_font_size=text_font_size,
                            text_font_family=text_font_family,
                            text_bold=text_bold,
                            num_text_colors=num_colors,
                            text_color1=color1,
                            text_color2=color2,
                            text_color3=color3,
                            bottom_bar_color=bar_color,
                            bottom_bar_text_color=bar_text_color,
                            bottom_bar_font_size=bar_font_size,
                            bottom_bar_bold=bar_bold,
                            headshot_image=headshots_data[first_idx]['image'],
                            headshot_position=headshots_data[first_idx]['position'],
                            background_image=bg_image
                        )
                        
                        st.session_state.tg_preview_image = thumbnail
                        st.rerun()
            
            if st.session_state.tg_preview_image:
                st.image(st.session_state.tg_preview_image, use_container_width=True)
        
        st.markdown("---")
        
        # Execute
        skip_existing = st.checkbox("Skip existing thumbnails", value=True, key="tg_skip")
        
        stories_to_process = [
            idx for idx in st.session_state.tg_selected_stories
            if not skip_existing or not st.session_state.tg_scanned_stories[idx]['has_thumbnail']
        ]
        
        if len(headshots_data) < len(st.session_state.tg_selected_stories):
            st.error("⚠️ Please upload headshots for all selected stories")
        elif len(stories_to_process) == 0:
            st.warning("⚠️ No stories to process")
        else:
            if st.button(f"⚡ Generate Thumbnails ({len(stories_to_process)} stories)", 
                        type="primary", use_container_width=True, key="tg_execute"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                
                for i, idx in enumerate(stories_to_process):
                    story = st.session_state.tg_scanned_stories[idx]
                    status_text.text(f"Generating {i+1}/{len(stories_to_process)}: Story {story['story_number']}")
                    
                    try:
                        thumbnail_text = story['metadata'].get('thumbnail', 'No text')
                        hook_text = story['metadata'].get('hook', '¡MIRA LO QUE PASÓ!')
                        
                        thumbnail = self.generator.generate_thumbnail(
                            story_text=thumbnail_text,
                            bottom_text=hook_text,
                            bg_color=bg_color,
                            text_font_size=text_font_size,
                            text_font_family=text_font_family,
                            text_bold=text_bold,
                            num_text_colors=num_colors,
                            text_color1=color1,
                            text_color2=color2,
                            text_color3=color3,
                            bottom_bar_color=bar_color,
                            bottom_bar_text_color=bar_text_color,
                            bottom_bar_font_size=bar_font_size,
                            bottom_bar_bold=bar_bold,
                            headshot_image=headshots_data[idx]['image'],
                            headshot_position=headshots_data[idx]['position'],
                            background_image=bg_image
                        )
                        
                        output_path = story['story_folder'] / "thumbnail.png"
                        thumbnail.save(output_path)
                        
                        settings = {
                            'bg_color': bg_color,
                            'text_font_size': text_font_size,
                            'text_font_family': text_font_family,
                            'text_bold': text_bold,
                            'num_colors': num_colors,
                            'color1': color1,
                            'color2': color2,
                            'color3': color3,
                            'bar_color': bar_color,
                            'bar_text_color': bar_text_color,
                            'bar_font_size': bar_font_size,
                            'bar_bold': bar_bold,
                            'headshot_position': headshots_data[idx]['position']
                        }
                        
                        settings_path = story['story_folder'] / "thumbnail_settings.json"
                        with open(settings_path, 'w', encoding='utf-8') as f:
                            json.dump(settings, f, indent=2)
                        
                        success_count += 1
                        
                    except Exception as e:
                        st.error(f"❌ Story {story['story_number']}: {str(e)}")
                    
                    progress_bar.progress((i + 1) / len(stories_to_process))
                
                status_text.empty()
                progress_bar.empty()
                
                st.success(f"✅ Generated {success_count}/{len(stories_to_process)} thumbnails!")