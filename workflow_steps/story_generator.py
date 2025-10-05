import json
import random
import os
from typing import Dict, Any
from api_client import APIClient
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client directly
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in .env")
    GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"🚨 FATAL: Failed to initialize Gemini Client: {e}")
    # We must raise here as the first step is essential
    raise e

STORY_PROMPT_TEMPLATE = """
Generate a high-detail storyboard for a {total_reel_duration} second video reel based on the theme: '{theme}'.
The story must be broken down into exactly {num_scenes} distinct scenes.
For each scene, provide:
1. 'scene_title': A short title.
2. 'scene_description': A vivid text description of the action, suitable for video generation.
3. 'character_prompt': A high-detail image generation prompt for the main character's state in this scene.
4. 'setting_prompt': A high-detail image generation prompt for the environment/setting.

Return the result as a single, valid JSON object following the example structure.
"""
# --- Define the required JSON structure using the Gemini types ---
STORY_JSON_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "storyboard": types.Schema(
            type=types.Type.ARRAY,
            description="A list of the video scenes.",
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "scene_title": types.Schema(type=types.Type.STRING),
                    "scene_description": types.Schema(type=types.Type.STRING),
                    "character_prompt": types.Schema(type=types.Type.STRING),
                    "setting_prompt": types.Schema(type=types.Type.STRING)
                },
                required=["scene_title", "scene_description", "character_prompt", "setting_prompt"]
            )
        )
    },
    # The output will have one top-level key: 'storyboard'
    required=["storyboard"] 
)

def generate_story_data(config: Dict[str, Any], client: APIClient) -> Dict[str, Any]:
    """Step 1: Generates the structured story and image/video prompts using the direct Gemini API."""
    
    # --- SETUP AND PROMPT GENERATION ---
    theme = random.choice(config['THEMES'])
    cfg = config['VIDEO_CONFIG']
    num_scenes = cfg['total_reel_duration_seconds'] // cfg['max_duration_per_scene_seconds']
    
    prompt = STORY_PROMPT_TEMPLATE.format(
        theme=theme, 
        num_scenes=num_scenes, 
        total_reel_duration=cfg['total_reel_duration_seconds']
    )
    
    print(f"\n--- 1. Story Generation (Theme: {theme}, Scenes: {num_scenes}) ---")
    
    try:
        # --- INITIAL GEMINI API CALL WITH SCHEMA ENFORCEMENT ---
        response = GEMINI_CLIENT.models.generate_content(
            model=config['GEMINI_STORYBOARD_MODEL'],
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", 
                # CRITICAL CHANGE: ENFORCE THE SCHEMA
                response_schema=STORY_JSON_SCHEMA,
                system_instruction="You are a storyboard artist. Output ONLY a single JSON object that strictly conforms to the provided schema."
            )
        )
        
        json_string = response.text.strip()
        
        # NOTE: With response_schema, the model output is usually clean JSON, 
        # so markdown fence cleanup may not be strictly needed, but we keep the initial cleanups for safety.
        if json_string.startswith("```json"):
             json_string = json_string.strip("```json").strip("```").strip()
        elif json_string.startswith("```"):
             json_string = json_string.strip("```").strip()

        # --- SIMPLIFIED JSON PARSING AND VALIDATION ---
        try:
            story_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            # If it fails here, the model has ignored the schema/mime_type, which is a rare but fatal failure
            raise ValueError(f"CRITICAL JSON DECODE FAILURE after schema attempt: {e}. Raw output: {json_string[:200]}...")

        # The schema forces the top-level key to be 'storyboard'
        potential_scenes = story_data.get('storyboard')

        # FINAL CHECK: Validation and Assignment
        if isinstance(potential_scenes, list) and len(potential_scenes) == num_scenes:
            # Assign the final expected key 'scenes' for downstream compatibility
            story_data['scenes'] = potential_scenes
            del story_data['storyboard'] # Clean up the schema-enforced key if necessary
        elif isinstance(potential_scenes, list) and len(potential_scenes) > 0:
            # If the count is off, log a warning but use the data
            print(f"⚠️ Warning: Model returned {len(potential_scenes)} scenes, expected {num_scenes}.")
            story_data['scenes'] = potential_scenes
            if 'storyboard' in story_data:
                del story_data['storyboard']
        else:
            # Final fatal error if 'storyboard' key is missing or invalid
            print(f"🚨 FATAL: Generated JSON does not contain the required 'storyboard' list.")
            raise ValueError("JSON structure invalid: missing 'storyboard' list required by schema.")
        
        # Assign metadata
        story_data['theme'] = theme
        story_data['num_scenes'] = len(story_data['scenes']) # Use the actual count
        print("   Story data generated and parsed successfully using direct Gemini API.")
        return story_data
        
    except Exception as e:
        print(f"🚨 FATAL ERROR: Story generation failed: {e}")
        raise

def generate_caption(story_data: Dict[str, Any], config: Dict[str, Any], client: APIClient) -> Dict[str, Any]:
    """Uses the direct Gemini API to generate a short, punchy caption."""
    
    caption_prompt = f"Write a compelling, short social media caption for a reel titled '{story_data.get('title', story_data['theme'])}'. Include 3 relevant hashtags. Limit to 30 words."
    
    try:
        # --- DIRECT GEMINI API CALL (Text Mode) ---
        caption_output = GEMINI_CLIENT.models.generate_content(
            model=config['GEMINI_CAPTION_MODEL'],
            contents=caption_prompt
        )
        
        caption = caption_output.text.strip()
        
        # Simple cleanup
        caption = caption.strip().strip('"').strip("'")
        
        print(f"   Generated Caption: {caption}")
        story_data['reel_caption'] = caption
        return story_data
        
    except Exception as e:
        print(f"🚨 Warning: Failed to generate caption using direct Gemini API: {e}. Using fallback.")
        story_data['reel_caption'] = f"An AI Reel about {story_data['theme']}. #AI #GenAI"
        return story_data