
import yaml
import os
from dotenv import load_dotenv 

def load_config():
    """Loads configuration from config/config.yaml."""
    load_dotenv() 
    
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print("Error: config/config.yaml not found.")
        exit()

def setup_directories(config):
    """Creates the output directory if it doesn't exist."""
    output_dir = config['output_dir']
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    return output_dir