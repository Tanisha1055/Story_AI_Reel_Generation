
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from moviepy.config import change_settings # FFMPEG path configuration might be needed

# Optional: Set FFMPEG path if moviepy can't find it automatically
# change_settings({"FFMPEG_BINARY": "/usr/local/bin/ffmpeg"}) 

def assemble_final_reel(config, clip_paths, story_data):
    """Stitches all video clips together, adds subtitles, and exports the final reel."""
    
    output_dir = config['output_dir']
    final_reel_path = os.path.join(output_dir, config['final_reel_name'])
    
    # 1. Load all video clips
    clips = [VideoFileClip(p) for p in clip_paths]
    
    # 2. Add Subtitles (Optional but highly recommended)
    final_clips_with_subtitles = []
    start_time = 0
    
    for i, (clip, scene) in enumerate(zip(clips, story_data['scenes'])):
        narration = scene['narration']
        
        # Create a text clip for the narration
        text_clip = TextClip(
            narration, 
            fontsize=40, 
            color='white', 
            font='Arial-Bold', 
            stroke_color='black', 
            stroke_width=2,
            bg_color='transparent',
            size=clip.size
        ).set_position(('center', 0.8), relative=True).set_duration(clip.duration)
        
        # Overlay the text onto the video clip
        composite_clip = CompositeVideoClip([clip, text_clip])
        final_clips_with_subtitles.append(composite_clip)

        start_time += clip.duration
    
    # 3. Concatenate all final clips
    final_clip = concatenate_videoclips(final_clips_with_subtitles)
    
    # 4. Add background music (Placeholder/Optional)
    # If you have an audio file:
    # audio_clip = AudioFileClip("path/to/music.mp3").set_duration(final_clip.duration)
    # final_clip = final_clip.set_audio(audio_clip)

    # 5. Export the final reel (Ensuring standard reel/short aspect ratio)
    print(f"Writing final reel to {final_reel_path}...")
    final_clip.write_videofile(
        final_reel_path, 
        codec='libx264', # Standard H.264 codec
        audio_codec='aac', 
        temp_audiofile='temp-audio.m4a', 
        remove_temp=True,
        fps=24 # Frames per second
    )
    
    return final_reel_path