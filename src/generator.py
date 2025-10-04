
import os
import json
import requests
from google import genai
from google.genai import types
from moviepy.video import fx as vfx
from PIL import Image, ImageDraw # Used only for fallback mock image
import requests
import base64
import time
from typing import Dict, Any, Optional

# --- Authentication and Setup ---
# The keys are retrieved from environment variables
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

def get_gemini_client():
    """Initializes the Gemini client."""
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    # The client will automatically pick up the GEMINI_API_KEY
    return genai.Client()

# --- STAGE 1 & 2: Story and Prompt Generation (Gemini) ---

def generate_story_json(client: genai.Client, config: Dict[str, Any], theme: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Generates a structured story and detailed visual prompts using Gemini.
    Includes a retry mechanism to handle partial or malformed JSON responses.
    """
    model = config['gemini_model_name']
    num_scenes = config['num_scenes']
    
    # --- Prompt Definition ---
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
    
    # --- Retry Loop Implementation ---
    for attempt in range(max_retries):
        try:
            # 1. Generate content from Gemini
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            # 2. Parse the JSON response
            story_data = json.loads(response.text)
            
            # Success
            print("Story generated successfully.")
            return story_data
        
        except json.JSONDecodeError:
            # Error handling for truncated or invalid JSON
            print(f"Error: Gemini did not return valid JSON on attempt {attempt + 1}/{max_retries}.")
            print("Raw Response (Partial):", response.text[:200])
            
            if attempt + 1 == max_retries:
                print("All retries failed. Returning None.")
                return None 
            
            # Wait 2 seconds before retrying
            time.sleep(2) 

    # Should be unreachable if max_retries > 0
    return None

def generate_scene_image(prompt: str, scene_num: int, output_dir: str) -> str:
    """Generates an image using the Stable Diffusion API via Hugging Face."""
    print(f"Calling Stable Diffusion for Scene {scene_num}...")

    # Configuration for the Stable Diffusion model
    HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    
    # Get token securely from the environment
    HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

    if not HF_TOKEN:
        raise ValueError("HUGGINGFACE_TOKEN not found. Please set it in your .env file.")

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # The payload structure often needs a few parameters for better generation
    payload = {
        "inputs": prompt,
        "options": {"wait_for_model": True} # Important: Wait if the model is loading
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"HuggingFace API Request Failed: {e}")

    # The response content is the raw image data (e.g., JPEG or PNG)
    image_data = response.content
    frame_filename = f"{output_dir}/scene_{scene_num}.png"
    
    with open(frame_filename, "wb") as f:
        f.write(image_data)

    print(f"Scene {scene_num} image saved successfully as {frame_filename}")
    return frame_filename

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