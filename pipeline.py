import argparse
import os
from dotenv import load_dotenv
load_dotenv() 
from src.utils import load_config, setup_directories
from src import generator
from src import media_processor
from src import social_poster
import traceback

os.environ["FFMPEG_BINARY"] = "C:/ffmpeg/bin/ffmpeg.exe"

def main(theme=None):
    """
    Executes the end-to-end automation pipeline.
    """
    config = load_config()
    # output_dir needs to be available for the generator.generate_scene_image call
    output_dir = setup_directories(config) 
    
    # Override theme if provided via command line
    if theme:
        config['theme'] = theme
    
    # --- CHANGE 1: REMOVED GEMINI IMAGE MODEL SETTING ---
    # config['image_generation_model'] = 'imagen-3.0-generate-002' 
            
    print("\n--- Starting AI Reel Generation Pipeline ---")
    print(f"Theme: {config['theme']}")
    print("-" * 40)
    
    try:
        # Initialize Gemini Client (still needed for generate_story_json and generate_caption_and_hashtags)
        gemini_client = generator.get_gemini_client()

        # --- STAGE 1 & 2: Story and Prompt Generation ---
        story_data = generator.generate_story_json(gemini_client, config, config['theme'])
        if not story_data or not story_data.get('scenes'):
            print("Failed to generate valid story data. Exiting.")
            return

        final_clip_paths = [] 
        for i, scene in enumerate(story_data['scenes']):
            scene_id = i + 1
            print(f"\n[SCENE {scene_id}/{config['num_scenes']}] Processing...")
            
            # --- CONSOLIDATED STAGE: Generate Frame using Hugging Face Stable Diffusion ---
            # 1. Combine prompts into a single string
            full_prompt = f"{scene['character_prompt']} {scene['setting_prompt']}"
            
            # 2. CHANGE 2: Updated function call signature for the Hugging Face implementation
            scene_frame_path = generator.generate_scene_image(
                full_prompt, # Prompt is the first argument
                scene_id,     # Scene number/ID
                output_dir    # Output directory for saving the image
            )
            
            # 💡 CONSOLIDATED STAGE: Generate Dynamic Video Clip using MoviePy
            clip_path = media_processor.generate_dynamic_video_clip(
                config, scene_id, scene_frame_path, scene['motion_prompt']
            )
            final_clip_paths.append(clip_path) 

        # --- STAGE 6.1: Final Reel Assembly (MoviePy) ---
        final_reel_path = media_processor.assemble_final_reel(config, final_clip_paths, story_data) 
        
        print("\n*** END-TO-END REEL GENERATION SUCCESSFUL ***")
        print(f"Final Reel Path: {final_reel_path}")
        print("-" * 40)

        # --- STAGE 6.2: Caption Generation and Posting ---
        caption_data = generator.generate_caption_and_hashtags(gemini_client, config, story_data)
        social_poster.post_reel(final_reel_path, caption_data)

    
    except Exception as e:
        print("❌ ERROR OCCURRED ❌")
        print(traceback.format_exc())
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Reel Generation Automation Pipeline")
    parser.add_argument(
        '--theme', 
        type=str, 
        default=None, 
        help="Optional: Override the theme specified in config.yaml."
    )
    args = parser.parse_args()
    main(args.theme)