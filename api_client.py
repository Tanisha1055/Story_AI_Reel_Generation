import os
import replicate # <-- We now rely on the official client!
from dotenv import load_dotenv

# --- CRITICAL: Ensure .env is loaded at the file level ---
load_dotenv()

# --- Global Configuration Variables ---
# We keep these for completeness, but replicate library handles its own auth
COMPLIANCE_ENDPOINT = os.getenv("COMPLIANCE_ENDPOINT_URL")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN") # Replicate library looks for this env var

class APIClient:
    """
    Acts as a wrapper for the official 'replicate' Python client to maintain
    compatibility with the existing pipeline's structure (APIClient.run_model).
    """
    def __init__(self):
        # The official 'replicate' library relies on the REPLICATE_API_TOKEN 
        # being set as an environment variable (which you said you have).
        if not REPLICATE_API_TOKEN:
            raise ValueError("The REPLICATE_API_TOKEN environment variable is not set.")
        
        # NOTE: The 'replicate' library is designed to be imported and used directly,
        # so this class mainly exists to adapt to your existing pipeline.

    def run_model(self, model_name: str, model_input_data: dict | str) -> dict:
        """
        Runs the model using the official 'replicate.run' function.
        
        It returns a dictionary with an 'output' key, to match the format
        that the previous custom APIClient was designed to return.
        """
        
        # The replicate.run expects model_name to be "owner/name:version_sha"
        model_identifier = model_name.split(':')[0] 
        print(f"--> [API Client] Requesting run for {model_identifier} (using official 'replicate' client)...")

        try:
            # 1. Execute the run using the official client
            # The client handles async polling, file I/O, and status checks internally.
            
            # Note: We assume the model_name contains the version SHA as per documentation examples.
            output = replicate.run(
                model_name,
                input=model_input_data
            )
            
            # The official client returns the raw output (a list of FileOutput objects for SDXL).
            # We wrap this output in a dictionary to maintain compatibility with your
            # pipeline's expected result format: {'output': [...]}
            return {'output': output}

        except Exception as e:
            print(f"🚨 Official Replicate Client Error for {model_identifier}: {e}")
            # Re-raise the exception to trigger the FATAL PIPELINE ERROR in main.py
            raise