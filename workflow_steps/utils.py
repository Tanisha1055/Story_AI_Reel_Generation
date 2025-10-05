import os
import requests
from typing import List

# Setup directories
os.makedirs('assets/downloaded_images', exist_ok=True)
os.makedirs('assets/downloaded_videos', exist_ok=True)

def download_file(url: str, directory: str, filename: str) -> str:
    """Downloads a file from a URL to a specified directory."""
    
    # Check for mock URLs which cannot be downloaded
    if "mock-delivery" in url:
        print(f"Skipping download for mock URL: {url}")
        return os.path.join(directory, filename) 
    
    filepath = os.path.join(directory, filename)
    print(f"   Downloading {filename} from {url}...")
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   Download successful: {filepath}")
        return filepath
    except Exception as e:
        print(f"   🚨 Download failed for {url}: {e}")
        # Halt the process if a real file fails to download
        raise