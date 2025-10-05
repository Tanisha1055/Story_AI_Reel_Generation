import os
import json
from api_client import APIClient
from workflow_steps.story_generator import generate_story_data, generate_caption
from workflow_steps.media_processor import generate_and_chain_media, combine_and_finalize_reel

# Load configuration
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("FATAL ERROR: config.json not found.")
    exit(1)

def run_automation_pipeline():
    """
    The main orchestration function for the end-to-end automation pipeline.
    """
    print("#" * 50)
    print("   AI Engineer Reel Automation Pipeline Started   ")
    print("#" * 50)

    # 0. Initialize API Client
    try:
        api_client = APIClient()
        os.makedirs('assets', exist_ok=True)
    except ValueError as e:
        print(f"Initialization Failed: {e}")
        return

    try:
        # 1. Generate Storyboard and Prompts (Direct Gemini API)
        story_data = generate_story_data(config, api_client)
        
        # CORRECTED CALL: Passing (story_data, config, api_client)
        story_data = generate_caption(story_data, config, api_client)

        # 2. Generate and Chain Media: (SDXL -> Seedance)
        story_data = generate_and_chain_media(story_data, config, api_client)

        # 3. Combine and Finalize Reel (MoviePy)
        final_reel_path = combine_and_finalize_reel(story_data, config)
        
        print("\n" + "=" * 50)
        print(f"Pipeline Complete. Final Reel at: {final_reel_path}")
        print(f"Caption: {story_data.get('reel_caption', 'No caption generated.')}")
        print("=" * 50)

    except Exception as e:
        print("\n" + "!" * 50)
        print(f"FATAL PIPELINE ERROR: {e}")
        print("!" * 50)


if __name__ == "__main__":
    run_automation_pipeline()