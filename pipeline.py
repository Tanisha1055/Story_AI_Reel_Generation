
import argparse
import os
from dotenv import load_dotenv
load_dotenv() 
from src.utils import load_config, setup_directories
from src import generator
from src import media_processor
from src import social_poster

def main(theme=None):
    """
    Executes the end-to-end automation pipeline.
    """
    config = load_config()
    output_dir = setup_directories(config)
    
    # Override theme if provided via command line
    if theme:
        config['theme'] = theme
        
    print("\n--- Starting AI Reel Generation Pipeline ---")
    print(f"Theme: {config['theme']}")
    print("-" * 40)
    
    try:
        # Initialize Gemini Client
        gemini_client = generator.get_gemini_client()

        # --- STAGE 1 & 2: Story and Prompt Generation ---
        story_data = generator.generate_story_json(gemini_client, config, config['theme'])
        if not story_data or not story_data.get('scenes'):
            print("Failed to generate valid story data. Exiting.")
            return

        final_clips = []
        for i, scene in enumerate(story_data['scenes']):
            scene_id = i + 1
            print(f"\n[SCENE {scene_id}/{config['num_scenes']}] Processing...")
            
            # --- STAGE 3: Asset Generation (Minimax/Image-01) ---
            char_img_path, setting_img_path = generator.generate_scene_assets(
                config, scene_id, scene['character_prompt'], scene['setting_prompt'], output_dir
            )
            
            # --- STAGE 4: Scene Frame Creation (Kontext-Pro) ---
            scene_frame_path = generator.combine_assets_to_frame(
                config, scene_id, char_img_path, setting_img_path
            )
            
            # --- STAGE 5: Video Clip Generation (Seedance-1-Pro) ---
            clip_path = generator.generate_video_clip(
                config, scene_id, scene_frame_path, scene['motion_prompt']
            )
            final_clips.append(clip_path)

        # --- STAGE 6.1: Final Reel Assembly (MoviePy) ---
        final_reel_path = media_processor.assemble_final_reel(config, final_clips, story_data)
        print("\n*** END-TO-END REEL GENERATION SUCCESSFUL ***")
        print(f"Final Reel Path: {final_reel_path}")
        print("-" * 40)

        # --- STAGE 6.2: Caption Generation and Posting ---
        caption_data = generator.generate_caption_and_hashtags(gemini_client, config, story_data)
        social_poster.post_reel(final_reel_path, caption_data)

    except Exception as e:
        print(f"\n--- CRITICAL ERROR --- \n{e}")
        print("Ensure all environment variables (API keys) are set and dependencies installed.")

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