
import os
import json
from google import genai
from google.genai import types
import time
from typing import Dict, Any, Optional
from moviepy import ColorClip # Correct import for moviepy

# --- Authentication and Setup ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def get_gemini_client():
    """Initializes the Gemini client."""
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    return genai.Client()

# 🟢 MISSING FUNCTION 1: Story Generation (Calls Gemini for structured JSON)
def generate_story_json(client: genai.Client, config: Dict[str, Any], theme: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Generates the structured story plan using the Gemini model."""
    model = config['gemini_model_name']
    num_scenes = config['num_scenes']
    
    prompt = f"""
    Generate a short story for a {config['reel_length_seconds']}-second video reel based on the theme '{theme}'. 
    The story must be divided into exactly {num_scenes} scenes. Each scene should have a clear visual focus for video generation.
    
    Output only a JSON object following this exact schema:
    {{
        "title": "A short, engaging title",
        "theme": "{theme}",
        "scenes": [
            {{
                "description": "Short narrative for the scene.",
                "character_prompt": "Detailed description of the main character/subject for T2V.",
                "setting_prompt": "Detailed cinematic setting (e.g., 'foggy ancient forest, golden hour lighting').",
                "motion_prompt": "Camera movement or subject action (e.g., 'cinematic crane shot, slow pan to the left')."
            }},
            // ... repeat for {num_scenes} total scenes
        ]
    }}
    """
    
    print(f"Calling Gemini for Story Generation (Theme: {theme})...")
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            story_data = json.loads(response.text)
            print("Story generated successfully.")
            return story_data
            
        except json.JSONDecodeError:
            print(f"Error: Gemini did not return valid JSON on attempt {attempt + 1}/{max_retries}.")
            time.sleep(2)  
    return None


# 🟢 STAGE 3: Video Generation (Google Veo 3 via Gemini API)
def generate_scene_video(prompt: str, scene_num: int, output_dir: str, config: Dict[str, Any]) -> str:
    """
    Generates a video clip using Google Veo 3 via the Gemini API.
    This is an asynchronous operation that requires polling.
    """
    print(f"Calling Google Veo 3 API for Scene {scene_num}...")

    client = get_gemini_client()
    model_name = config['video_generation_model_name']
    scene_duration = config.get('scene_duration_seconds', 7)
    
    # Veo 3 currently supports 4, 6, or 8 seconds. 
    if scene_duration <= 4:
        veo_duration = 4
    elif scene_duration <= 6:
        veo_duration = 6
    else:
        veo_duration = 8

    video_filename = os.path.join(output_dir, f"scene_{scene_num}_clip.mp4")

    try:
        # STEP 1: Start the asynchronous video generation operation
        operation = client.models.generate_videos(
            model=model_name,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                resolution="1080p",
            ),
        )

        # STEP 2: Poll the operation status until the video is done
        max_wait_time = 300
        start_time = time.time()
        while not operation.done and (time.time() - start_time) < max_wait_time:
            print(f"Waiting for Veo 3 video (Scene {scene_num})... Elapsed: {int(time.time() - start_time)}s")
            time.sleep(20)
            operation = client.operations.get(operation)

        if not operation.done:
            print(f"Veo 3 operation timed out after {max_wait_time}s.")
            raise TimeoutError("Veo 3 generation timed out.")

        # STEP 3: Download the generated video file
        generated_video = operation.result.generated_videos[0]
        client.files.download(file=generated_video.video, download_path=video_filename)

        print(f"Scene {scene_num} VEO 3 video saved successfully as {video_filename}")
        return video_filename

    except Exception as e:
        print(f"❌ ERROR with Google Veo 3 API for scene {scene_num}. Error: {e}")
        # FALLBACK: Create a mock video on failure
        mock_filename = os.path.join(output_dir, f"scene_{scene_num}_MOCK.mp4")
        print(f"Generating mock video clip due to API error: {mock_filename}")
        clip = ColorClip((1920, 1080), color=(0, 0, 255), duration=scene_duration)
        clip.write_videofile(mock_filename, fps=24, logger=None)
        return mock_filename

# 🟢 MISSING FUNCTION 2: Caption Generation
def generate_caption_and_hashtags(client: genai.Client, config: Dict[str, Any], story_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates social media caption and hashtags using the Gemini model."""
    model = config['gemini_model_name']
    prompt = f"""
    Based on the story titled '{story_data['title']}' with the theme '{story_data['theme']}', 
    generate a compelling social media caption (under 200 characters) and 5 highly relevant hashtags. 
    The tone should be exciting and mysterious. Output only a JSON object following this schema:
    {{
        "caption": "Your compelling caption text here.",
        "hashtags": ["#AIReel", "#GenerativeAI", "#YourThemeTag", "#AnotherTag", "#FifthTag"]
    }}
    """
    
    print("\nCalling Gemini for Caption and Hashtag Generation...")
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        caption_data = json.loads(response.text)
        print("Caption generated successfully.")
        return caption_data
    except Exception as e:
        print(f"Error generating caption: {e}. Using fallback.")
        return {"caption": f"Check out this amazing short! Theme: {story_data['theme']}", "hashtags": ["#AIReel", "#GenerativeAI", "#Shorts"]}