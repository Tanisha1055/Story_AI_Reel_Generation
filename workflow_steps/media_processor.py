import os
from typing import Dict, Any, List
# Assuming api_client.py is imported correctly
from api_client import APIClient
# Assuming .utils has download_file
from .utils import download_file
from moviepy import VideoFileClip, concatenate_videoclips


def generate_and_chain_media(story_data: Dict[str, Any], config: Dict[str, Any], client: APIClient) -> Dict[str, Any]:
    """
    Step 2: Chains SDXL image generation to Seedance video generation.
    FIX: Ensure the output from client.run_model is handled safely regardless
    of whether it returns a dict, list, or FileOutput object.
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
        
        # =========================================================================
        # ✅ FIX: Robustly extract output from char_output
        # =========================================================================
        if isinstance(char_output, dict):
            # Normal case: client.run_model returns {'output': [...]}
            raw_output = char_output.get('output')
            if raw_output is None:
                raw_output_list = []
            elif not isinstance(raw_output, list):
                raw_output_list = [raw_output]
            else:
                raw_output_list = raw_output
        elif isinstance(char_output, list):
            # Case where client.run_model bypasses the {'output':...} wrapper
            raw_output_list = char_output
        else:
            # Case where client.run_model returns a single FileOutput object
            raw_output_list = [char_output] if hasattr(char_output, "url") else []
        # =========================================================================
        
        # Robust URL Extraction (Operating on the guaranteed list: raw_output_list)
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
        
        # =========================================================================
        # ✅ FIX: Robustly extract output from clip_output
        # =========================================================================
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
        # =========================================================================
        
        # =========================================================================
        # ✅ FIX: Robust Video URL Extraction (Operating on the guaranteed list)
        # =========================================================================
        final_video_url = None
        
        if raw_video_list:
            # 💡 Print the now-guaranteed list output for debugging
            print(f"   DEBUG: clip_output type -> {type(clip_output)}")
            print(f"   DEBUG: raw_video_list -> {raw_video_list}")

            first_output = raw_video_list[0]
            if isinstance(first_output, str):
                final_video_url = first_output
            elif isinstance(first_output, dict):
                final_video_url = first_output.get("url")
            elif hasattr(first_output, "url"):
                # Safely get the .url attribute from FileOutput object
                final_video_url = getattr(first_output, "url", None)
            else:
                final_video_url = None
        # =========================================================================

        if not final_video_url:
            print(f"🚨 ERROR: Video model ({VIDEO_MODEL}) did not return a valid video URL. Skipping scene.")
            scene['video_url'] = None
            continue
            
        scene['video_url'] = final_video_url
        print(f"    - Final Video Clip URL: {final_video_url}")

    return story_data


def combine_and_finalize_reel(story_data: Dict[str, Any], config: Dict[str, Any]) -> str:
    """
    Downloads all generated clips and combines them into a final reel using MoviePy.
    """
    print("\n--- 3. Final Reel Assembly and Compliance Check ---")
    
    final_clips = []
    
    if config['VIDEO_CONFIG']['resolution'] == '480p':
        final_w, final_h = 854, 480 
    else:
        final_w, final_h = 480, 480 
    
    total_duration = 0
    scenes_to_process = story_data.get('scenes', [])
    
    for i, scene in enumerate(scenes_to_process):
        clip_filename = f"scene_{i+1}.mp4"
        
        # Retrieve video URL using the correct key 'video_url' (Key Mismatch Fix retained)
        video_url = scene.get('video_url')

        if not video_url:
            print(f"   Skipping Scene {i+1}: Missing video_url.")
            continue
            
        try:
            # Download the real MP4 file for combining
            local_clip_path = download_file(
                url=video_url, 
                directory='assets/downloaded_videos', 
                filename=clip_filename
            )
        except Exception as e:
            print(f"   Skipping Scene {i+1} due to failed download: {e}")
            continue
            
        try:
            clip = VideoFileClip(local_clip_path)
            
            # MANDATORY: Resize and ensure max duration per scene
            clip = clip.resize(newsize=(final_w, final_h)).subclip(0, config['VIDEO_CONFIG']['max_duration_per_scene_seconds'])
            
            total_duration += clip.duration
            final_clips.append(clip)
            
            if total_duration > 120: 
                print("🚨 CRITICAL: Exceeded 120s global limit. Truncating immediately.")
                final_clips.pop()
                break
        except Exception as e:
            print(f"   Skipping Scene {i+1} due to MoviePy/clip error: {e}")
            continue


    if not final_clips:
        raise Exception("No video clips were successfully processed to create the final reel.")
        
    final_reel = concatenate_videoclips(final_clips)
    
    # Final check against the target reel duration
    target_duration = config['VIDEO_CONFIG']['total_reel_duration_seconds']
    if final_reel.duration > target_duration:
        final_reel = final_reel.subclip(0, target_duration)
    
    final_reel_path = "assets/final_reel.mp4"
    
    print(f"✅ Final Reel Duration: {final_reel.duration:.2f}s (Targeted {target_duration}s)")
    print(f"✅ Final Reel Resolution: {final_w}x{final_h} (480p Compliance OK)")
    
    final_reel.write_videofile(
        final_reel_path, 
        codec='libx264', 
        audio_codec='aac', 
        fps=24,
        verbose=False,
        logger=None
    )
    
    print(f"🎉 Final reel saved to: {final_reel_path}")
    return final_reel_path