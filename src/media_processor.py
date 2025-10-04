
import os
from moviepy import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from moviepy.video import fx as vfx

os.environ["FFMPEG_BINARY"] = "C:/ffmpeg/bin/ffmpeg.exe"

# --- STAGE 5 (Video Clip Generation - SIMPLIFIED) ---
# This function is now just a placeholder for the flow, 
# as the T2V model in generator.py already produces the final clip.
def process_scene_clip(config, scene_id, video_path, motion_prompt):
    """
    Placeholder: The T2V model generated the clip. This step can be used for 
    optional post-processing like adding music, text overlay, or final resizing.
    """
    print(f"Post-processing dynamic clip for Scene {scene_id}...")

    # We can use MoviePy here to, for example, ensure the duration is exact
    clip = VideoFileClip(video_path)
    required_duration = config.get('scene_duration_seconds', 7)
    
    if clip.duration > required_duration:
        clip = clip.subclip(0, required_duration)
        new_path = os.path.join(config['output_dir'], f"scene_{scene_id}_proc.mp4")
        clip.write_videofile(
            new_path,
            fps=24,
            codec='libx264',
            audio=False,
            logger=None
        )
        clip.close()
        # Rename original file to processed file
        os.remove(video_path)
        os.rename(new_path, video_path)
        print(f"✅ Clip duration adjusted to {required_duration}s.")
        return video_path
    
    clip.close()
    return video_path


# --- STAGE 6.1: Final Reel Assembly (MoviePy) ---
def assemble_final_reel(config, clip_paths, story_data):
    """Loads clip paths and stitches them into the final video reel."""
    print("\n--- Stitching Final Reel ---")
    final_reel_path = os.path.join(config['output_dir'], config['final_reel_name'])
    
    all_clips = []
    # Load all clips from their paths
    for path in clip_paths:
        try:
            clip = VideoFileClip(path) 
            all_clips.append(clip)
        except Exception as e:
            print(f"Warning: Could not load clip {path}. Skipping. Error: {e}")
            
    if not all_clips:
        raise Exception("No valid video clips were generated or loaded for final assembly.")

    # Concatenate all scene clips
    final_clip = concatenate_videoclips(all_clips)

    # Add Narration Text Overlay (Optional Enhancement)
    # The Text-to-Speech step is missing, so we'll just add the text as a subtitle
    final_composite = [final_clip]
    current_time = 0
    for scene in story_data['scenes']:
        text_clip = TextClip(
            text=scene['description'],  
            font_size=50, 
            color='white', 
            stroke_color='black', 
            stroke_width=2,
            font='Arial-Bold',
            bg_color='rgba(0,0,0,0.5)', # Semi-transparent background
            method='label' 
        ).set_position(('center', 'bottom')).set_duration(config.get('scene_duration_seconds', 7)).set_start(current_time)
        
        final_composite.append(text_clip)
        current_time += config.get('scene_duration_seconds', 7)
        
    final_video = CompositeVideoClip(final_composite, size=final_clip.size)
    
    # Write the final file
    final_video.write_videofile(
        final_reel_path, 
        codec='libx264', 
        audio_codec='aac', 
        fps=24, 
        logger='bar'
    )
    
    # Important: Close all clips to free resources
    for clip in all_clips:
        clip.close()
    
    final_video.close()
    print(f"✅ Final reel assembled with narration: {final_reel_path}")
    return final_reel_path