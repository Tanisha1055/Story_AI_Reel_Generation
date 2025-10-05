import os
from typing import Dict, Any, List
# Assuming api_client.py is imported correctly
from api_client import APIClient
# Assuming .utils has download_file
from .utils import download_file

# =========================================================================
# ✅ FINAL FIX: Consolidated and Corrected MoviePy v2.x imports
# We use 'from moviepy.video.fx import all as vfx' to ensure resize and subclip are available.
# =========================================================================
from moviepy import VideoFileClip, concatenate_videoclips
from moviepy.video import fx as vfx 
# =========================================================================


def generate_and_chain_media(story_data: Dict[str, Any], config: Dict[str, Any], client: APIClient) -> Dict[str, Any]:
    """
    Step 2: Chains SDXL image generation to Seedance video generation.
    FIX: Robustly handle API client output (dict, list, or FileOutput object).
    """
    print("\n--- 2. Image and Video Generation Chain (SDXL -> Seedance) ---")
    
    VIDEO_MODEL = config['VIDEO_GENERATOR_MODEL']
    CLIP_DURATION = config['VIDEO_CONFIG']['max_duration_per_scene_seconds']
    
    # Accessing the corrected 'scenes' list from story_data
    for i, scene in enumerate(story_data['scenes']):
        print(f"  > Processing Scene {i+1}: {scene['scene_title']}")
        
        # --- 2a. Character Image Generation (SDXL) ---
        char_input = {"prompt": scene['character_prompt'], "aspect_ratio": "1:1"}
        
        char_output = client.run_model(model_name=config['IMAGE_CHARACTER_MODEL'], model_input_data=char_input)
        
        # Robustly extract output from char_output
        if isinstance(char_output, dict):
            raw_output = char_output.get('output')
            if raw_output is None:
                raw_output_list = []
            elif not isinstance(raw_output, list):
                raw_output_list = [raw_output]
            else:
                raw_output_list = raw_output
        elif isinstance(char_output, list):
            raw_output_list = char_output
        else:
            raw_output_list = [char_output] if hasattr(char_output, "url") else []
        
        # Robust URL Extraction
        char_url = None
        if raw_output_list:
            first_output = raw_output_list[0]
            if isinstance(first_output, str):
                char_url = first_output
            elif isinstance(first_output, dict):
                char_url = first_output.get("url")
            elif hasattr(first_output, "url"):
                char_url = getattr(first_output, "url", None)
            else:
                char_url = None
        
        if not char_url:
            print("🚨 ERROR: SDXL did not return a valid image URL. Skipping scene.")
            continue
        
        scene['character_image_url'] = char_url
        print(f"    - Character Image URL: {char_url}")

        # --- 2b. Video Clip Generation (Seedance-1-pro) ---
        seedance_input = {
            "prompt": scene['scene_description'],
            "image": char_url, 
            "duration": CLIP_DURATION,
            "resolution": config['VIDEO_CONFIG']['resolution'] 
        }
        
        clip_output = client.run_model(model_name=VIDEO_MODEL, model_input_data=seedance_input)
        
        # Robustly extract output from clip_output
        if isinstance(clip_output, dict):
            raw_video_output = clip_output.get('output')
            if raw_video_output is None:
                raw_video_list = []
            elif not isinstance(raw_video_output, list):
                raw_video_list = [raw_video_output]
            else:
                raw_video_list = raw_video_output
        elif isinstance(clip_output, list):
            raw_video_list = clip_output
        else:
            raw_video_list = [clip_output] if hasattr(clip_output, "url") else []
        
        # Robust Video URL Extraction
        final_video_url = None
        
        if raw_video_list:
            print(f"   DEBUG: clip_output type -> {type(clip_output)}")
            print(f"   DEBUG: raw_video_list -> {raw_video_list}")

            first_output = raw_video_list[0]
            if isinstance(first_output, str):
                final_video_url = first_output
            elif isinstance(first_output, dict):
                final_video_url = first_output.get("url")
            elif hasattr(first_output, "url"):
                final_video_url = getattr(first_output, "url", None)
            else:
                final_video_url = None

        if not final_video_url:
            print(f"🚨 ERROR: Video model ({VIDEO_MODEL}) did not return a valid video URL. Skipping scene.")
            scene['video_url'] = None
            continue
            
        scene['video_url'] = final_video_url
        print(f"    - Final Video Clip URL: {final_video_url}")

    return story_data


def combine_and_finalize_reel(story_data, config):
    """
    Downloads all video clips from the generated URLs and merges them into a final reel.
    Does NOT resize or trim clips.
    """
    final_clips = []

    for i, scene in enumerate(story_data.get('scenes', [])):
        video_url = scene.get('video_url')
        if not video_url:
            print(f"Skipping Scene {i+1}: Missing video_url.")
            continue

        try:
            local_clip_path = download_file(
                url=video_url,
                directory='assets/downloaded_videos',
                filename=f"scene_{i+1}.mp4"
            )
            clip = VideoFileClip(local_clip_path)
            final_clips.append(clip)
        except Exception as e:
            print(f"Skipping Scene {i+1} due to error: {e}")
            continue

    if not final_clips:
        raise Exception("No video clips were successfully downloaded to create the final reel.")

    final_reel = concatenate_videoclips(final_clips)
    final_reel_path = "assets/final_reel.mp4"

    final_reel.write_videofile(
        final_reel_path,
        codec='libx264',
        audio_codec='aac',
        fps=24
    )

    # Close all clips to free resources
    final_reel.close()
    for clip in final_clips:
        clip.close()

    print(f"🎉 Final reel saved to: {final_reel_path}")
    return final_reel_path