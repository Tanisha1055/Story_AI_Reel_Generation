
import os
import json
import requests
from google import genai
from google.genai import types

# --- Authentication and Setup ---
# The keys are retrieved from environment variables
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def get_gemini_client():
    """Initializes the Gemini client."""
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    # The client will automatically pick up the GEMINI_API_KEY
    return genai.Client()

# --- STAGE 1 & 2: Story and Prompt Generation (Gemini) ---

def generate_story_json(client, config, theme):
    """Generates a structured story and detailed visual prompts using Gemini."""
    model = config['gemini_model_name']
    num_scenes = config['num_scenes']
    
    prompt = f"""
    Generate a short story for a {config['reel_length_seconds']}-second video reel based on the theme '{theme}'. 
    The story must be exactly {num_scenes} scenes. For each scene, provide:
    1. 'narration': A short line of dialogue or narration.
    2. 'character_prompt': A highly detailed, professional text-to-image prompt (e.g., cinematic, 8k, photorealistic) describing the main character for that specific scene. Ensure consistency across scenes.
    3. 'setting_prompt': A highly detailed, professional text-to-image prompt describing the background and environment.
    4. 'motion_prompt': A short instruction for the video model (e.g., 'Slow zoom on the character's face', 'Gentle camera pan left', 'Slight handheld shake').
    
    Output only a JSON object following this exact schema:
    {{
        "title": "...",
        "theme": "{theme}",
        "scenes": [
            {{
                "id": 1,
                "narration": "...",
                "character_prompt": "...",
                "setting_prompt": "...",
                "motion_prompt": "..."
            }},
            # ... up to {num_scenes} scenes
        ]
    }}
    """
    
    print(f"Calling Gemini for Story Generation (Theme: {theme})...")
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )

    try:
        story_data = json.loads(response.text)
        print("Story generated successfully.")
        return story_data
    except json.JSONDecodeError:
        print("Error: Gemini did not return valid JSON.")
        print("Raw Response:", response.text[:200])
        return None

# --- STAGE 3: Asset Generation (Minimax/Image-01 - PLACEHOLDER) ---

def generate_scene_assets(config, scene_id, char_prompt, setting_prompt, output_dir):
    """Generates character and setting images via Minimax API."""
    print(f"Generating assets for Scene {scene_id}...")
    
    MINIMAX_KEY = os.environ.get("MINIMAX_KEY")
    if not MINIMAX_KEY:
        raise ValueError("MINIMAX_KEY environment variable not set.")

    endpoint = config['minimax_endpoint']
    
    # *** PLACEHOLDER for Minimax API CALL ***
    # In a real scenario, you'd make two separate calls here (or one if the API supports batch).
    
    # 1. Character Generation
    char_filename = os.path.join(output_dir, f"scene_{scene_id}_char.png")
    # response = requests.post(endpoint, json={'prompt': char_prompt, 'key': MINIMAX_KEY, ...})
    # with open(char_filename, 'wb') as f:
    #     f.write(response.content) 

    # 2. Setting Generation
    setting_filename = os.path.join(output_dir, f"scene_{scene_id}_setting.png")
    # response = requests.post(endpoint, json={'prompt': setting_prompt, 'key': MINIMAX_KEY, ...})
    # with open(setting_filename, 'wb') as f:
    #     f.write(response.content) 

    # --- MOCK ASSET CREATION (FOR DEMO/TESTING ONLY) ---
    # Since we can't call Minimax, we create dummy files (requires Pillow)
    from PIL import Image, ImageDraw
    Image.new('RGB', (512, 512), color = 'red').save(char_filename)
    Image.new('RGB', (512, 512), color = 'blue').save(setting_filename)
    
    print(f"Mock assets saved: {char_filename}, {setting_filename}")
    return char_filename, setting_filename

# --- STAGE 4: Scene Frame Creation (Kontext-Pro - PLACEHOLDER) ---

def combine_assets_to_frame(config, scene_id, char_img_path, setting_img_path):
    """Combines character and setting into a cohesive frame using Kontext-Pro."""
    print(f"Composing frame for Scene {scene_id}...")
    
    KONTEXT_PRO_KEY = os.environ.get("KONTEXT_PRO_KEY")
    if not KONTEXT_PRO_KEY:
        raise ValueError("KONTEXT_PRO_KEY environment variable not set.")
    
    endpoint = config['kontext_pro_endpoint']
    frame_filename = os.path.join(config['output_dir'], f"scene_{scene_id}_frame.png")

    # *** PLACEHOLDER for Kontext-Pro API CALL ***
    # You would typically upload these files or pass their URLs to the API.
    # prompt = "Overlay the character realistically onto the setting, preserving lighting."
    # data = {'character': char_img_path, 'setting': setting_img_path, 'prompt': prompt, 'key': KONTEXT_PRO_KEY, ...}
    # response = requests.post(endpoint, files=data)
    # with open(frame_filename, 'wb') as f:
    #     f.write(response.content) 

    # --- MOCK FRAME CREATION (FOR DEMO/TESTING ONLY) ---
    from PIL import Image
    char = Image.open(char_img_path).convert("RGBA")
    setting = Image.open(setting_img_path).convert("RGBA")
    setting.paste(char, (100, 100), char) # Simple paste for mock
    setting.convert('RGB').save(frame_filename)

    print(f"Mock frame saved: {frame_filename}")
    return frame_filename

# --- STAGE 5: Video Clip Generation (Seedance-1-Pro - PLACEHOLDER) ---

def generate_video_clip(config, scene_id, frame_path, motion_prompt):
    """Generates a video clip from a static frame using Seedance API."""
    print(f"Generating video clip for Scene {scene_id}...")
    
    SEEDANCE_KEY = os.environ.get("SEEDANCE_KEY")
    if not SEEDANCE_KEY:
        raise ValueError("SEEDANCE_KEY environment variable not set.")
        
    endpoint = config['seedance_endpoint']
    duration = config['scene_duration_seconds']
    clip_filename = os.path.join(config['output_dir'], f"scene_{scene_id}_clip.mp4")

    # *** PLACEHOLDER for Seedance API CALL ***
    # data = {'image_url': frame_path, 'prompt': motion_prompt, 'duration': duration, 'key': SEEDANCE_KEY, ...}
    # response = requests.post(endpoint, json=data)
    # with open(clip_filename, 'wb') as f:
    #     f.write(response.content) 
    
    # --- MOCK VIDEO CREATION (REQUIRES MOVIEPY - FOR DEMO/TESTING ONLY) ---
    from moviepy import ImageClip
    # Create a simple clip from the static frame for demonstration
    clip = ImageClip(frame_path, duration=duration)
    clip.write_videofile(clip_filename, fps=24, logger=None)
    
    print(f"Mock video clip saved: {clip_filename}")
    return clip_filename

# --- Auxiliary Function for Posting Metadata ---

def generate_caption_and_hashtags(client, config, story_data):
    """Generates a social media-friendly caption and relevant hashtags."""
    prompt = f"""
    Based on the story titled '{story_data['title']}' with the theme '{story_data['theme']}', 
    generate a compelling social media caption (under 200 characters) and 5 highly relevant hashtags. 
    The tone should be exciting and mysterious. Output only a JSON object.
    """
    
    response = client.models.generate_content(
        model=config['gemini_model_name'],
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )

    try:
        caption_data = json.loads(response.text)
        return caption_data
    except json.JSONDecodeError:
        return {"caption": f"Check out this amazing short! Theme: {story_data['theme']}", "hashtags": ["#AIReel", "#GenerativeAI", "#Shorts"]}